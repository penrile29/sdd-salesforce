#!/usr/bin/env python3
"""Generates the sdd-salesforce method structure in a project (skill sdd-bootstrap).

Copies the templates in ../assets/ to the target, replaces the {{KEY}} placeholders with the interview answers and
resolves the conditional blocks (inline or on lines of their own; not nested):

    <!-- if autonomy=critical -->…<!-- end if -->      the answer has that value
    <!-- if language -->…<!-- end if -->               the answer is given

The project gets the «en» document vocabulary (method.vocabulary in sdd.config.json): the templates carry its headings
and fields, the ones check-traceability reads.

It never overwrites. If any file it would generate already exists, it writes nothing, lists the conflicts and exits
with 2, unless --add-missing is given, which writes only what is missing. Two exceptions:
- .gitignore is merged: the missing lines are appended, each with the comment of its group;
- README.md is replaced with --replace-readme (the skill passes it after asking); without the flag, a README from
  `sf project generate` is one more conflict.

If the target already has the seed decision (also with its 0.2/0.3 name), its date and its file win: no copy with
today's date is created, and what is generated links to the existing one.

It runs no git or sf commands: the skill does that.

Usage:
    python3 bootstrap.py --target <path> --answers <answers.json> [--dry-run] [--add-missing] [--replace-readme]
                        [--json]
    python3 bootstrap.py --self-test

answers.json holds the interview answers:
    {"project": "…", "client": "…", "org": "<alias>", "expiry": "YYYY-MM-DD, «no expiry» or «to be confirmed»",
     "approver": "…", "profile": "full|light (optional, full)", "autonomy": "strict|critical (light: critical)",
     "areas": ["agentforce", …], "client_sources": "…", "internal_only": "…", "channels": "…",
     "date": "YYYY-MM-DD (optional)", "language": "language of the documents, e.g. «es» (optional)",
     "browser": true|false (optional; by default, true if an area of the catalog's «browser.areas» is planned)}
    All values are text, except areas (a list of texts), and they cannot contain double quotes, backslashes or line
    breaks (they would break the frontmatter). A null counts as a missing key. The Spanish keys and values of 0.2 and
    0.3 are accepted as aliases (sdd_vocab.ANSWER_KEYS); if a key comes in both languages, the English one wins with a
    warning. With «profile» «light», the autonomy is «critical» (another one is ignored with a warning). With «browser»,
it also writes .mcp.json with the pinned Playwright MCP (skills-by-area.json, «browser»); an existing .mcp.json without
a «playwright» server is merged.

Exit code: 0 if it generates (or dry-runs with no conflicts); 2 if there are conflicts or the answers are not valid; 1
if something is missing from the plugin.
"""

import argparse
import datetime
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "sdd-method" / "scripts"))
import sdd_vocab as V  # noqa: E402

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets"
PLUGIN = HERE.parent.parent.parent
VOCABULARY = "en"


def browser_catalog():
    """The «browser» entry of the catalog: package, pinned version, Chromium revision and areas."""
    try:
        b = json.loads(CATALOG.read_text(encoding="utf-8")).get("browser") or {}
    except (OSError, ValueError):
        b = {}
    return b if isinstance(b, dict) else {}


def mcp_server():
    """The «playwright» server of the project's .mcp.json: Playwright's Chromium, a profile and an output per project."""
    b = browser_catalog()
    package = "%s@%s" % (b.get("package") or "@playwright/mcp", b.get("version") or "latest")
    return {"type": "stdio", "command": "npx",
            "args": ["-y", package, "--browser", "chromium", "--user-data-dir", ".playwright/profile",
                     "--output-dir", ".playwright/output"]}


