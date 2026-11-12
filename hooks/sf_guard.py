#!/usr/bin/env python3
"""PreToolUse (Bash) hook of sdd-salesforce: protects the project's org and the release gate.

It only acts inside a project with sdd.config.json (the one of the folder each command runs in, following the `cd`s
of the call) and on sf or sfdx commands, wherever they are: after `npx`, `time`, `sudo` or `env`, inside `$(…)`,
backticks, parentheses or `bash -c '…'`. For each one it:
- denies pointing at an org other than the project's org_alias (--target-org, -o, --targetusername, -u, in any of
  their forms and even if repeated), and SF_TARGET_ORG or SFDX_DEFAULTUSERNAME pointing at another one;
- denies `sf config set target-org <other>` and `sf alias set <org_alias>=…`, which would redefine the project's org;
- denies a command that touches an org without an explicit --target-org, unless the project's local target-org
  (.sf/config.json) is its own: the default org may belong to another project. Only local commands are exempt
  (org list, org login, alias list, config get, project generate, plugins, help…);
- if sdd.config.json cannot be read or has no org_alias, denies every command that touches an org until it is fixed;
- asks for confirmation (ask) for `sf agent publish` and `sf agent activate`, which are the release gate, and, with
  strict autonomy, for a deployment that is not --dry-run. With the light profile (method.profile), neither asks: they
  are automatic in the project's org, which is still the only one allowed.
It does not see scripts that call sf internally nor MCP tools: the method's rule covers that. On a failure of its own,
it decides nothing.

Usage: python3 sf_guard.py            (reads the JSON event from stdin)
       python3 sf_guard.py --self-test
"""

import json
import os
import re
import shlex
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import project as P  # noqa: E402

SHELL_C = re.compile(r"""(?:^|[\s;&|(])(?:bash|sh|zsh)\s+(?:-\w*c\w*)\s+(?P<q>['"])(?P<body>.*?)(?P=q)""", re.DOTALL)
EVAL = re.compile(r"""(?:^|[\s;&|(])eval\s+(?P<q>['"])(?P<body>.*?)(?P=q)""", re.DOTALL)
ASSIGNMENT = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")
ORG_VARS = ("SF_TARGET_ORG", "SFDX_DEFAULTUSERNAME")
LONG_FLAGS = ("--target-org", "--targetusername")
SHORT_FLAGS = ("-o", "-u")
LOCAL_COMMANDS = ("", "org list", "org login", "org logout", "org create", "alias list", "alias unset", "config get",
                  "config list", "config unset", "project generate", "template", "plugins", "version", "help", "update",
                  "autocomplete", "info", "doctor", "search", "commands", "which", "whatsnew", "lightning generate",
                  "apex generate", "schema generate", "force:project:create", "force:alias:list", "force:org:list",
                  "force:auth", "auth", "code-analyzer", "scanner", "project convert", "project list",
                  "static-resource generate", "visualforce generate", "analytics generate", "force:source:convert",
                  "force:mdapi:convert", "force:apex:class:create", "force:lightning")
RELEASE = ("agent publish", "agent activate")
SF_TOPICS = ("project", "org", "data", "apex", "agent", "alias", "config", "package", "community", "schema", "sobject",
             "lightning", "flow", "deploy", "retrieve", "force:source:deploy", "force:data:soql:query")
USE_DEV_HUB = ("org create scratch", "org delete scratch", "org resume scratch", "org create shape", "package",
               "force:org:create", "force:package")


def tokens(segment):
    """The words of a command. If a piece was left with a stray double quote (when splitting at a $( inside quotes),
    that quote is removed before reading it."""
    for candidate in (segment, segment.replace('"', "") if segment.count('"') % 2 else None):
        if candidate is None:
            continue
        try:
            return shlex.split(candidate)
        except ValueError:
            pass
    return segment.replace('"', "").replace("'", "").split()


