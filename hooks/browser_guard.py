#!/usr/bin/env python3
"""PreToolUse hook of sdd-salesforce for the Playwright MCP (tools mcp__playwright__*): org isolation in the browser.

Inside a project with sdd.config.json, it looks for the URLs in the tool's input (the url of browser_navigate or
browser_tabs, and the literal URLs in the code of browser_run_code_unsafe or browser_evaluate) and:
- denies a host of a Salesforce org (My Domain, Lightning, Setup, sites, Visualforce, content, Experience Builder,
  micro-apps) whose My Domain is not the project's, which check-environment.py --query-org stores in the inventory
  («org.my_domain»). A sandbox's My Domain keeps its suffix («acme--uat»): it is another org than «acme»;
- with the «filename» of browser_run_code_unsafe, reads that file and looks for URLs in it (if it cannot, it asks);
- asks for confirmation if the project's My Domain is not known yet, for an org host other than the login ones;
- lets through the project's org, login.salesforce.com and test.salesforce.com, the documentation, localhost and any
  website that is not a Salesforce org.
It does not see the navigation that a click causes. Outside an sdd project, or on a failure of its own, it decides
nothing.

Usage: python3 browser_guard.py            (reads the JSON event from stdin)
       python3 browser_guard.py --self-test
"""

import json
import os
import re
import sys
import tempfile
from urllib.parse import unquote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import project as P  # noqa: E402

# Suffixes of the hosts of a Salesforce org. The first label of the host starts with the org's My Domain name
# («acme-dev-ed.develop.my.salesforce.com», «acme-dev-ed--c.develop.vf.force.com»).
ORG_SUFFIXES = (".my.salesforce.com", ".lightning.force.com", ".my.salesforce-setup.com", ".my.site.com",
                ".salesforce-sites.com", ".salesforce.app", ".salesforce-experience.com", ".my.salesforce-scrt.com",
                ".documentforce.com", ".visualforce.com", ".force.com")
# Visualforce, files and containers add «--<namespace>» to the My Domain («acme--uat--c.sandbox.vf.force.com»).
CONTENT_SUFFIXES = (".vf.force.com", ".file.force.com", ".container.force.com", ".documentforce.com",
                    ".visualforce.com", ".visual.force.com", ".content.force.com")
# Only this tool runs the code of the file it names; in the others, «filename» is where a screenshot or snapshot is
# saved (review round 15, F-007).
RUNS_FILE = "mcp__playwright__browser_run_code_unsafe"
LOGIN_HOSTS = ("login.salesforce.com", "test.salesforce.com", "developer.force.com")
URL = re.compile(r"""\bhttps?:/+([^/\s'"`<>?#]+)""", re.IGNORECASE)
DOTS = {"\u3002": ".", "\uff0e": ".", "\uff61": "."}


def normalize(text):
    """The text as a browser reads a URL in it: without tabs or line breaks, «\\» as «/», %XX decoded and the
    ideographic full stops as dots."""
    t = re.sub(r"[\t\r\n]", "", str(text or ""))
    t = unquote(t).replace("\\", "/")
    for k, v in DOTS.items():
        t = t.replace(k, v)
    return t


def host_of(value):
    """The host of a URL, also without a scheme («acme.my.salesforce.com/lightning»), in lowercase, or ''."""
    v = normalize(value).strip()
    m = URL.search(v)
    h = m.group(1) if m else (v.split("/", 1)[0] if v and " " not in v.split("/", 1)[0] else "")
    return h.rsplit("@", 1)[-1].split(":", 1)[0].lower().rstrip(".")


def hosts(tool_input, root=None, tool_name=RUNS_FILE):
    """The hosts that the tool's input would open, and whether the code file it names could not be read. The file is
    resolved from the project root, as the MCP does (review round 15, F-008)."""
    out, unreadable = [], False
    if not isinstance(tool_input, dict):
        return out, unreadable
    runs_file = tool_name == RUNS_FILE and bool(tool_input.get("filename"))
    texts = [v for k, v in tool_input.items() if k not in ("url", "filename") and isinstance(v, str)]
    if runs_file:
        path = os.path.join(root or os.getcwd(), os.path.expanduser(str(tool_input["filename"])))
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                texts.append(fh.read())
        except OSError:
            unreadable = True
    if tool_input.get("url"):
        out.append(host_of(tool_input["url"]))
    for v in texts:
        out += [host_of("https://" + m.group(1)) for m in URL.finditer(normalize(v))]
    return [h for h in out if h], unreadable


