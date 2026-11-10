---
name: sdd-bootstrap
description: "Bootstraps a Salesforce project with the sdd-salesforce method: a short interview, then it generates a short CLAUDE.md with the project's data, sdd.config.json, adoption decision 001, knowledge/, docs/delivery-plan/ (status, change queue, handover, questions, plan and traceability) and local git. The method's rules and scripts stay in the plugin. Use it when someone wants to start, set up or bootstrap a Salesforce project, POC, demo or RFP (an empty folder or one just created with sf project generate, without sdd.config.json), even if they do not name the method or the skill."
---

# sdd-bootstrap

Leaves a project ready to work with the method: a short `CLAUDE.md` with the project's data, `sdd.config.json`,
`knowledge/` with adoption decision 001, `docs/delivery-plan/` with the project's own templates and a first commit.
The method's rules (`sdd-method` skill) and the environment and traceability scripts **are not copied**: they are used
from the plugin, and the plugin injects the method's core into every session of the project. It does **not** write the
spec or do the discovery: that is the Plan stage, which starts right after.

The templates and the generator are in this skill's folder: `${CLAUDE_SKILL_DIR}/assets/` and
`${CLAUDE_SKILL_DIR}/scripts/bootstrap.py`.

## What it does not do
- It does not create the SFDX project (`sf project generate`), log in to the org or change its configuration.
- It does not run `sf` commands against any org until the user has confirmed that the alias is this project's.
- It does not run commands whose output carries credentials, such as `sf org display`, which includes the access
  token.
- It does not create a remote, push or publish anything.
- It does not overwrite files: if one exists, it shows it and asks.

## 1. Check the target
The target is the folder the user names or, if they say nothing, the working directory. Look at:
- **What is there:** `ls -la`. If it is neither empty nor a freshly created SFDX project, show the user what is there
  and ask before going on.
- **`sfdx-project.json`:** if it does not exist, say so and offer `sf project generate --name <name> --output-dir
  <parent>`; without it you can go on, but with the documentation only.
- **Several POCs:** each in its own folder, with its own git and its own org. If the target is inside another project
  with `sdd.config.json`, stop and ask: projects are not nested.
- **Git:** if there is already a repository, do not run `git init`; use that one.
- **Org:** read the alias only from the target's local configuration (`.sf/config.json` → `target-org`). Do not use
  `sf config get target-org` to propose it: it may return the global default org, which may belong to another client.

## 2. Interview
Ask one thing per topic. Whatever is already known from the environment, propose it instead of asking. For closed
options, use questions with options.

| Key | Question | Notes |
|---|---|---|
| `project`, `client` | Name of the project and of the client | |
| `org` | Alias of the integration org | From the local `.sf/config.json`, if it exists. A different one per POC |
| `expiry` | When the org expires | Once the alias is confirmed, read it with the `dx-org-trial-expiration-check` skill (it queries `TrialExpirationDate` with SOQL; for a scratch org, `sf org list`). If it is not there or not known, "to be confirmed" |
| `approver` | Who approves the gates and the release | A name: it will appear in the decisions |
| `autonomy` | `strict` (human OK at every gate, including each Execution step) or `critical` (only what is critical is escalated; the gate for each step is the reviewer's verdict) | Recommend `strict` if it is their first time with the method |
| `areas` | Salesforce pieces planned | Options: the keys of `areas` in `${CLAUDE_SKILL_DIR}/../sdd-method/scripts/skills-by-area.json`; they can be left empty and set in the discovery |
| `client_sources` | Which client sources there will be in `docs/client/` | A description only, no content |
| `internal_only` | Which material is internal only (competitors, product direction…) | |
| `channels` | Allowed external channels (Slack, email, Support…) | Every message sent will still need the approver's OK |
| `language` | Language of the project's documents | Ask **only** if it is not clear from the conversation (for example, the user writes in Spanish and the client's documents are in Spanish: `es`). A short code such as `es` or `en`. If in doubt and they do not answer, leave it out: the documents then follow the user's language |

Write the answers to a JSON file in the scratchpad (not in the project), with these keys.

## 3. Generate
1. **Dry-run** and show the result:
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/scripts/bootstrap.py --target <target> --answers <answers.json> --dry-run
   ```
2. If there are **conflicts**, show them and ask: stop, or write only what is missing (`--add-missing`). If the
   conflict is the `CLAUDE.md`, also offer to generate the new one in the scratchpad and show the differences. If it is
   the `README.md` from `sf project generate` (the script says so), ask whether to replace it: with an OK, add
   `--replace-readme`.
3. **Generate** (the same command without `--dry-run`, with `--add-missing` or `--replace-readme` if they were
   chosen). If the target already has decision 001, the script uses its date and says so: it does not duplicate it.

## 4. Git
- No repository: `git init -b main`.
- `git add` what was generated and one commit, "Bootstrap the sdd-salesforce method". The `baseline-<date>` tag is
  **not** set now: it is set when the approver approves the Plan gate.

## 5. Check
From the target:
- `python3 ${CLAUDE_SKILL_DIR}/../sdd-method/scripts/check-traceability.py`: it must finish **with no errors** (with
  an empty spec there will be warnings).
- `python3 ${CLAUDE_SKILL_DIR}/../sdd-method/scripts/check-environment.py --quick`: a quick check of the base skills
  and the planned areas. It warns, it does not block. Compare what it says with the list of skills in your session and
  mention the gaps in the summary.

## 6. Summary and next step
Say what was created, merged or left untouched, the commit and the warnings. Then **carry on in this same session**:
do not send the user to open another one.

**Unless the target is not the session's working directory** (for example, the session was opened in `~/pocs` and
the project is `~/pocs/acme`): there, this session does not see the project (it does not load its `CLAUDE.md`, does
not receive the core, and the `sf` guard does not recognize it). Say so in one sentence and ask the user to open the
session in the target; there, saying "start" is enough. What follows then applies to that session.
- Read the whole `sdd-method` skill: from here on the method applies, also for the rest of this session.
- Say what only the user can do:
  - if there is no login to the org, `sf org login web --alias <org>` and `sf config set target-org <org>` inside the
    target;
  - copy the client's sources into `docs/client/` (it is not versioned).
- Close with **one** question: whether you should start the **Plan** once that is ready (it starts with the full
  environment verification and goes on with the discovery, which ends at the Plan gate). If the user says yes, start
  it here.
- Do not ask the user to invoke a skill or give them a `/command`: they ask for the next thing by talking ("start",
  "what is missing?").