def split_commands(text):
    """Splits a command into its simple commands, like the shell: at &&, ||, ;, |, &, newlines, parentheses, $( and
    backticks, and at { and } when they stand alone. It does not split inside single quotes; inside double quotes, a $(
    or a backtick opens code until it closes. A backslash at the end of a line continues the command."""
    text = re.sub(r"\\\r?\n", " ", text or "")
    pieces, current, quote, stack, i = [], [], None, [], 0

    def cut():
        pieces.append("".join(current))
        del current[:]
    while i < len(text):
        c, two = text[i], text[i:i + 2]
        if quote == "'":
            current.append(c)
            quote = None if c == "'" else quote
        elif quote == '"':
            if two == "$(" or c == "`":
                cut()
                stack.append('"')
                quote = None
                i += 2 if two == "$(" else 1
                continue
            current.append(c)
            if c == "\\" and i + 1 < len(text):
                current.append(text[i + 1])
                i += 1
            elif c == '"':
                quote = None
        elif c in "'\"":
            quote = c
            current.append(c)
        elif two in ("&&", "||", "$(", "<(", ">("):
            cut()
            stack.append(None)
            i += 2
            continue
        elif c in ")`" and stack:
            cut()
            quote = stack.pop()
        elif c in ";|&\n()`":
            cut()
        elif c in "{}" and (i == 0 or text[i - 1] in " \t;") and (i + 1 == len(text) or text[i + 1] in " \t;\n"):
            cut()
        else:
            current.append(c)
            if c == "\\" and i + 1 < len(text):
                current.append(text[i + 1])
                i += 1
        i += 1
    cut()
    return [s.strip() for s in pieces if s.strip() and s.strip() != '"']


def segments(command):
    """The simple commands of a Bash call, with what is inside bash -c and eval expanded."""
    text = command or ""
    inner = []
    for rx in (SHELL_C, EVAL):
        inner += [m.group("body") for m in rx.finditer(text)]
    return split_commands(text) + [s for body in inner for s in split_commands(body)]


WRAPPERS = ("npx", "time", "sudo", "env", "command", "exec", "nohup", "nice", "caffeinate", "xargs", "timeout",
            "watch", "bunx", "pnpm", "yarn")
SHELL_KEYWORDS = ("if", "then", "else", "elif", "while", "until", "do", "!", "coproc")
NON_EXECUTING = ("echo", "printf", "grep", "egrep", "fgrep", "rg", "cat", "less", "more", "head", "tail", "wc", "sort",
                 "diff", "true", "false", ":", "#")


def is_sf(token):
    return os.path.basename(token) in ("sf", "sfdx") or "salesforce/cli" in token


def strip_keywords(f):
    """The tokens of a command without the shell keywords that precede it (do, then, if, !…)."""
    while f and f[0] in SHELL_KEYWORDS:
        f = f[1:]
    return f


def sf_position(f):
    """Index of sf or sfdx if it is the command that runs: the first one, or after assignments and a wrapper (npx,
    sudo -u user, time -p, xargs -I{}…, with their options). None if the command is something else (echo sf …,
    git commit -m "sf …")."""
    i = 0
    while i < len(f) and ASSIGNMENT.match(f[i]):
        i += 1
    if i >= len(f):
        return None
    if is_sf(f[i]):
        return i
    if os.path.basename(f[i]) not in WRAPPERS:
        return None
    for j in range(i + 1, len(f)):
        if is_sf(f[j]):
            return j
    return None


def resolve(value, known):
    """Replaces $VAR and ${VAR} with their value if the call assigns it; if any is left unresolved, None."""
    def one(m):
        name = m.group(1) or m.group(2)
        return known[name] if name in known else "\0"
    r = re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)", one, value)
    return None if "\0" in r or "$" in r or "{}" in r or "`" in r else r


def org_values(f):
    """All the values of the org options of an sf command, in any of their forms."""
    vals = []
    for i, x in enumerate(f):
        if x in LONG_FLAGS + SHORT_FLAGS and i + 1 < len(f):
            vals.append(f[i + 1])
        elif any(x.startswith(op + "=") for op in LONG_FLAGS + SHORT_FLAGS):
            vals.append(x.split("=", 1)[1])
        elif any(x.startswith(op) and len(x) > 2 and not x.startswith("--") for op in SHORT_FLAGS):
            vals.append(x[2:])
    return vals