def org_name(host):
    """The My Domain name of an org host, or None if the host is not a Salesforce org."""
    if host in LOGIN_HOSTS or not any(host.endswith(s) for s in ORG_SUFFIXES):
        return None
    label = host.split(".", 1)[0]
    if any(host.endswith(s) for s in CONTENT_SUFFIXES) and "--" in label:
        label = label.rsplit("--", 1)[0]
    return label


def my_domain(root, conf):
    """The project's My Domain name, from the environment inventory, or ''."""
    vocab = P.V.vocabulary(P.read_json(os.path.join(root, "sdd.config.json"))[0])[0]
    path = ((conf.get("environment") or {}).get("inventory") if isinstance(conf.get("environment"), dict) else None) \
        or P.V.INVENTORY_PATH[vocab]
    inv = P.read_json(os.path.join(root, path))[0]
    org = inv.get("org") if isinstance(inv.get("org"), dict) else {}
    return str(org.get("my_domain") or "").strip().lower()


def decide(tool_name, tool_input, cwd):
    """(decision, reason): decision is 'deny', 'ask' or None."""
    if not str(tool_name or "").startswith("mcp__playwright__"):
        return None, ""
    root = P.project_root(cwd)
    if not root:
        return None, ""
    org, method, conf, problem = P.config(root)
    mine = my_domain(root, conf)
    found, unreadable = hosts(tool_input, root, tool_name)
    if unreadable:
        return "ask", ("%s names a file that the browser guard cannot read (%s): confirm that it only opens the "
                       "project's org." % (tool_name, tool_input.get("filename")))
    for h in found:
        name = org_name(h)
        if name is None:
            continue
        if not mine:
            return "ask", ('%s is a Salesforce org host and the My Domain of this project (%s, org "%s") is not in the '
                           'environment inventory yet: run check-environment.py --query-org, or confirm that this is '
                           'the project\'s org.' % (h, root, org or "?"))
        if name != mine:
            return "deny", ('This project (%s) works only with its org (My Domain "%s"), and %s belongs to another org '
                            '("%s"). The browser only opens the project\'s org.' % (root, mine, h, name))
    return None, ""


