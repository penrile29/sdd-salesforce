# sdd-salesforce changelog

Each project records in its decision 001 and in `sdd.config.json` the version of the method it adopted. If the loaded
plugin is a different one, the start hook and `check-environment.py` warn about it: check here what changed and, if it
affects the project, record it with a decision.

## 0.5.0 · 2026-11-12 (release)

**Light profile.** A project is `full` (the whole method, as before) or `light` (`method.profile`). Light keeps the
three gates (Plan, Design, release), the spec with requirements and AC, traceability, org isolation and the approver's
OK for every external message and every irreversible org setting, and relaxes the rest: environment gaps are warnings,
decisions only for what matters, no review of the spec and the plan before the Design gate, a flat delivery plan
(`W1.n` with `Satisfies`, `Touches`, `Skill`), no test-first, deploy, `sf agent publish` and `sf agent activate` in the
project's org without asking (the `sf` guard no longer asks), a release gate that is "demo accepted", and handovers only
when compacted or at the end of the day. The hook injects a light block after the core in light projects. Rule M-11
explains why and lists the irreversible settings. `sdd-bootstrap` asks one question with three options (full with OK at
every step, full critical only, light). Projects without `method.profile` are `full`: nothing changes for them. The
Spanish aliases `metodo.perfil`, `ligero` and `completo` are accepted.

**Parallel orchestration.** In both profiles, the orchestrator launches author subagents in parallel, each in its own
worktree, with the files they touch reserved through the new step field `Touches`, and one reviewer subagent with a
separate context per step; it integrates and deploys one step at a time. Separate author sessions still work in full.

**Browser for UI tests (rule M-12).** `sdd-bootstrap` asks whether the project will test in the browser (yes by
default with UI areas) and writes `.mcp.json` with the Playwright MCP pinned in the catalog (`@playwright/mcp@0.0.83`,
Chromium revision 1247), its profile and output in `.playwright/` (ignored by git), and `environment.browser` in
`sdd.config.json`. When `environment.browser` is true, or the project already has the `playwright` server,
`check-environment.py` checks `node`, `npx`, the `.mcp.json` and the Chromium revision and gives the command that
installs it; a project without the key and with UI areas only gets a warning. With `--query-org` it records the org's
My Domain in the inventory (`org.my_domain`; a sandbox keeps its suffix, `acme--uat`, and the value is only kept while
`org_alias` does not change). A new hook, `browser_guard.py`, denies opening the host of another Salesforce org from
the Playwright MCP (a sandbox is another org), also in the file that `browser_run_code_unsafe` names, and asks while
the My Domain is not recorded. The verification label `browser check` (`comprobación en navegador`
in the `es` vocabulary) is read in the step report, and the reference `references/browser.md` gathers the setup and the
Salesforce gotchas. An older project gets the browser with `sdd-bootstrap --add-missing`, which merges `.mcp.json`
without touching the rest.

**For projects on 0.4:** nothing breaks. To adopt light or the browser, record it with a decision that supersedes 001.

## 0.4.1 · 2026-11-11 (release)

**The map opens on the web.** GitHub shows HTML files as source code, so the README now links `MAP.html` to its
GitHub Pages copy, https://penrile29.github.io/sdd-salesforce/MAP.html. The map itself does not change, and the copy
in the plugin still opens offline. Nothing else changes: projects on 0.4.0 do not need a decision.

## 0.4.0 · 2026-11-10 (release)

**The plugin is in English, with a single copy.** Skills, references, templates, scripts, hooks, README, GUIDE, MAP
and this changelog are in English. Nothing is kept twice: there is no Spanish copy.