def decide(command, cwd):
    """(decision, reason): decision is 'deny', 'ask' or None."""
    here = os.path.abspath(cwd or os.getcwd())
    session = P.project_root(here)  # the session's project: a cd out of it does not switch the guard off
    asks, env = [], {}
    known = {}
    for seg in segments(command):
        f = strip_keywords(tokens(seg))
        if f[:1] == ["for"] or (f[:1] and f[0].startswith("#")):
            continue
        if f[:1] == ["cd"] and len(f) > 1:
            here = os.path.normpath(os.path.join(here, os.path.expanduser(f[1])))
            continue
        if f[:1] == ["export"]:
            f = f[1:]
        assigned = dict(m.groups() for m in (ASSIGNMENT.match(x) for x in f) if m)
        known.update(assigned)
        env.update({k: v for k, v in assigned.items() if k in ORG_VARS})
        root = P.project_root(here) or session
        if not root:
            continue
        if session and root != session and sf_position(f) is not None:
            return "deny", ("This session belongs to the project %s: do not run sf in another project (%s) from it; "
                            "open a session in its folder." % (session, root))
        org, method, conf, problem = P.config(root)
        for var, value in env.items():
            if org and value != org:
                return "deny", ('This project (%s) works only with the org "%s", and %s points to "%s".'
                                % (root, org, var, value))
        if f and os.path.basename(f[0]) in NON_EXECUTING:
            continue
        if f[:1] == ["git"] and f[1:2] and f[1] in ("commit", "log", "show", "diff", "grep", "tag"):
            continue
        # Fail-safe: an org option that points at another org, in a command that runs something, is denied even if the
        # command is not recognised as sf (a shell alias, $S, an odd wrapper).
        long_values = [x.split("=", 1)[1] if "=" in x else (f[k + 1] if k + 1 < len(f) else "")
                       for k, x in enumerate(f) if x.split("=", 1)[0] in LONG_FLAGS]
        idx = sf_position(f)
        via_var = bool(f) and f[0].startswith("$") and (
            is_sf(resolve(f[0], known) or "") or (len(f) > 1 and f[1] in SF_TOPICS))
        candidates = long_values + (org_values(f) if idx is not None or via_var else [])
        for value in candidates:
            real = resolve(value, known)
            if real != org:
                return "deny", ('This project (%s) works only with the org "%s", and "%s" points to "%s". Repeat the '
                                'command with a literal --target-org %s.' % (root, org, " ".join(f[:4]), value, org))
        if idx is None:
            if via_var:
                return "deny", ('"%s" may be sf through a variable: write the sf command directly so that the guard '
                                'can check the org.' % " ".join(f[:3]))
            continue
        f = f[idx:]
        words = []
        for x in f[1:]:
            if x.startswith("-"):
                break
            words.append(x)
        sub = " ".join(words)
        shown = " ".join(f[:4])
        if "--help" in f or "-h" in f:
            continue
        local = any(sub == lc or sub.startswith(lc + " ") or (lc.endswith(":") and sub.startswith(lc))
                    for lc in LOCAL_COMMANDS)
        if problem:
            if local:
                continue
            return "deny", ('%s in %s: fix it before running "%s", because without it the project\'s org is unknown.'
                            % (problem, root, shown))
        if sub.startswith("config set"):
            values = [x.split("=", 1)[1] for x in f if x.startswith("target-org=")]
            values += [f[i + 1] for i, x in enumerate(f) if x == "target-org" and i + 1 < len(f)]
            if any(v != org for v in values):
                return "deny", ('This project (%s) works only with the org "%s": do not change its target-org to '
                                'another one.' % (root, org))
            continue
        if sub.startswith("alias set") or sub.startswith("force:alias:set"):
            if any(x.split("=", 1)[0] == org for x in f if "=" in x) or org in f[f.index(words[-1]) + 1:]:
                return "deny", 'Do not redefine the alias "%s", which is the org of this project (%s).' % (org, root)
            continue
        hubs = [f[k + 1] for k, x in enumerate(f) if x == "--target-dev-hub" and k + 1 < len(f)]
        hubs += [x.split("=", 1)[1] for x in f if x.startswith("--target-dev-hub=")]
        if any(sub.startswith(c) for c in USE_DEV_HUB):  # elsewhere, -v is something else (--values in data create)
            hubs += [f[k + 1] for k, x in enumerate(f) if x == "-v" and k + 1 < len(f)]
        hub = str(conf.get("dev_hub") or "").strip()
        if not hubs and any(sub.startswith(c) for c in USE_DEV_HUB[:4]):
            local_hub = P.read_json(os.path.join(root, ".sf", "config.json"))[0].get("target-dev-hub")
            local_hub = str(local_hub or "").strip()
            if not hub or local_hub != hub:
                return "deny", ('"%s" would use the default dev hub, which may belong to another project. %s' % (
                    shown, "Repeat the command with --target-dev-hub %s." % hub if hub else
                    'Declare the POC\'s dev hub in "dev_hub" of sdd.config.json and pass it with --target-dev-hub.'))
        if any(h != hub for h in hubs):
            return "deny", ('"%s" uses the dev hub "%s", and this project (%s) %s. If the POC uses scratch orgs, put '
                            'its dev hub in "dev_hub" of sdd.config.json.'
                            % (shown, hubs[0], root, 'declares "%s"' % hub if hub else "declares none"))
        targets = org_values(f)
        others = [d for d in targets if resolve(d, known) != org]
        if others:
            return "deny", ('This project (%s) works only with the org "%s", and "%s" points to "%s". Repeat the '
                            'command with --target-org %s.' % (root, org, shown, others[0], org))
        if not targets and not local and P.local_target_org(root) != org:
            return "deny", ('"%s" touches an org and has no --target-org: the default org may belong to another '
                            'project. Repeat the command with --target-org %s.' % (shown, org))
        if any(sub.startswith(r) for r in RELEASE) and P.V.profile(method) != "light":
            asks.append("Publishing or activating an agent is the release gate: it needs the explicit OK of the "
                        "approver (%s)." % (method.get("approver") or "the project's approver"))
        elif sub.startswith("project deploy") and not any(x.startswith("--dry-run") for x in f) \
                and "validate" not in sub and str(method.get("autonomy") or "") == "strict":
            asks.append("With strict autonomy, every deployment waits for the approver's OK on the diff (%s)."
                        % (method.get("approver") or "the project's approver"))
    if asks:
        return "ask", " ".join(asks)
    return None, ""


