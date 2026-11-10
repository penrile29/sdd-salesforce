# Knowledge: the why of this project

The code and the design documents tell the **what** and the **how**; this folder keeps the **why**, so that anyone,
person or agent, understands why the system is the way it is before changing it. If you are an agent, `ls` this folder
before planning or building anything and choose what to read by the headers (`read-knowledge` skill).

| Folder | What it keeps | Skill |
|---|---|---|
| `discovery/` | The AS-IS: the client's sources (cited, not copied), the org snapshot, documentation and Slack. Index in [discovery/README.md](discovery/README.md) | — |
| `specs/` | Requirements with AC and, later, the design; from the Design gate on, their "Change log" | `create-spec` |
| `decisions/` | Why X and not Y. 001 is the adoption of the method; the project's own start at 002 | `create-decision` |
| `gotchas/` | Traps already paid for, with their evidence | `create-gotcha` |

When reading, only `Active` decisions bind. The names, frontmatter and statuses of each type are set by their skills.