**Language rule.** Claude answers in the user's language. The project's documents are written in `method.language`
of `sdd.config.json` (if it is not set, in the user's language), and every subagent brief states it. Template
headings and fields, IDs, git tags and file names are copied as they are, never translated: a project in Spanish has
its prose in Spanish and the template headings in English. `sdd-bootstrap` asks for the document language only when
it is not clear from the conversation and records it in `method.language` and in decision 001.

**Vocabulary per project.** The headings, fields, IDs, tags and paths that `check-traceability.py` reads depend on the
project, set by `method.vocabulary` (`en` or `es`):
- New projects use `en`: `AC-<AREA>-NN.N` IDs, `## Change log`, `Depends on` / `Satisfies` / `Test first` / `Size`,
  `[PENDING: Q-NN]`, the `design-approved` tag, `step-reports/`, `w0-validations.md`, `demo-walkthrough.md` and
  `docs/baseline/environment.json`. "Evolutivo" is now a *change request*, with levels 0 bug, 1 tweak, 2 feature and
  3 contract or risk.
- Projects bootstrapped with 0.2 or 0.3 keep their Spanish vocabulary (`CA-…`, `## Registro de cambios`, `fichas/`,
  `diseno-aprobado`…) and keep working unchanged. Without `method.vocabulary`, a configuration with `metodo` is read
  as `es`, also if an English `method` was added next to it.
- Spanish keys in `sdd.config.json` are always accepted as aliases, at every level, as are the values `estricta` and
  `critico` (now `strict` and `critical`), the Spanish answer keys of the bootstrap interview and the Spanish area IDs
  (`voz` → `voice`, `integracion` → `integration`, `sitio-lwr` → `lwr-site`, `canales-mensajeria` →
  `messaging-channels`, `modelo-datos` → `data-model`, `seguridad-acceso` → `access-security`, `analitica` →
  `analytics`). If a section appears in both languages (`method` and `metodo`), both are merged key by key; where
  both have the same key with different values, the English one wins, with a warning in the session context. An
  unknown `method.vocabulary` ends with exit code 2.

**Renamed.**
- Skills: `sdd-metodo` → `sdd-method`, `sdd-ayuda` → `sdd-help`. The shortcuts `/sdd-salesforce:sdd-metodo` and
  `/sdd-salesforce:sdd-ayuda` no longer exist.
- Scripts: `check-entorno.py` → `check-environment.py`, `check-trazabilidad.py` → `check-traceability.py`,
  `arrancar.py` → `bootstrap.py`; the hooks are `method_context.py`, `sf_guard.py` and `project.py`.
- References: `reglas.md` → `rules.md`, `comunicacion.md` → `communication.md`, `orquestador.md` →
  `orchestrator.md`, `brief-autor.md` → `author-brief.md`; the catalog `skills-por-area.json` →
  `skills-by-area.json`.
- Files: `GUIA.md` → `GUIDE.md`, `MAPA.html` → `MAP.html`. In new projects, `docs/cliente/` → `docs/client/` and the
  seed decision `001_adoptar-sdd-salesforce.md` → `001_adopt-sdd-salesforce.md` (an existing old seed is recognised
  and linked).
- Script options are in English (`--self-test`, `--project`, `--step`, `--graph`, `--no-review`, `--quick`,
  `--query-org`, `--no-write`, `--catalog`, `--validate-catalog`, `--target`, `--answers`, `--dry-run`,
  `--add-missing`, `--replace-readme`). The Spanish ones (`--autoprueba`, `--paso`, `--grafo`, `--rapido`…) are still
  accepted, because the documents of older projects give them.

**Inventory and report in English.** `check-environment.py` writes the inventory with English keys and states
(`present` / `missing` / `shadowed`), to `docs/baseline/environment.json` in new projects (`entorno.json` in older
ones), and the report to `environment-<date>.md` (`entorno-<fecha>.md` in older ones). `check-traceability.py`
reads an inventory in either language. Script messages and outputs, including `--json`, are in English (`AVISO` is now
`WARNING`).

**Older projects keep their hook label.** The `CLAUDE.md` generated by 0.2 and 0.3 tells Claude to stop if it does not
see «[sdd-salesforce …] Proyecto sdd»: in those projects the hook's first line keeps that label. New projects get
"sdd project".

**Not yet validated in a real session:** the real-session tests have not been run against this version. The
self-tests and two rounds of independent review pass.

### Upgrading from 0.3

- **Nothing to migrate.** A 0.3 project keeps its Spanish configuration, headings, IDs, tag and paths; the checks and
  the hooks read them as before. Do not set `method.vocabulary: "en"` on it: its documents would no longer match.
  Moving an existing project to the `en` vocabulary is not supported.
- **Old names are mapped by the hook.** Your `CLAUDE.md`, decision 001, `status.md` and handover still cite
  `sdd-metodo`, `check-trazabilidad.py`, `docs/cliente/` and so on. In those projects the hook adds a line with each
  old name and its replacement, and the English terms of the method core next to your Spanish headings (`Change log`
  = `Registro de cambios`, `step-reports/` = `fichas/`…). Old script options keep working. To call a skill yourself,
  use the new name (`/sdd-salesforce:sdd-method`, `/sdd-salesforce:sdd-help`), or just ask.
- **Document language.** The method core now arrives in English, but Claude still answers in your language and, with
  no `method.language`, writes documents in it. To fix it, add `"language": "es"` (or `"idioma": "es"`) inside the
  `metodo` object of `sdd.config.json`.
- **Running `sdd-bootstrap` 0.4 over a 0.3 project is not a migration.** It does not overwrite existing files and
  leaves `sdd.config.json` (and so the `es` vocabulary) as it is; at most it adds the missing files with their new
  English names next to the Spanish ones. Do not use it to upgrade.
- As with any version change, the start hook and `check-environment.py` warn that the project adopted 0.3.0; if you
  adopt 0.4.0, record it with a decision.

## 0.3.0 · 2026-11-10 (release)

**Guided conversation: nobody has to invoke a skill.**
- The method core gains the rule "You lead": in the first message Claude orients the user from `status.md`, loads the
  skills itself and ends each gate or escalation with a single concrete question. `sdd-metodo` (now `sdd-method`)
  gains the section "Guided conversation", with what to do on "start", "where are we?", "I approve", "there is a
  bug…" or "record this".
- `sdd-bootstrap` continues in the same session: when it finishes it loads `sdd-metodo` and asks whether to start the
  Plan. There is no longer any need to open a new session.
- `UserPromptSubmit` hook: if the session does not have the core yet (for example, because the project was
  bootstrapped in it), it injects it once.
- The start hook's short notice also appears in an empty folder and no longer gives a `/command`: Claude offers the
  bootstrap in one sentence and loads `sdd-bootstrap` itself.
- The descriptions of `sdd-bootstrap` and `sdd-metodo` include the phrases with which their work is requested.
- README, GUIA (now GUIDE) and `sdd-ayuda` (now `sdd-help`) describe each step with an example phrase; the
  `/commands` remain as a shortcut.
- With `critico` autonomy (now `critical`), between steps Claude reports and carries on; the closing question is for
  gates and escalations. After the Plan gate, the Design gate or a release is approved, it says that the next stage
  continues in a new session.
- **Not revalidated in a real session:** `claude -p` had no API access, so the real-session tests remain pending
  against this version. The self-tests and an independent review pass.

## 0.2.0 · 2026-11-06 (release)

**A single source for the method.**
- New skill, `sdd-metodo` (now `sdd-method`), with the method's rules (cycle and gates, roles, Definition of Done,
  escalation, communication, environment, traceability and change requests) and, in `references/`, the why of each
  rule (M-01 to M-09), the orchestrator template, the author brief and the communication protocol.