def main():
    try:
        event = json.load(sys.stdin)
        decision, reason = decide(event.get("tool_name"), event.get("tool_input") or {}, event.get("cwd") or os.getcwd())
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
        os.makedirs(os.path.join(poc, "docs", "baseline"))
        with open(os.path.join(poc, "sdd.config.json"), "w", encoding="utf-8") as fh:
            json.dump({"org_alias": "poc-demo", "method": {"vocabulary": "en"}}, fh)
        nav = "mcp__playwright__browser_navigate"
        # Without a My Domain in the inventory: org hosts ask, the rest passes
        for url, expected in (("https://acme-dev-ed.develop.my.salesforce.com/", "ask"),
                              ("https://login.salesforce.com", None), ("https://developer.salesforce.com/docs", None)):
            got = decide(nav, {"url": url}, poc)[0]
            if got != expected:
                failures.append("without My Domain, %s gives %r (expected %r)" % (url, got, expected))
        with open(os.path.join(poc, "docs", "baseline", "environment.json"), "w", encoding="utf-8") as fh:
            json.dump({"org": {"alias": "poc-demo", "my_domain": "acme-dev-ed"}}, fh)
        cases = [  # CA-NAV-01.3
            (nav, {"url": "https://acme-dev-ed.develop.my.salesforce.com/lightning/page/home"}, None),
            (nav, {"url": "https://acme-dev-ed.develop.lightning.force.com/lightning/o/Account/list"}, None),
            (nav, {"url": "acme-dev-ed.develop.my.salesforce-setup.com/lightning/setup/SetupOneHome/home"}, None),
            (nav, {"url": "https://acme-dev-ed--c.develop.vf.force.com/apex/Page"}, None),
            (nav, {"url": "https://acme-dev-ed.develop.my.site.com/portal/s/"}, None),
            (nav, {"url": "https://login.salesforce.com/?locale=es"}, None),
            (nav, {"url": "https://test.salesforce.com"}, None),
            (nav, {"url": "https://help.salesforce.com/s/articleView?id=sf.x.htm"}, None),
            (nav, {"url": "http://localhost:3000/"}, None),
            (nav, {"url": "https://www.example.com/"}, None),
            (nav, {"url": "https://beta-corp.my.salesforce.com/"}, "deny"),
            (nav, {"url": "https://BETA-CORP.lightning.force.com/lightning/page/home"}, "deny"),
            (nav, {"url": "https://beta-corp.my.site.com/s/"}, "deny"),
            ("mcp__playwright__browser_tabs", {"action": "new", "url": "https://beta-corp.my.salesforce.com"}, "deny"),
            ("mcp__playwright__browser_run_code_unsafe",
             {"code": "await page.goto('https://beta-corp.my.salesforce-setup.com/lightning/setup')"}, "deny"),
            ("mcp__playwright__browser_run_code_unsafe",
             {"code": "page.frames().find(f => f.url().includes('salesforce-setup.com'))"}, None),
            ("mcp__playwright__browser_snapshot", {}, None),
            # Review round 14, F-003: URLs that Chromium normalizes, more org hosts and the code in a file
            (nav, {"url": "https://beta-corp.my.salesforce.com\\@example.com/"}, "deny"),
            (nav, {"url": "https://beta-corp.my.salesforce%2Ecom/"}, "deny"),
            (nav, {"url": "https://beta-\tcorp.my.salesforce.com/"}, "deny"),
            (nav, {"url": "https://beta-corp.my.salesforce\u3002com/"}, "deny"),
            (nav, {"url": "view-source:https://beta-corp.my.salesforce.com/"}, "deny"),
            (nav, {"url": "https://beta-corp.builder.salesforce-experience.com/"}, "deny"),
            (nav, {"url": "https://beta-corp--c.documentforce.com/"}, "deny"),
            (nav, {"url": "https://acme-dev-ed--c.documentforce.com/"}, None),
            (nav, {"url": "https://developer.force.com/"}, None),
            ("mcp__playwright__browser_run_code_unsafe", {"filename": "walk.js"}, "deny"),
            ("mcp__playwright__browser_run_code_unsafe", {"filename": "missing.js"}, "ask"),
            ("mcp__other__navigate", {"url": "https://beta-corp.my.salesforce.com"}, None),
        ]
        cases += [  # review round 15, F-007 and F-008: «filename» of a screenshot is not read; the code file, from the root
            ("mcp__playwright__browser_take_screenshot", {"filename": "evidence/W1.1/list.png"}, None),
            ("mcp__playwright__browser_snapshot", {"filename": "walk.js"}, None),
            (nav, {"url": "https://acme-dev-ed--c.na1.visual.force.com/apex/P"}, None),
        ]
        with open(os.path.join(poc, "walk.js"), "w", encoding="utf-8") as fh:
            fh.write("await page.goto('https://beta-corp.lightning.force.com/lightning/page/home');\n")
        for tool, inp, expected in cases:
            got = decide(tool, inp, os.path.join(poc, "docs"))[0]
            if got != expected:
                failures.append("%s %r gives %r (expected %r)" % (tool, inp, got, expected))
        # Review round 14, F-001: a sandbox is another org than production and than the other sandboxes
        with open(os.path.join(poc, "docs", "baseline", "environment.json"), "w", encoding="utf-8") as fh:
            json.dump({"org": {"alias": "poc-demo", "my_domain": "acme--uat"}}, fh)
        for url, expected in (("https://acme--uat.sandbox.my.salesforce.com/", None),
                              ("https://acme--uat.sandbox.lightning.force.com/lightning/page/home", None),
                              ("https://acme--uat--c.sandbox.vf.force.com/apex/Page", None),
                              ("https://acme.my.salesforce.com/", "deny"), ("https://acme.lightning.force.com/", "deny"),
                              ("https://acme--qa.sandbox.my.salesforce.com/", "deny"),
                              ("https://acme--qa--c.sandbox.vf.force.com/apex/Page", "deny")):
            got = decide(nav, {"url": url}, poc)[0]
            if got != expected:
                failures.append("sandbox acme--uat: %s gives %r (expected %r)" % (url, got, expected))
        if decide(nav, {"url": "https://beta-corp.my.salesforce.com"}, tmp)[0] is not None:
            failures.append("outside an sdd project the guard decides something")
        # A 0.3.0 project (vocabulary es) reads its inventory from entorno.json
        old = os.path.join(tmp, "old")
        os.makedirs(os.path.join(old, "docs", "baseline"))
        with open(os.path.join(old, "sdd.config.json"), "w", encoding="utf-8") as fh:
            json.dump({"org_alias": "old-demo", "metodo": {"autonomia": "critico"}}, fh)
        with open(os.path.join(old, "docs", "baseline", "entorno.json"), "w", encoding="utf-8") as fh:
            json.dump({"org": {"my_domain": "old-org"}}, fh)
        if decide(nav, {"url": "https://old-org.my.salesforce.com"}, old)[0] is not None or \
                decide(nav, {"url": "https://acme-dev-ed.my.salesforce.com"}, old)[0] != "deny":
            failures.append("in a 0.3.0 project it does not read the My Domain from entorno.json")
    for f in failures:
        print("FAIL:", f)
    print("self-test: %s" % ("OK" if not failures else "%d failures" % len(failures)))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in P.argv(sys.argv[1:]) else main())