def plugin_version():
    try:
        return str(json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")).get("version") or "")
    except (OSError, ValueError):
        return ""

REQUIRED = ["project", "client", "org", "expiry", "approver"]
TEXTS = REQUIRED + ["autonomy", "profile", "client_sources", "internal_only", "channels", "date", "language"]
KNOWN = set(TEXTS) | {"areas", "browser"}
CATALOG = PLUGIN / "skills" / "sdd-method" / "scripts" / "skills-by-area.json"
MCP = ".mcp.json"
# Default answers: they end up in the generated files.
DEFAULTS = {
    "areas": [],
    "client_sources": "client documentation",
    "internal_only": "none for now",
    "channels": "none for now; added with a decision",
}
SEED = "001_adopt-sdd-salesforce.md"
SFDX_README = "Salesforce DX Project"

BLOCK = re.compile(r"^[ \t]*<!-- if (\w+)(?:=([\w-]+))? -->[ \t]*\n(.*?)^[ \t]*<!-- end if -->[ \t]*\n",
                   re.MULTILINE | re.DOTALL)
INLINE = re.compile(r"<!-- if (\w+)(?:=([\w-]+))? -->(.*?)<!-- end if -->", re.DOTALL)
PLACEHOLDER = re.compile(r"\{\{([A-Z_]+)\}\}")

FORBIDDEN = {'"': "double quotes", "\\": "backslashes", "\n": "line breaks", "\r": "line breaks"}


def check_text(key, value):
    if not isinstance(value, str):
        raise ValueError("\"%s\" must be text, not %s" % (key, type(value).__name__))
    for c, name in FORBIDDEN.items():
        if c in value:
            raise ValueError("\"%s\" cannot contain %s" % (key, name))


def load_answers(answers):
    """The answers with English keys and values, the defaults filled in and a «warnings» list."""
    if not isinstance(answers, dict):
        raise ValueError("the answers must be a JSON object")
    warnings = []
    data, origin = {}, {}  # English key → value, and the key as it came
    raw = {k: v for k, v in answers.items() if v is not None}  # null counts as missing
    # English keys first, so that they win over their Spanish alias.
    for k in sorted(raw, key=lambda x: x in V.ANSWER_KEYS):
        en = V.ANSWER_KEYS.get(k, k)
        if en in data:
            warnings.append("\"%s\" and \"%s\" are the same answer: \"%s\" is used" % (origin[en], k, origin[en]))
            continue
        data[en], origin[en] = raw[k], k
    for k in sorted(set(data) - KNOWN):
        warnings.append("unknown answer \"%s\": ignored" % origin[k])
        del data[k]
    for key in TEXTS:
        if key in data:
            check_text(origin[key], data[key])
    areas = data.get("areas")
    if areas is not None:
        if not isinstance(areas, list):
            raise ValueError("\"%s\" must be a list of texts" % origin["areas"])
        for a in areas:
            check_text(origin["areas"], a)
        data["areas"] = V.areas(areas)
    data["profile"] = V.VALUES["profile"].get(data.get("profile") or "full", data.get("profile") or "full")
    if data["profile"] not in V.PROFILES:
        raise ValueError("profile must be %s, not \"%s\"" % (" or ".join(V.PROFILES), raw[origin["profile"]]))
    if data["profile"] == "light":
        given = V.VALUES["autonomy"].get(data.get("autonomy"), data.get("autonomy"))
        if given not in (None, "", "critical"):
            warnings.append("\"%s\" is \"%s\", and the light profile implies the critical autonomy: critical is used"
                            % (origin["autonomy"], raw[origin["autonomy"]]))
        data["autonomy"] = "critical"
    missing = [k for k in REQUIRED + ["autonomy"] if not str(data.get(k, "")).strip()]
    if missing:
        raise ValueError("missing answers: " + ", ".join(missing))
    data["autonomy"] = V.VALUES["autonomy"].get(data["autonomy"], data["autonomy"])
    if data["autonomy"] not in V.AUTONOMIES:
        raise ValueError("autonomy must be %s, not \"%s\"" % (" or ".join(V.AUTONOMIES), raw[origin["autonomy"]]))
    if "browser" in data and not isinstance(data["browser"], bool):
        raise ValueError("\"%s\" must be true or false" % origin["browser"])
    r = dict(DEFAULTS)
    r.update({k: v for k, v in data.items() if v not in (None, "")})
    if "language" in r:
        r["language"] = r["language"].strip()
        if not r["language"]:
            del r["language"]
    r["mode"] = "light" if r["profile"] == "light" else r["autonomy"]  # what the templates' blocks choose by
    if "browser" not in r:
        ui = set(browser_catalog().get("areas") or [])
        r["browser"] = bool(ui & set(r["areas"]))
    r["date"] = r.get("date") or datetime.date.today().isoformat()
    try:
        datetime.date.fromisoformat(r["date"])
    except ValueError:
        raise ValueError("\"%s\" must be YYYY-MM-DD, not \"%s\"" % (origin.get("date", "date"), r["date"]))
    r["warnings"] = warnings
    return r


def seed_name(r):
    return r.get("seed") or "%s-%s" % (r["date"], SEED)


def placeholders(r):
    if r["profile"] == "light":
        escalation = "Only what is critical is escalated, with the light profile below"
    elif r["autonomy"] == "critical":
        escalation = ("Only what is critical is escalated: user experience, approved requirements, stack or a "
                      "blocker; the orchestrator decides and records the rest")
    else:
        escalation = "Every gate, including the one for each Execution step, waits for the approver's OK"
    return {
        "PROJECT": r["project"], "CLIENT": r["client"], "ORG": r["org"], "EXPIRY": r["expiry"],
        "APPROVER": r["approver"], "DATE": r["date"], "CLIENT_SOURCES": r["client_sources"],
        "INTERNAL_ONLY": r["internal_only"], "CHANNELS": r["channels"], "ESCALATION": escalation,
        "AREAS": ", ".join(r["areas"]) or "to be decided in the discovery",
        "AUTONOMY": r["autonomy"], "VERSION": plugin_version() or "(no version)",
        "LANGUAGE": r.get("language", ""), "SEED": seed_name(r), "PROFILE": r["profile"],
        "BROWSER_VERSION": "%s@%s" % (browser_catalog().get("package") or "@playwright/mcp",
                                      browser_catalog().get("version") or "latest"),
    }


def render(text, r, source):
    def pick(m):
        value = r.get(m.group(1))
        keep = bool(value) if m.group(2) is None else str(value) == m.group(2)
        return m.group(3) if keep else ""

    text = BLOCK.sub(pick, text)
    text = INLINE.sub(pick, text)
    if "<!-- if " in text or "<!-- end if -->" in text:
        raise ValueError("%s: conditional block not closed or nested" % source)
    values = placeholders(r)
    unknown = sorted(set(PLACEHOLDER.findall(text)) - set(values))
    if unknown:
        raise ValueError("%s: placeholders with no value: %s" % (source, ", ".join(unknown)))
    return PLACEHOLDER.sub(lambda m: values[m.group(1)], text)


def plan(r):
    """List of (path relative to the target, kind, source). Kinds: template, copy, empty, config."""
    step_reports = V.traceability_defaults(VOCABULARY)["paths"]["step_reports"]
    p = [("CLAUDE.md", "template", ASSETS / "CLAUDE.md.tmpl"),
         ("README.md", "template", ASSETS / "README.md.tmpl"),
         (".gitignore", "template", ASSETS / "gitignore.tmpl"),
         ("knowledge/README.md", "template", ASSETS / "knowledge/README.md"),
         ("knowledge/discovery/README.md", "template", ASSETS / "knowledge/discovery/README.md"),
         ("knowledge/specs/.gitkeep", "empty", None),
         ("knowledge/gotchas/.gitkeep", "empty", None)]
    for f in sorted((ASSETS / "decisions").glob("*.md")):
        name = seed_name(r) if f.name == SEED else "%s-%s" % (r["date"], f.name)
        p.append(("knowledge/decisions/" + name, "template", f))
    for f in sorted((ASSETS / "delivery-plan").rglob("*")):
        if f.is_file():
            p.append(("docs/delivery-plan/" + f.relative_to(ASSETS / "delivery-plan").as_posix(), "template", f))
    p += [(step_reports + "/.gitkeep", "empty", None),
          ("docs/baseline/.gitkeep", "empty", None),
          ("docs/client/.gitkeep", "empty", None),
          ("reviews/.gitkeep", "empty", None),
          ("sdd.config.json", "config", None)]
    if r.get("browser"):
        p.append((MCP, "mcp", None))
    return p


def content(kind, source, r, target_rel):
    if kind == "empty":
        return ""
    if kind == "copy":
        return source.read_text(encoding="utf-8")
    if kind == "mcp":
        return json.dumps({"mcpServers": {"playwright": mcp_server()}}, ensure_ascii=False, indent=2) + "\n"
    if kind == "config":
        # Minimal: the defaults of the checks live in the plugin scripts (sdd-method/scripts/).
        method = {"plugin": "sdd-salesforce", "version": plugin_version(), "approver": r["approver"],
                  "profile": r["profile"], "autonomy": r["autonomy"], "vocabulary": VOCABULARY}
        if r.get("language"):
            method["language"] = r["language"]
        cfg = {"project": r["project"], "org_alias": r["org"], "areas": r["areas"], "method": method,
               "environment": {"browser": bool(r.get("browser"))}}
        return json.dumps(cfg, ensure_ascii=False, indent=2) + "\n"
    return render(source.read_text(encoding="utf-8"), r, target_rel)


def merge_gitignore(current, new):
    """Appends the template lines that are missing, each preceded by the comment of its group (once)."""
    lines = set(current.splitlines())
    missing, comment = [], None
    for l in new.splitlines():
        if not l.strip():
            continue
        if l.lstrip().startswith("#"):
            comment = l
            continue
        if l in lines:
            continue
        if comment is not None:
            if comment not in lines:
                missing.append(comment)
            comment = None
        missing.append(l)
    if not missing:
        return None
    sep = "" if current.endswith("\n") or not current else "\n"
    return current + sep + "\n# sdd-salesforce\n" + "\n".join(missing) + "\n"


def merge_mcp(current):
    """The project's .mcp.json with the «playwright» server added; None if it already has one, "" if it is not valid."""
    try:
        data = json.loads(current)
    except ValueError:
        return ""
    servers = data.get("mcpServers") if isinstance(data, dict) else None
    if not isinstance(servers, dict):
        return ""
    if "playwright" in servers:
        return None
    servers["playwright"] = mcp_server()
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def existing_seed(target):
    """File name of the seed decision the target already has (current or 0.2/0.3 name), or None."""
    found = []
    for name in (SEED, V.LEGACY_SEED):
        found += [f.name for f in (target / "knowledge/decisions").glob("????-??-??-" + name)]
    return sorted(found)[0] if found else None


def bootstrap(target, r, dry_run=False, add_missing=False, replace_readme=False):
    target = Path(target).resolve()
    res = {"target": str(target), "create": [], "merge": [], "replace": [], "conflicts": [], "skipped": [],
           "warnings": list(r.get("warnings", [])), "sfdx_readme": False}
    seed = existing_seed(target)
    if seed:
        if seed[:10] != r["date"]:
            res["warnings"].append("the target's seed decision is dated %s: that date is used" % seed[:10])
        if seed.endswith(V.LEGACY_SEED):
            res["warnings"].append("the target has the seed decision of 0.2/0.3 (%s): it is kept and linked" % seed)
        r = dict(r, date=seed[:10], seed=seed)
    work = []
    for rel, kind, source in plan(r):
        if source is not None and not source.exists():
            raise FileNotFoundError("missing from the plugin: %s" % source)
        text = content(kind, source, r, rel)
        path = target / rel
        if not path.exists():
            res["create"].append(rel)
            work.append((path, text))
        elif rel == ".gitignore":
            merged = merge_gitignore(path.read_text(encoding="utf-8"), text)
            if merged is not None:
                res["merge"].append(rel)
                work.append((path, merged))
        elif rel == MCP:
            merged = merge_mcp(path.read_text(encoding="utf-8"))
            if merged:
                res["merge"].append(rel)
                work.append((path, merged))
            elif merged == "":
                (res["skipped"] if add_missing else res["conflicts"]).append(rel)
            elif json.loads(path.read_text(encoding="utf-8"))["mcpServers"]["playwright"] != mcp_server():
                res["warnings"].append("%s already has a «playwright» server different from the pinned one (%s): it "
                                       "is kept" % (rel, mcp_server()["args"][1]))
        elif rel == "README.md" and SFDX_README in path.read_text(encoding="utf-8") and replace_readme:
            res["replace"].append(rel)
            work.append((path, text))
        elif kind == "empty":
            continue
        elif add_missing:
            res["skipped"].append(rel)
        else:
            res["conflicts"].append(rel)
            if rel == "README.md" and SFDX_README in path.read_text(encoding="utf-8"):
                res["sfdx_readme"] = True
    if res["conflicts"] or dry_run:
        return res
    for path, text in work:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        if path.suffix == ".py":
            path.chmod(0o755)
    return res


# --- Self-test -----------------------------------------------------------------------------------------------------

# CA-VOC-01.1: a minimal spec, a step and its traceability rows in the «en» vocabulary, added to a fresh project.
_SPEC = """---
title: Orders in the portal
description: Self-test spec
updated_at: 2026-11-05
status: Ready
author: Ann Smith + agent
tags: [orders]
---

# Orders in the portal

# Part 1 · Requirements

## Requirements

### R-ORD-01 — The user sees their orders
- Source: self-test
- Priority: P0 · Status: Ready
- AC-ORD-01.1 — Given a user with orders, when they open "My orders", then they see the list (Apex test).
- AC-ORD-01.2 — Given a user without orders, when they open "My orders", then they see the notice "No orders yet"
  (Apex test).
- Open items: none.

# Part 2 · Design

## Verified with
Not applicable: self-test spec.

## Change log

| Date | Type | IDs | Before → after | Changes behaviour? | Origin | Approval | Commit |
|---|---|---|---|---|---|---|---|
"""
_STEPS = """# Wave 1

### W1.1 — Order list
- **Scope:** portal · `force-app/main/default/classes/Orders*`
- **Builds:** the controller of "My orders"
- **Satisfies:** R-ORD-01. **Source:** spec 001
- **Depends on:** none
- **Parallel with:** none
- **Test first:** yes — `OrdersControllerTest`
- **Skill:** `platform-apex-generate`
- **Level:** 2
- **Size:** S
"""
_TRACE_HEAD = ("## P0 AC\n\n| Requirement | AC | Source and status | Step | Verification | Evidence state |\n"
               "|---|---|---|---|---|---|\n")
_TRACE_ROWS = ("| R-ORD-01 | AC-ORD-01.1 | spec 001 · Ready | W1.1 | Apex test | planned |\n"
               "| R-ORD-01 | AC-ORD-01.2 | spec 001 · Ready | W1.1 | Apex test | planned |\n")
# CA-LIG-01.6 and CA-NAV-01.5: a flat step of the light profile (no Size, waves or Test first) with a browser check.
_FLAT_STEP = """### W1.1 — Order list page
- **Satisfies:** R-ORD-01. **Source:** spec 001
- **Touches:** `force-app/main/default/lwc/orderList/`
- **Skill:** `experience-lwc-generate`
- **Done when:** AC-ORD-01.1 browser check: given a user with orders, the list is shown.
"""
_FLAT_ROWS = ("| R-ORD-01 | AC-ORD-01.1 | spec 001 · Ready | W1.1 | browser check | planned |\n"
              "| R-ORD-01 | AC-ORD-01.2 | spec 001 · Ready | W1.1 | browser check | planned |\n")
_FLAT_REPORT = """# W1.1 — step report

## Verification cases
- AC-ORD-01.1 — browser check: as a user with orders, "My orders" shows the list (screenshot in evidence/W1.1/).
- AC-ORD-01.2 — browser check: as a user without orders, the notice "No orders yet" is shown.
"""
_SCOPES_HEAD = "| Scope | Steps | Own folders and prefixes | Consumes | Exposes |\n|---|---|---|---|---|\n"
_SCOPES_ROW = "| portal | W1.1 | `classes/Orders*` | — | — |\n"


def check_traceability(project, *options):
    """(exit code, output) of check-traceability.py on the project, in a subprocess."""
    script = PLUGIN / "skills" / "sdd-method" / "scripts" / "check-traceability.py"
    p = subprocess.run([sys.executable, str(script), "--project", str(project)] + list(options), capture_output=True,
                       text=True, timeout=120)
    return p.returncode, p.stdout + p.stderr


def self_test():
    base = {"project": "Order portal", "client": "ACME", "org": "acme-demo", "expiry": "2026-12-31",
            "approver": "Ann Smith", "autonomy": "critical", "areas": ["agentforce"], "date": "2026-11-05"}
    seed = "knowledge/decisions/2026-11-05-" + SEED
    failures = []

    def check(cond, msg):
        if not cond:
            failures.append(msg)

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        # CA-BOOT-01.1: empty folder
        d1 = tmp / "empty"
        res = bootstrap(d1, load_answers(base))
        check(not res["conflicts"], "empty: conflicts in an empty folder")
        for rel in ["CLAUDE.md", ".gitignore", seed, "docs/delivery-plan/status.md", "docs/delivery-plan/integration.md",
                    "docs/delivery-plan/step-reports/.gitkeep", "docs/client/.gitkeep", "sdd.config.json"]:
            check((d1 / rel).exists(), "empty: missing " + rel)
        # CA-BOOT-02.1: 20 files or fewer, no method scripts or decisions, one seed and the adopted version
        generated = [f for f in d1.rglob("*") if f.is_file()]
        check(len(generated) <= 20, "v0.2: generates %d files (at most 20)" % len(generated))
        check(not (d1 / "scripts").exists(), "v0.2: copies scripts/ into the project")
        check([f.name for f in (d1 / "knowledge/decisions").glob("*.md")] == [Path(seed).name],
              "v0.2: there is not exactly one seed")
        for moved in ["agent-brief.md", "orchestrator-prompt.md", "communication-protocol.md"]:
            check(not (d1 / "docs/delivery-plan" / moved).exists(), "v0.2: %s is still in the project" % moved)
        # CA-VOC-01.1: English keys, method.vocabulary «en» and no language when it is not given (CA-IDI-01.5)
        cfg = json.loads((d1 / "sdd.config.json").read_text())
        check(sorted(cfg) == ["areas", "environment", "method", "org_alias", "project"],
              "CA-VOC-01.1: unexpected keys in sdd.config.json: %s" % sorted(cfg))
        check(cfg.get("environment") == {"browser": False} and not (d1 / MCP).exists(),
              "CA-NAV-01.1: agentforce only, without «browser»: there is a .mcp.json or environment.browser is not false")
        check(cfg.get("method") == {"plugin": "sdd-salesforce", "version": plugin_version(), "approver": "Ann Smith",
                                    "profile": "full", "autonomy": "critical", "vocabulary": "en"},
              "CA-VOC-01.1: unexpected method section: %s" % cfg.get("method"))
        check(V.vocabulary(cfg) == ("en", None), "CA-VOC-01.1: the config does not read as the «en» vocabulary")
        check(cfg.get("org_alias") == "acme-demo" and cfg.get("areas") == ["agentforce"] and cfg["project"] ==
              "Order portal", "empty: sdd.config.json without project, org or areas")
        # CA-BOOT-02.2: the entry reading (without the core, which the hook injects) is short
        words = sum(len((d1 / r).read_text().split()) for r in
                    ["CLAUDE.md", "docs/delivery-plan/handover.md", "docs/delivery-plan/status.md", seed])
        check(words <= 2000, "v0.2: the project entry has %d words (at most 2000)" % words)
        check("docs/client/" in (d1 / ".gitignore").read_text().splitlines(), "empty: docs/client/ is not ignored")
        for f in d1.rglob("*.md"):
            t = f.read_text()
            check("{{" not in t and "<!-- if " not in t and "<!-- end if" not in t,
                  "empty: unresolved placeholder or block in " + str(f.relative_to(d1)))
        d001 = (d1 / seed).read_text()
        check("escalate to Ann Smith" in d001, "empty: the critical-only escalation is missing")
        check("Strict autonomy:" not in d001, "empty: the strict autonomy block slipped in")
        check("Document language" not in d001 and "Document language" not in (d1 / "CLAUDE.md").read_text(),
              "CA-IDI-01.5: without language, 001 or CLAUDE.md speak of a document language")
        claude = (d1 / "CLAUDE.md").read_text()
        check("[decision 001](%s)" % seed in claude, "empty: CLAUDE.md does not link the seed decision")
        check("«[sdd-salesforce …] sdd project»" in claude, "empty: CLAUDE.md lost the plugin label it must look for")
        # Structural tokens of the «en» vocabulary in the templates
        en = V.traceability_defaults("en")
        status = (d1 / "docs/delivery-plan/status.md").read_text()
        trace = (d1 / "docs/delivery-plan/traceability.md").read_text()
        integ = (d1 / "docs/delivery-plan/integration.md").read_text()
        check("\n## %s\n" % en["status"]["section"] in status and "### Change queue" in status
              and "## Requests and work items" in status, "en: status.md without its headings")
        check("| Step | Scope and session | Branch and commit | State |" in status,
              "en: the «Steps» table of status.md has no state in column 4")
        check("\n## %s\n" % en["sections"]["exclusions"] in trace and "\n## %s " % en["sections"]["steps_without_ac"]
              in trace and _TRACE_HEAD in trace, "en: traceability.md without its sections")
        check("\n## %s" % en["sections"]["scopes"] in integ and "`design-approved`" in integ,
              "en: integration.md without «Scopes» or the design-approved tag")
        code, out = check_traceability(d1)
        check(code == 0, "CA-VOC-01.1: check-traceability on the fresh project exits with %d:\n%s" % (code, out))
        # CA-VOC-01.1: with a minimal spec, a step and their rows, check-traceability exits with 0
        (d1 / "knowledge/specs/2026-11-05-001_orders.md").write_text(_SPEC, encoding="utf-8")
        (d1 / "docs/delivery-plan/implementation/W1.md").write_text(_STEPS, encoding="utf-8")
        (d1 / "docs/delivery-plan/traceability.md").write_text(trace.replace(_TRACE_HEAD, _TRACE_HEAD + _TRACE_ROWS, 1),
                                                               encoding="utf-8")
        code, out = check_traceability(d1)
        check(code == 0 and "ERROR" not in out,
              "CA-VOC-01.1: check-traceability with a spec and a step exits with %d:\n%s" % (code, out))
        # --graph reads the «Scopes» table of integration.md
        check(_SCOPES_HEAD in integ, "en: integration.md without the «Scopes» table")
        (d1 / "docs/delivery-plan/integration.md").write_text(integ.replace(_SCOPES_HEAD, _SCOPES_HEAD + _SCOPES_ROW, 1),
                                                              encoding="utf-8")
        code, out = check_traceability(d1, "--graph")
        check(code == 0 and "ERROR" not in out, "CA-VOC-01.1: --graph with its scope exits with %d:\n%s" % (code, out))
        (d1 / "docs/delivery-plan/integration.md").write_text(integ, encoding="utf-8")
        # Without its rows, the same project fails: the check really reads the en vocabulary of the templates
        (d1 / "docs/delivery-plan/traceability.md").write_text(trace, encoding="utf-8")
        code, out = check_traceability(d1)
        check(code != 0 and "AC-ORD-01.1" in out, "CA-VOC-01.1: without the rows, check-traceability does not fail")
        for f in ["knowledge/specs/2026-11-05-001_orders.md", "docs/delivery-plan/implementation/W1.md"]:
            (d1 / f).unlink()
        # CA-IDI-01.5: with language, method.language and decision 001 record it
        d6 = tmp / "language"
        bootstrap(d6, load_answers(dict(base, language="es")))
        cfg = json.loads((d6 / "sdd.config.json").read_text())
        check(cfg["method"].get("language") == "es" and cfg["method"].get("vocabulary") == "en",
              "CA-IDI-01.5: method.language is not «es»: %s" % cfg["method"])
        check("**Document language:** `es`" in (d6 / seed).read_text(), "CA-IDI-01.5: decision 001 does not record it")
        check("**Document language:** `es`" in (d6 / "CLAUDE.md").read_text(), "CA-IDI-01.5: CLAUDE.md does not say it")
        check(load_answers(dict(base, language="  ")).get("language") is None, "language: a blank one is kept")
        # CA-LIG-01.1: the light profile fixes critical, and CLAUDE.md and 001 say it; every template is still generated
        d8 = tmp / "light"
        r = load_answers(dict(base, profile="light", autonomy="strict"))
        check(r["autonomy"] == "critical" and any("light profile implies" in w for w in r["warnings"]),
              "CA-LIG-01.1: light with strict does not become critical with a warning")
        bootstrap(d8, r)
        cfg = json.loads((d8 / "sdd.config.json").read_text())
        check(cfg["method"]["profile"] == "light" and cfg["method"]["autonomy"] == "critical",
              "CA-LIG-01.1: sdd.config.json of a light project: %s" % cfg["method"])
        check((d8 / "docs/delivery-plan/integration.md").exists(), "light: integration.md is missing")
        claude, d001 = (d8 / "CLAUDE.md").read_text(), (d8 / seed).read_text()
        check("**Profile:** `light`" in claude and "need no OK" in claude, "CA-LIG-01.1: CLAUDE.md does not say light")
        check("Light profile:" in d001 and "Critical-only autonomy:" not in d001 and "Full profile" in d001,
              "CA-LIG-01.1: decision 001 does not record the light profile")
        check("Org versions" in (d8 / "docs/delivery-plan/status.md").read_text(),
              "CA-LIG-01.1: status.md of a light project without its «Org versions» table")
        check(load_answers(dict(base, autonomy=None, profile="ligero"))["autonomy"] == "critical",
              "light: without autonomy it is not critical, or «ligero» is not accepted")
        check("Light profile:" not in (d1 / seed).read_text() and "Org versions" not in
              (d1 / "docs/delivery-plan/status.md").read_text(), "full: the light blocks slipped in")
        try:
            load_answers(dict(base, profile="lite"))
            check(False, "profile: «lite» is accepted")
        except ValueError:
            pass
        # CA-LIG-01.6 and CA-NAV-01.5: the flat plan passes without --graph, and browser check is read in the report
        (d8 / "knowledge/specs/2026-11-05-001_orders.md").write_text(_SPEC, encoding="utf-8")
        (d8 / "docs/delivery-plan/implementation/W1.md").write_text(_FLAT_STEP, encoding="utf-8")
        t8 = (d8 / "docs/delivery-plan/traceability.md").read_text()
        (d8 / "docs/delivery-plan/traceability.md").write_text(t8.replace(_TRACE_HEAD, _TRACE_HEAD + _FLAT_ROWS, 1),
                                                               encoding="utf-8")
        reports = d8 / V.traceability_defaults(VOCABULARY)["paths"]["step_reports"]
        reports.mkdir(parents=True, exist_ok=True)
        code, out = check_traceability(d8)
        check(code == 0 and "ERROR" not in out, "CA-LIG-01.6: the flat plan gives errors without --graph:\n%s" % out)
        (reports / "W1.1.md").write_text(_FLAT_REPORT.replace("- AC-ORD-01.2", "- (pending) AC-ORD-02.9"),
                                         encoding="utf-8")
        code, out = check_traceability(d8, "--step", "W1.1", "--no-review")
        check(code != 0 and "AC-ORD-01.2" in out, "CA-NAV-01.5: a browser check not cited in the report passes:\n%s"
              % out)
        (reports / "W1.1.md").write_text(_FLAT_REPORT, encoding="utf-8")
        code, out = check_traceability(d8, "--step", "W1.1", "--no-review")
        check(code == 0, "CA-NAV-01.5: with the browser checks in the report, --step W1.1 exits with %d:\n%s"
              % (code, out))
        # CA-NAV-01.1: with a UI area (or browser true), .mcp.json with the pinned server and .playwright/ ignored
        d9 = tmp / "browser"
        r = load_answers(dict(base, areas=["lwc"]))
        check(r["browser"] is True, "CA-NAV-01.1: a UI area does not propose the browser by default")
        bootstrap(d9, r)
        mcp = json.loads((d9 / MCP).read_text())["mcpServers"]["playwright"]
        pinned = "%s@%s" % (browser_catalog()["package"], browser_catalog()["version"])
        check(mcp["args"][1] == pinned and "chromium" in mcp["args"] and ".playwright/profile" in mcp["args"],
              "CA-NAV-01.1: .mcp.json without the pinned server: %s" % mcp)
        check(".playwright/" in (d9 / ".gitignore").read_text().splitlines(), "CA-NAV-01.1: .playwright/ is not ignored")
        check(json.loads((d9 / "sdd.config.json").read_text())["environment"] == {"browser": True},
              "CA-NAV-01.1: environment.browser is not true")
        check("## Browser" in (d9 / "CLAUDE.md").read_text(), "CA-NAV-01.1: CLAUDE.md without its Browser section")
        check(load_answers(dict(base, areas=["lwc"], browser=False))["browser"] is False, "browser: false is not kept")
        # An existing .mcp.json without playwright is merged; with --add-missing in an older project, it is added
        (d9 / MCP).write_text(json.dumps({"mcpServers": {"other": {"command": "x"}}}))
        res = bootstrap(d9, r, add_missing=True)
        merged = json.loads((d9 / MCP).read_text())["mcpServers"]
        check(MCP in res["merge"] and "other" in merged and "playwright" in merged,
              "browser: an existing .mcp.json is not merged: %s" % res)
        res = bootstrap(d9, r, add_missing=True)
        check(MCP not in res["merge"] + res["conflicts"], "browser: a .mcp.json with playwright is touched again")
        try:
            load_answers(dict(base, browser="yes"))
            check(False, "browser: a text is accepted")
        except ValueError:
            pass
        # The strict autonomy (full profile)
        d2 = tmp / "with-profile"
        res = bootstrap(d2, load_answers(dict(base, profile="full", autonomy="strict")))
        d001 = (d2 / seed).read_text()
        check("Strict autonomy:" in d001 and "Critical-only autonomy:" not in d001,
              "strict: the strict autonomy block is missing")
        check("Every gate, including" in (d2 / "CLAUDE.md").read_text(), "strict: CLAUDE.md without its escalation")
        # Answers of 0.2 and 0.3: Spanish keys and values are aliases
        legacy = {"proyecto": "Order portal", "cliente": "ACME", "org": "acme-demo", "caducidad": "2026-12-31",
                  "aprobador": "Ann Smith", "autonomia": "estricta", "areas": ["voz"], "fecha": "2026-11-05",
                  "idioma": "es", "perfil": "completo"}
        r = load_answers(legacy)
        check(r["autonomy"] == "strict" and r["areas"] == ["voice"] and r["language"] == "es"
              and r["project"] == "Order portal" and r["date"] == "2026-11-05" and r["profile"] == "full",
              "legacy: Spanish answers not translated: %s" % r)
        d7 = tmp / "legacy"
        bootstrap(d7, r)
        cfg = json.loads((d7 / "sdd.config.json").read_text())
        check(cfg["method"]["autonomy"] == "strict" and cfg["areas"] == ["voice"] and "metodo" not in cfg,
              "legacy: sdd.config.json not in English: %s" % cfg)
        check(load_answers(dict(base, autonomy="critico"))["autonomy"] == "critical", "legacy: «critico» not accepted")
        r = load_answers(dict(base, aprobador="Someone else"))
        check(r["approver"] == "Ann Smith" and any("aprobador" in w for w in r["warnings"]),
              "legacy: with both keys, the English one does not win with a warning")
        r = load_answers(dict(base, colour="blue"))
        check("colour" not in r and any("colour" in w for w in r["warnings"]), "answers: unknown key without warning")
        # CA-BOOT-01.3: does not overwrite an existing CLAUDE.md
        d3 = tmp / "existing"
        d3.mkdir()
        (d3 / "CLAUDE.md").write_text("mine\n")
        res = bootstrap(d3, load_answers(base))
        check(res["conflicts"] == ["CLAUDE.md"], "existing: unexpected conflicts %s" % res["conflicts"])
        check((d3 / "CLAUDE.md").read_text() == "mine\n", "existing: overwrote CLAUDE.md")
        check(not (d3 / "knowledge").exists(), "existing: wrote something despite the conflict")
        res = bootstrap(d3, load_answers(base), add_missing=True)
        check("CLAUDE.md" in res["skipped"] and (d3 / "knowledge/README.md").exists(),
              "existing: --add-missing did not add what was missing")
        # CA-BOOT-01.7 and 01.8: README and .gitignore from sf project generate
        d4 = tmp / "sfdx"
        d4.mkdir()
        (d4 / "README.md").write_text("# Salesforce DX Project: Next Steps\n")
        (d4 / ".gitignore").write_text("# Salesforce cache\n.sf/\n.sfdx/\n# Dependency directories\nnode_modules/\n")
        res = bootstrap(d4, load_answers(base))
        check(res["conflicts"] == ["README.md"] and res["sfdx_readme"],
              "sfdx: without --replace-readme, the README must be the only conflict: %s" % res["conflicts"])
        check((d4 / "README.md").read_text().startswith("# Salesforce DX"), "sfdx: replaced the README without the flag")
        res = bootstrap(d4, load_answers(base), replace_readme=True)
        check("README.md" in res["replace"] and ".gitignore" in res["merge"], "sfdx: did not merge/replace")
        gi = (d4 / ".gitignore").read_text().splitlines()
        check(gi.count(".sfdx/") == 1 and gi.count("node_modules/") == 1, "sfdx: duplicated .gitignore lines")
        check(".vscode/" not in gi, "sfdx: the .gitignore takes .vscode/ out of git")
        for i, l in enumerate(gi):
            if l.startswith("#") and i > 4 and l != "# sdd-salesforce":
                check(i + 1 < len(gi) and gi[i + 1].strip() and not gi[i + 1].startswith("#"),
                      "sfdx: comment without its lines in the .gitignore: %s" % l)
        # CA-BOOT-01.6: running again with --add-missing on another day does not duplicate the seed decision
        (d1 / "CLAUDE.md").unlink()
        res = bootstrap(d1, load_answers(dict(base, date="2026-11-20")), add_missing=True)
        check(not any("2026-11-20" in rel for rel in res["create"]), "another day: created a seed with the new date")
        check(res["create"] == ["CLAUDE.md"], "another day: created %s" % res["create"])
        claude = (d1 / "CLAUDE.md").read_text()
        check("2026-11-05-001_" in claude and "2026-11-20" not in claude,
              "another day: the regenerated CLAUDE.md does not link the existing seed")
        check(len(list((d1 / "knowledge/decisions").glob("*.md"))) == 1, "another day: there is not exactly one seed")
        # The same with the seed of a 0.2/0.3 project: it is kept, linked and not duplicated
        d8 = tmp / "legacy-seed"
        old = "knowledge/decisions/2026-10-01-" + V.LEGACY_SEED
        (d8 / old).parent.mkdir(parents=True)
        (d8 / old).write_text("old seed\n")
        res = bootstrap(d8, load_answers(base), add_missing=True)
        check(old in res["skipped"] and not any(SEED in rel for rel in res["create"]),
              "legacy seed: created a new seed next to it: %s" % res["create"])
        check("](%s)" % old in (d8 / "CLAUDE.md").read_text(), "legacy seed: CLAUDE.md does not link it")
        check(any(V.LEGACY_SEED in w for w in res["warnings"]), "legacy seed: no warning")
        # CA-BOOT-01.9: answers with wrong types or characters that break the frontmatter
        for key, value in [("autonomy", ["critical"]), ("expiry", 20261231), ("areas", "flow"),
                           ("approver", 'Ann "the boss"'), ("client", "ACME\nInc."), ("date", "tomorrow"),
                           ("approver", None), ("project", "Order\\portal"), ("language", 7),
                           ("aprobador", 'Ann "the boss"')]:
            try:
                load_answers(dict(legacy if key in V.ANSWER_KEYS else base, **{key: value}))
                failures.append("answers: accepted %s=%r" % (key, value))
            except ValueError as e:
                check(key in str(e), "answers: the error does not name \"%s\": %s" % (key, e))
        d5 = tmp / "colon"
        bootstrap(d5, load_answers(dict(base, approver="Ann Smith: director")))
        check('author: "Ann Smith: director + sdd-salesforce"' in (d5 / seed).read_text(),
              "colon: the author of 001 is not quoted")
        # Invalid answers
        try:
            load_answers(dict(base, autonomy="total"))
            failures.append("answers: accepted an invalid autonomy")
        except ValueError:
            pass
    for f in failures:
        print("FAIL:", f)
    print("self-test: %s" % ("OK" if not failures else "%d failures" % len(failures)))
    return 1 if failures else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--target")
    ap.add_argument("--answers")
    ap.add_argument("--dry-run", action="store_true", help="writes nothing: says what it would do")
    ap.add_argument("--add-missing", action="store_true", help="writes only what is missing")
    ap.add_argument("--replace-readme", action="store_true",
                    help="replaces the stock README from sf project generate (ask first)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(V.argv(sys.argv[1:]))
    if a.self_test:
        return self_test()
    if not a.target or not a.answers:
        ap.error("--target and --answers are required")
    try:
        r = load_answers(json.loads(Path(a.answers).read_text(encoding="utf-8")))
        res = bootstrap(a.target, r, dry_run=a.dry_run, add_missing=a.add_missing, replace_readme=a.replace_readme)
    except ValueError as e:
        print("error:", e, file=sys.stderr)
        return 2
    except FileNotFoundError as e:
        print("error:", e, file=sys.stderr)
        return 1
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        for warning in res["warnings"]:
            print("warning:", warning)
        for key in ["create", "merge", "replace", "skipped", "conflicts"]:
            for rel in res[key]:
                print("%-10s %s" % (key, rel))
        if res["sfdx_readme"]:
            print("README.md is the one from sf project generate: use --replace-readme to replace it.")
        if res["conflicts"]:
            print("Nothing was written: some files already exist. Review them or use --add-missing.")
        elif a.dry_run:
            print("Dry run: nothing was written.")
    return 2 if res["conflicts"] else 0


if __name__ == "__main__":
    sys.exit(main())