- `SessionStart` hook: in a project with `sdd.config.json`, it injects the method core and the project data when a
  session starts, resumes and after it is compacted.
- `PreToolUse` hook on Bash: it denies `sf` commands against another org or without `--target-org` when they change an
  org, and asks for confirmation for `sf agent publish`, `sf agent activate` and, with strict autonomy, for a deploy.
- The scripts `check-entorno.py` (now `check-environment.py`) and `check-trazabilidad.py` (now
  `check-traceability.py`) run from the plugin; `check-entorno.py` treats the skills of the plugin it runs from as
  present, also with `--plugin-dir`.

**A lighter bootstrap** (20 files instead of 35; the initial reading drops from about 6,800 to about 1,500 words):
- a short `CLAUDE.md` with the project data and a single seed decision, "We adopt sdd-salesforce X.Y": the project's
  decisions start at 002;
- a minimal `sdd.config.json`, with the `metodo` section (version, approver and autonomy);
- no `scripts/`, no seeds 001-009 and no `agent-brief.md`, `orchestrator-prompt.md` or `communication-protocol.md`,
  which live in the plugin;
- `integration.md`, the plan and the traceability, with only what belongs to the project.

**Change requests** ("evolutivos", changes after the Design gate): a change queue in `status.md`, level 0 (bug) and a
short path for levels 0-1, a "Registro de cambios" (change log) at the end of the spec, the delta written before the
code with the approval pending, the `release-N` tag and a check error if a requirement or AC changed without its row.
The log compares every spec with the last tag, so deleting a spec retires its IDs and renaming it changes nothing.

**For newcomers:** the `sdd-ayuda` skill (now `sdd-help`) explains what the plugin is, what it installs, how it is used
and good SDD practices in Salesforce, with the path to the guide and the map; and in a Salesforce project that does
not use the method yet, the start hook leaves a line so that Claude offers `/sdd-salesforce:sdd-bootstrap`.

**Other:** the option to "link" the rules of a parent `CLAUDE.md` is gone (there are no longer rules in the generated
`CLAUDE.md`); the light profile is retired. The package now ships only the plugin; development material stays out.

## 0.1.0 · 2026-11-05

First version: `sdd-bootstrap` with the rules, the 8 seed decisions and the scripts copied into each project; method
and knowledge skills; environment verification and a generalised traceability check.