def main():
    try:
        event = json.load(sys.stdin)
        command = (event.get("tool_input") or {}).get("command", "")
        decision, reason = decide(command, event.get("cwd") or os.getcwd())
    except Exception:  # a failure of the guard blocks nothing
        return 0
    if decision:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": decision,
                                                 "permissionDecisionReason": reason}}, ensure_ascii=False))
    return 0


def self_test():
    failures = []
    with tempfile.TemporaryDirectory() as tmp:
        poc = os.path.join(tmp, "poc")
        os.makedirs(os.path.join(poc, "force-app"))
        cfg = os.path.join(poc, "sdd.config.json")

        def write(data):
            with open(cfg, "w", encoding="utf-8") as fh:
                fh.write(data if isinstance(data, str) else json.dumps(data))
        # A 0.3.0 config, with Spanish keys and values: the aliases must read it as the English one.
        write({"org_alias": "poc-demo", "metodo": {"autonomia": "estricta", "aprobador": "Ana"}})
        inside, outside = os.path.join(poc, "force-app"), tmp
        os.makedirs(os.path.join(poc, "force-app", "..", "..", "other"), exist_ok=True)
        with open(os.path.join(tmp, "other", "sdd.config.json"), "w", encoding="utf-8") as fh:
            json.dump({"org_alias": "other-demo"}, fh)
        cases = [
            ("another org with -o", "sf project deploy start -o beta-demo --json", inside, "deny"),
            ("another org with --target-org=", "sf data query -q 'SELECT Id FROM Account' --target-org=beta-demo",
             inside, "deny"),
            ("another org in a compound command", "ls && sf org display --target-org beta-demo --json", inside, "deny"),
            ("sfdx with -u", "sfdx force:source:deploy -p force-app -u beta-demo", inside, "deny"),
            ("inside $(...)", "RES=$(sf project deploy start -o beta-demo --json)", inside, "deny"),
            ("backticks", "echo `sf org display -o beta-demo --json`", inside, "deny"),
            ("npx sf", "npx sf data query -q 'SELECT Id FROM Account' -o beta-demo", inside, "deny"),
            ("time and sudo", "time sudo sf apex run -f x.apex -o beta-demo", inside, "deny"),
            ("in parentheses", "(cd force-app && sf project deploy start -o beta-demo)", inside, "deny"),
            ("bash -c", "bash -c 'sf project deploy start --target-org beta-demo'", inside, "deny"),
            ("-o attached", "sf project deploy start -obeta-demo", inside, "deny"),
            ("repeated --target-org", "sf project deploy start --target-org poc-demo --target-org beta-demo", inside,
             "deny"),
            ("SF_TARGET_ORG in the command", "SF_TARGET_ORG=beta-demo sf project deploy start", inside, "deny"),
            ("export SF_TARGET_ORG", "export SF_TARGET_ORG=beta-demo && sf data query -q 'SELECT Id FROM User'", inside,
             "deny"),
            ("alias set of the project's alias", "sf alias set poc-demo=other@example.com", inside, "deny"),
            ("cd into the project from the parent folder", "cd poc && sf project deploy start -o beta-demo", tmp,
             "deny"),
            ("read without --target-org", "sf data query -q 'SELECT Id FROM Account' --json", inside, "deny"),
            ("deploy without --target-org", "sf project deploy start --source-dir force-app --json", inside, "deny"),
            ("change the local target-org to another", "sf config set target-org beta-demo", inside, "deny"),
            ("dry-run with its org", "sf project deploy start --dry-run --target-org poc-demo --json", inside, None),
            ("read with its org", "RES=$(sf data query -q 'SELECT Id FROM Account' -o poc-demo --json)", inside, None),
            ("deploy with its org, strict autonomy", "sf project deploy start --target-org poc-demo --json", inside,
             "ask"),
            ("publish with its org inside $(...)", "X=$(sf agent publish authoring-bundle --api-name A -o poc-demo)",
             inside, "ask"),
            ("local command without an org", "sf org list --json && sf --version && sf config get target-org", inside,
             None),
            ("login of its alias", "sf org login web --alias poc-demo", inside, None),
            ("not sf", "echo sf project deploy start -o beta-demo", inside, None),
            ("several lines with \\",
             "sf project deploy start \\\n  --source-dir force-app \\\n  --target-org beta-demo", inside, "deny"),
            ("delete over several lines", "sf data delete record \\\n -s Account -i 001 \\\n -o beta-demo", inside,
             "deny"),
            ("npx @salesforce/cli", "npx @salesforce/cli project deploy start -o beta-demo", inside, "deny"),
            ("sudo -u user", "sudo -u ana sf project deploy start -o beta-demo", inside, "deny"),
            ("xargs with a placeholder", "echo beta-demo | xargs -I{} sf project deploy start -o {}", inside, "deny"),
            ("undeclared dev hub", "sf org create scratch -f x.json --target-dev-hub other-hub -a s1", inside, "deny"),
            ("cd out of the project", "cd /tmp && sf project deploy start -o beta-demo", inside, "deny"),
            ("parentheses inside single quotes", "git commit -m 'fix (sf project deploy start -o beta-demo)'",
             inside, None),
            ("SOQL with parentheses", "sf data query -q \"SELECT Id FROM Account WHERE Id IN (SELECT AccountId FROM "
             "Contact)\" -o poc-demo --json", inside, None),
            ("$(...) inside double quotes", 'echo "$(sf org display -o beta-demo --json)"', inside, "deny"),
            ("help", "sf project deploy start --help", inside, None),
            ("for … do sf", "for i in 1 2; do sf project deploy start -o beta-demo; done", inside, "deny"),
            ("while … do sf", "while true; do sf data query -q 'SELECT Id FROM User' -o beta-demo; done", inside,
             "deny"),
            ("if … then sf", "if true; then sf apex run -f x.apex -o beta-demo; fi", inside, "deny"),
            ("if sf …", "if sf org display -o beta-demo --json; then echo ok; fi", inside, "deny"),
            ("! sf", "! sf project deploy start -o beta-demo", inside, "deny"),
            ("npx @salesforce/cli@latest", "npx @salesforce/cli@latest project deploy start -o beta-demo", inside,
             "deny"),
            ("$(true && sf …) in quotes", 'X="$(true && sf org display -o beta-demo)"', inside, "deny"),
            ("$(cd x; sf …) in quotes", 'X="$(cd force-app; sf org display -o beta-demo)"', inside, "deny"),
            ("shell alias or $S", "S=sf; $S project deploy start -o beta-demo", inside, "deny"),
            ("xargs -I{} with a placeholder, critical", "echo x | xargs -I{} sf project deploy start -o {}", inside,
             "deny"),
            ("$ORG resolved to the project's org", "ORG=poc-demo; sf data query -q 'SELECT Id FROM User' -o $ORG",
             inside, None),
            ("unresolved ${ORG}", "sf data query -q 'SELECT Id FROM User' -o ${ORG}", inside, "deny"),
            ("data create with -v (--values)", "sf data create record -s Account -v \"Name='Acme'\" -o poc-demo",
             inside, None),
            ("code-analyzer without an org", "sf code-analyzer run --workspace force-app", inside, None),
            ("project convert without an org", "sf project convert source -d mdapi", inside, None),
            ("another org's --target-org in a non-sf command", "my-script.sh --target-org beta-demo", inside, "deny"),
            ("variable that is not sf", "$PYTHON script.py -o out.json", inside, None),
            ("org in double quotes at the end", 'sf data query -q "SELECT Id FROM User" -o "poc-demo"', inside, None),
            ("${ORG} in double quotes", 'export ORG=poc-demo && sf data query -q "SELECT Id FROM User" -o "${ORG}"',
             inside, None),
            ("another org in double quotes", 'sf data query -q "SELECT Id FROM User" -o "beta-demo"', inside, "deny"),
            ("scratch without a dev hub", "sf org create scratch -f config/project-scratch-def.json -a s1", inside,
             "deny"),
            ("unknown variable with an sf topic", "$CLI project deploy start -o beta-demo", inside, "deny"),
            ("--dry-run=true", "sf project deploy start --dry-run=true -o poc-demo", inside, None),
            ("outside an sdd project", "sf project deploy start -o beta-demo", outside, None),
            ("from another project's session", "cd ../../other && sf project deploy start -o other-demo", inside,
             "deny"),
        ]
        for name, command, cwd, expected in cases:
            got = decide(command, cwd)[0]
            if got != expected:
                failures.append("%s: %r (expected %r)" % (name, got, expected))
        os.makedirs(os.path.join(poc, ".sf"))
        with open(os.path.join(poc, ".sf", "config.json"), "w", encoding="utf-8") as fh:
            json.dump({"target-org": "poc-demo"}, fh)
        if decide("sf apex run --file x.apex", inside)[0] is not None:
            failures.append("with the project's local target-org, a command without -o is denied")
        write({"org_alias": "poc-demo", "metodo": {"autonomia": "critico"}})
        if decide("sf project deploy start --target-org poc-demo", inside)[0] is not None:
            failures.append("with autonomy critico, a deploy to its org asks for confirmation")
        # CA-VOC-01.4: English keys and values decide the same as the 0.3.0 ones
        for method, expected in (({"autonomy": "strict", "approver": "Ana"}, "ask"), ({"autonomy": "critical"}, None)):
            write({"org_alias": "poc-demo", "method": method})
            d = decide("sf project deploy start --target-org poc-demo", inside)
            if d[0] != expected or (expected and "Ana" not in d[1]):
                failures.append("with method %r, a deploy to its org gives %r (expected %r)" % (method, d[0], expected))
        # Review round 12, F-001: a 0.3.0 config that gains an English «method» keeps its «metodo» values
        write({"org_alias": "poc-demo", "metodo": {"autonomia": "estricta", "aprobador": "Ana"},
               "method": {"language": "es"}})
        d = decide("sf project deploy start --target-org poc-demo", inside)
        if d[0] != "ask" or "Ana" not in d[1]:
            failures.append("with «metodo» (strict) plus an English «method», a deploy gives %r, not ask (F-001)" % d[0])
        # CA-LIG-01.3 and 01.4: in light, publish, activate and deploy to its org do not ask; another org is still denied
        write({"org_alias": "poc-demo", "metodo": {"perfil": "ligero", "autonomia": "estricta"}})
        for command, expected in (("sf agent publish authoring-bundle --api-name A --target-org poc-demo --json", None),
                                  ("sf agent activate --api-name A --target-org poc-demo --json", None),
                                  ("sf project deploy start --source-dir force-app --target-org poc-demo --json", None),
                                  ("sf agent publish authoring-bundle --api-name A --target-org beta-demo", "deny"),
                                  ("sf project deploy start --source-dir force-app -o beta-demo --json", "deny")):
            got = decide(command, inside)[0]
            if got != expected:
                failures.append("light: %r gives %r (expected %r)" % (command, got, expected))
        write({"org_alias": "poc-demo", "method": {"profile": "full", "autonomy": "critical"}})
        if decide("sf agent activate --api-name A --target-org poc-demo", inside)[0] != "ask":
            failures.append("full: activate in its org does not ask (CA-LIG-01.3)")
        write("{ not json")
        if decide("sf data query -q 'SELECT Id FROM User' -o poc-demo", inside)[0] != "deny":
            failures.append("with a corrupt sdd.config.json, a command that touches an org is not denied")
        if decide("sf org list", inside)[0] is not None:
            failures.append("with a corrupt sdd.config.json, a local command is denied")
    for f in failures:
        print("FAIL:", f)
    print("self-test: %s" % ("OK" if not failures else "%d failures" % len(failures)))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in P.argv(sys.argv[1:]) else main())
