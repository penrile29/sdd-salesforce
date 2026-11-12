# sdd-salesforce

**Spec-driven development with agents in Salesforce projects.** A Claude Code plugin that sets up the project and
teaches Claude to work with this method:

1. Requirements with acceptance criteria before designing.
2. Decisions verified with the Salesforce skills and the official documentation.
3. A delivery plan with AC → step → test traceability, checked by a script.
4. Independent review with a separate context.
5. Human gates at the points that change the product.

Two profiles: **full**, the whole method, and **light**, the same gates and the same spec with AC with less ceremony
around them, for demos. UI tests use Playwright's own Chromium, per project.

Author: **Pedro Fernández Enrile, Principal SE**. Version 0.5.0 (changes in [CHANGELOG.md](CHANGELOG.md)).

The methodology, explained for the team, is in [GUIDE.md](GUIDE.md).
[MAP.html](https://penrile29.github.io/sdd-salesforce/MAP.html) is an interactive map of the files that the method
generates and maintains, by stage and with the skills that create them: the link opens it on the web, and the copy in
the plugin opens in any browser, offline. The plugin's design, its reviews and its real-session tests stay in the
development repository: they are not part of the package.

## What it includes

| Skill | What for |
|---|---|
| `sdd-method` | **The method's rules, in one place**: cycle and gates, roles, Definition of Done, escalation, communication, language, environment verification, traceability and change requests. Ships the `check-environment.py` and `check-traceability.py` scripts |
| `sdd-bootstrap` | Bootstraps a project: a short interview, then it generates a short `CLAUDE.md` with the project data, `sdd.config.json`, the adoption decision 001, `knowledge/`, `docs/delivery-plan/` and the first commit |
| `implementation-integration-plan` | Discovery, spec, decisions and delivery plan (steps, dependencies, waves, traceability); afterwards, the integration |
| `independent-code-review` | Review with a context separate from the author's, with findings, evidence and a verdict on a specific commit |
| `create-spec` | A spec in two parts: requirements with IDs and AC (Given/When/Then) and, afterwards, design and contracts; from the Design gate on, its "Change log" |
| `create-decision` | Decisions with status, author, alternatives and "Verified with" |
| `create-gotcha` | Traps already paid for, with their evidence |
| `read-knowledge` | Reads the why of the current project (never from other customers' folders) |
| `sdd-help` | For newcomers: what the plugin is, what it installs, how to use it in a simple or complex POC, good SDD practices in Salesforce and where the guide and the map are. Ask "what is sdd-salesforce?" or "how do I start?" |

**Hooks**, which only act inside a project with `sdd.config.json` (in a Salesforce project that does not use the
method yet, or in an empty folder, the start hook only adds a line so that Claude offers to bootstrap it if you are
about to start, plan or build something):
- **when a session starts, resumes or is compacted**, and in the first message of a session that does not have it yet
  (the bootstrap session), they inject the method core and the project data, so the rules are not copied into the
  project and survive compaction;
- **before every Bash command**, they deny `sf` commands against another org or without `--target-org` when they
  change an org, and ask for confirmation for `sf agent publish`, `sf agent activate` and, with strict autonomy, for a
  deploy (with the light profile, none of the three asks). Reads also need `--target-org`, so as not to read data
  from the default org, which may belong to another customer;
- **before every tool of the Playwright MCP**, they deny opening the host of another Salesforce org (a sandbox counts
  as another org): the browser only opens the project's org, by its My Domain, which the environment verification
  records. Until it is recorded, they ask before opening any org host.

**Scripts** (in `skills/sdd-method/scripts/`; they run from the plugin and are not copied):
- **`check-environment.py`:** at the start of Plan, verifies that the Salesforce skills, the tools and the API version
  the project needs are there. It reads the minimums from the frontmatter of each sf-skill.
- **`check-traceability.py`:** checks that every AC in the spec has its step and its verification, that the plan has
  no cycles, that the skill of each step is installed and, from the Design gate on, that every change to the spec has
  its row in the "Change log".

## Language

Claude answers in the language you write in. The project's documents are written in `method.language` of
`sdd.config.json`, which the bootstrap asks for when it is not clear from the conversation (if it is not set, they
follow your language). The headings and fields of the templates, the IDs (`AC-…`), the git tags and the file names
stay in English whatever the language, because the scripts read them: a project in Spanish has its prose in Spanish
and the template headings in English.

## Requirements

- Claude Code.
- The **sf-skills** from `forcedotcom/sf-skills` (tested with release 1.66.0) and, for Agentforce agents, the
  **ADLC** plugin (`agentforce-adlc`). The plugin does not ship them; `check-environment.py` says which ones are
  missing.
- Salesforce CLI (`sf`), `git` and `python3` (3.9 or later; some sf-skills need 3.10). Some skills also need `jq` and
  `node`.
- For UI tests: `node` and `npx`, and Playwright's Chromium for the pinned `@playwright/mcp` (the environment
  verification gives the command that installs it). The MCP is declared per project in `.mcp.json`, which
  `sdd-bootstrap` writes; check whether your organization requires approving MCP servers before using it.

## Installation

The plugin is distributed from a public GitHub repository,
[`penrile29/sdd-salesforce`](https://github.com/penrile29/sdd-salesforce), which is also its marketplace. No access
request is needed.

With Claude Code 2.1.275 or later, in a single step, inside a session:

```text
/plugin install sdd-salesforce --marketplace penrile29/sdd-salesforce
```

Or from the terminal, in two steps (installs with user scope; add `--scope project` for a single project):

```bash
claude plugin marketplace add penrile29/sdd-salesforce
claude plugin install sdd-salesforce@sdd-salesforce
```

- **Update:** `claude plugin update sdd-salesforce@sdd-salesforce`. Then open a new session. If the version changes,
  the plugin's notice tells you in every POC; check the [CHANGELOG](CHANGELOG.md).
- **Try it without installing anything:** `claude --plugin-dir /path/to/sdd-salesforce` (the `.zip` works too).

**From a file** (`sdd-salesforce-<version>.zip`), without access to the repository:

1. To try it in a session, without installing anything: `claude --plugin-dir /path/to/sdd-salesforce-<version>.zip`.
2. To install it permanently, unzip it into a stable folder (for example, `~/plugins/sdd-salesforce`, which is also
   its marketplace) and, from the terminal:

   ```bash
   claude plugin marketplace add ~/plugins/sdd-salesforce
   claude plugin install sdd-salesforce@sdd-salesforce
   ```

3. To update to a new version, replace the contents of that folder and run
   `claude plugin marketplace update sdd-salesforce` and `claude plugin update sdd-salesforce@sdd-salesforce`.

In all three cases, open a new session afterwards. To learn what it is and how to start, ask "what is
sdd-salesforce?".
- **License:** proprietary, in [LICENSE](LICENSE). Installing and using it is allowed; modifying or redistributing it
  is not. Improvements are proposed to the author with an issue.

If you have the `knowledge-base` plugin installed, uninstall it wherever you use this one: both ship a different
`create-decision`.

## Usage

Everything is asked for by talking: you do not need to know what the skills are called. Claude loads the right one,
tells you where the project stands and ends each step with the question that unblocks it.

1. Create the SFDX project (`sf project generate`) or open an empty folder, and start Claude Code there.
2. Say what you want, for example "I want to set up a Salesforce POC for Acme". Claude offers to bootstrap it with the
   method and runs the interview: customer, org alias, approver, orchestrator autonomy, Salesforce areas,
   confidentiality and, if it is not clear, the language of the documents.
3. When it finishes, in the same session, it asks you for what only you can do: log in to the org (`sf org login web
   --alias <org>`, `sf config set target-org <org>`) and copy the customer's sources into `docs/client/` (not
   versioned).
4. Say "start". Claude follows the cycle and stops at each gate to wait for your OK:
   - **Plan:** environment verification and discovery → Plan gate;
   - **Design:** spec with requirements and AC, decisions and delivery plan, with independent review → Design gate;
   - **Execute:** one step at a time, tests first and with independent review;
   - **Review:** integration in the org and Definition of Done → release gate, with the `release-N` tag.
5. To resume, in any session, ask "where are we?". To approve a gate, "I approve".
6. After the Design gate, describe the change as you would to a person ("there is a bug in…", "change
   AC-ORD-01.2"). It follows the **change-request path**: it enters the queue in `status.md`, is classified at level 0
   (bug) to 3 and, if it touches the spec, leaves its row in the "Change log" before the code. A bug or a tweak
   (levels 0 and 1) takes the short path: a test or the change, and a review of the diff.

**Shortcuts:** if you prefer, `/sdd-salesforce:sdd-bootstrap` bootstraps the project and `/sdd-salesforce:sdd-help`
explains the method. They are not needed.

## Several POCs on the same machine

- **One folder, one git and one org per POC.** Each one has its `sdd.config.json` with its `org_alias`. Projects are
  not nested.
- **The plugin is installed once** and every POC uses the same version of the method. Each POC records in its decision
  001 and in `sdd.config.json` the version it adopted; if the loaded plugin is a different one, the start hook and
  `check-environment.py` warn about it. Check the [CHANGELOG](CHANGELOG.md) and, if something affects the POC, record
  it with a decision.
- **The org does not cross over:** the hook denies Bash `sf` commands that target an org other than the one of the
  folder they run in (also inside `$(…)`, after `npx` or with `SF_TARGET_ORG`), those that touch an org without
  `--target-org` (the global default org may belong to another POC), those that redefine the project's alias and those
  run in another POC from this one's session. If the POC uses scratch orgs, declare its dev hub in `dev_hub` in
  `sdd.config.json`. It does not see scripts that call `sf` internally or the Salesforce MCP tools: with those, the
  method's rule applies.
- **Nor does the knowledge:** `read-knowledge` only reads the current project's, even if there are sibling folders
  with their own.
- **A simple POC** uses the same with less ceremony: one or two waves, level 1 or 2 steps and a single session that
  writes, with a subagent that reviews. The handover and the queue are used the same way; orchestration across several
  author sessions, only if needed.

## How the work is split: profile and autonomy

An orchestrator launches author subagents in parallel, each in its own worktree and with the files it touches
reserved, and one reviewer subagent with a separate context per step; it integrates and deploys one step at a time.
The ceremony of each change is set by its level (0 to 3): a text tweak is not treated like a permissions change.

The bootstrap asks one question with three options:
- **Full, OK at every step** (`strict`): human OK at every gate, also at every Execute step.
- **Full, critical only** (`critical`): the gate of each step is the reviewer's verdict; user experience, approved
  requirements, stack changes and blockers are escalated.
- **Light:** the same three gates and the spec with requirements and AC, with a flat delivery plan, no test-first, no
  review of the spec and the plan before the Design gate, and deploy, publish and activate in the project's org without
  asking. The release gate becomes "demo accepted". Good for demos with little risk and a short deadline.

In all of them, the Plan gate, the Design gate, the release, every irreversible org setting and every external message
need the approver's OK.

## Browser for UI tests

With `browser: true` in the interview (proposed when there are UI areas), the project gets a `.mcp.json` with the
Playwright MCP pinned by the plugin, with its own Chromium and its profile in `.playwright/` (not versioned). The
Browser pane and Claude in Chrome are not used: they are disabled in enterprise orgs. You approve the MCP the first
time, open a new session in the project and log in to the org by hand in the Chromium window. UI AC are verified with
`browser check`, and the demo walkthrough is run in Chromium. Details in `skills/sdd-method/references/browser.md`.
