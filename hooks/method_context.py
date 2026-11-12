#!/usr/bin/env python3
"""SessionStart and UserPromptSubmit hooks of sdd-salesforce: they inject the method core into projects with
sdd.config.json.

In a Salesforce project (sfdx-project.json) that does not use the method yet, or in an empty folder, SessionStart
injects only one line so that Claude can offer it, in words, if the user is going to start, plan or build something.

SessionStart runs on startup, on resume and after compacting a session, and leaves a marker per session when it injects
the core. UserPromptSubmit injects the core once if the session does not have it yet: for example, when the project was
bootstrapped in that same session. The core is the <!-- core --> block of the sdd-method SKILL.md, read at that moment:
there is no copy. Outside those cases it does nothing. It never breaks the session: on any error, it exits silently.

Usage: python3 method_context.py            (reads the JSON event from stdin)
       python3 method_context.py --self-test
"""

import json
import os
import re
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import project as P  # noqa: E402

CORE_MARKER = re.compile(r"<!-- core -->\s*\n(.*?)\n\s*<!-- /core -->", re.DOTALL)
LIGHT_MARKER = re.compile(r"<!-- light -->\s*\n(.*?)\n\s*<!-- /light -->", re.DOTALL)
# What does not count when deciding whether a folder is empty.
IGNORED = {".git", ".sf", ".sfdx", ".vscode", ".idea", ".DS_Store", ".claude"}
MARKER_TTL = 7 * 24 * 3600
# Prefix of the session marker files. It keeps its 0.3 name so that markers written by earlier versions still count
# and are still cleaned up.
MARKER_PREFIX = "nucleo-"


def block(plugin_root, marker):
    try:
        with open(os.path.join(plugin_root, "skills", "sdd-method", "SKILL.md"), encoding="utf-8") as fh:
            m = marker.search(fh.read())
    except OSError:
        return ""
    return m.group(1).strip() if m else ""


def core(plugin_root):
    return block(plugin_root, CORE_MARKER)


def light(plugin_root):
    """The light block of the sdd-method SKILL.md: injected after the core in light projects (method.profile)."""
    return block(plugin_root, LIGHT_MARKER)


def is_empty_folder(cwd):
    try:
        return not [e for e in os.listdir(cwd) if e not in IGNORED]
    except OSError:
        return False


def context(cwd, plugin_root=None):
    """The text to inject, or None if cwd is not in an sdd or SFDX project and is not an empty folder."""
    root = P.project_root(cwd)
    if not root:
        sfdx = P.sfdx_root(cwd)
        empty = not sfdx and is_empty_folder(cwd)
        if not sfdx and not empty:
            return None
        name, version = P.plugin_version()
        where = ("%s is a Salesforce project that does not use the %s method yet." % (sfdx, name) if sfdx else
                 "%s is an empty folder." % os.path.abspath(cwd))
        return ("[%s %s] %s If the user wants to start a Salesforce project here (POC, demo, RFP) or to plan or "
                "build something, offer once, in one sentence, to bootstrap it with the %s method and, if they accept, "
                "load the sdd-bootstrap skill yourself: do not ask them to invoke a skill and do not give them a "
                "command. If they ask what the method is or how to use it, use the sdd-help skill. If it is not "
                "relevant, do not mention it." % (name, version or "?", where, name))
    org, method, c, problem = P.config(root)
    name, version = P.plugin_version()
    legacy = P.legacy_names(root)
    # A 0.2/0.3 CLAUDE.md looks for its own label to know the plugin is loaded.
    label = P.V.LEGACY_PROJECT_LABEL if legacy else "sdd project"
    profile = P.V.profile(method)
    lines = ['[%s %s] %s "%s" in %s: org %s, approver %s, autonomy %s, profile %s.' % (
        name, version or "?", label, c.get("project") or os.path.basename(root), root, org or "(no org_alias)",
        method.get("approver") or "(no approver)", method.get("autonomy") or "(no autonomy)", profile)]
    if problem:
        lines.append("Warning: %s. Until it is fixed, the plugin's guard denies the sf commands that touch an org."
                     % problem)
    for w in c.get("_warnings") or []:
        lines.append("Warning: %s." % w)
    warning = P.version_warning(name, str(method.get("version") or ""), version)
    if warning:
        lines.append(warning)
    if legacy:
        lines.append(legacy)
    text = core(plugin_root or P.plugin_root())
    lines.append(text or "The method core could not be read: load the sdd-method skill before working.")
    if profile == "light":
        lines.append(light(plugin_root or P.plugin_root()) or "The light block could not be read: load the sdd-method "
                     "skill and apply its light profile before working.")
    return "\n".join(lines)


def marker_path(markers, session):
    session = re.sub(r"[^A-Za-z0-9_-]", "", str(session or ""))[:100]
    return os.path.join(markers, MARKER_PREFIX + session) if session else None


def read_marker(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return ""


def write_marker(path, root):
    """True if the marker is written."""
    try:
        os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(root)
        return True
    except OSError:
        return False


def markers_dir():
    """One per user: on Linux, /tmp is shared and another user's folder could not be written."""
    user = str(os.getuid()) if hasattr(os, "getuid") else re.sub(r"\W", "", os.environ.get("USERNAME", ""))
    return os.path.join(tempfile.gettempdir(), "sdd-salesforce-%s" % (user or "x"))


def clean_markers(markers):
    try:
        for e in os.listdir(markers):
            path = os.path.join(markers, e)
            if e.startswith(MARKER_PREFIX) and time.time() - os.path.getmtime(path) > MARKER_TTL:
                os.remove(path)
    except OSError:
        pass


def respond(event, plugin_root=None, markers=None):
    """The hook output for this event, or None. The session marker says for which project it already has the core."""
    cwd = event.get("cwd") or os.getcwd()
    kind = event.get("hook_event_name") or "SessionStart"
    markers = markers or markers_dir()
    marker = marker_path(markers, event.get("session_id"))
    root = P.project_root(cwd)
    if kind == "UserPromptSubmit":
        if not root or not marker or read_marker(marker) == root:
            return None
    elif kind != "SessionStart":
        return None
    elif event.get("source") == "startup":
        clean_markers(markers)
    text = context(cwd, plugin_root)
    if not text:
        return None
    # Without a marker, UserPromptSubmit would repeat the core on every message: in that case only SessionStart
    # injects it.
    if root and marker and not write_marker(marker, root) and kind == "UserPromptSubmit":
        return None
    return {"hookSpecificOutput": {"hookEventName": kind, "additionalContext": text}}


def main():
    try:
        event = json.load(sys.stdin)
    except ValueError:
        event = {}
    try:
        output = respond(event if isinstance(event, dict) else {})
    except Exception:  # a hook must not break the session
        return 0
    if output:
        print(json.dumps(output, ensure_ascii=False))
    return 0


def self_test():
    failures = []
    plugin = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with tempfile.TemporaryDirectory() as tmp:
        outside = os.path.join(tmp, "other")
        inside = os.path.join(tmp, "poc", "force-app", "main")
        os.makedirs(outside)
        os.makedirs(inside)
        # A 0.3.0 config, with Spanish keys and values: the aliases must read it as the English one.
        with open(os.path.join(tmp, "poc", "sdd.config.json"), "w", encoding="utf-8") as fh:
            json.dump({"proyecto": "poc", "org_alias": "poc-demo",
                       "metodo": {"version": "0.0.1", "aprobador": "Ana", "autonomia": "estricta"}}, fh)
        sfdx = os.path.join(tmp, "sfdx", "force-app")
        os.makedirs(sfdx)
        open(os.path.join(tmp, "sfdx", "sfdx-project.json"), "w").write("{}")
        notice = context(sfdx, plugin) or ""
        if "sdd-bootstrap" not in notice or "sdd-help" not in notice or core(plugin) in notice:
            failures.append("in an SFDX project without the method it does not give the short notice (or injects the "
                            "core)")
        if "/sdd" in notice:
            failures.append("the short notice gives a /command")
        if "does not use the sdd-salesforce method yet" not in notice:
            failures.append("in an SFDX project the short notice does not say it does not use the method yet")
        empty = os.path.join(tmp, "empty")
        os.makedirs(os.path.join(empty, ".git"))
        notice = context(empty, plugin) or ""
        if "empty folder" not in notice or "sdd-bootstrap" not in notice or "/sdd" in notice or core(plugin) in notice:
            failures.append("in an empty folder it does not give the short notice without a /command (CA-GUI-01.1)")
        open(os.path.join(outside, "notes.txt"), "w").write("x")
        if context(outside, plugin) is not None:
            failures.append("in a folder with files that is neither SFDX nor sdd it injects something (CA-GUI-01.1)")
        t = context(inside, plugin) or ""
        if "org poc-demo" not in t or "approver Ana" not in t:
            failures.append("it does not give the project's org and approver")
        if core(plugin) not in t or not core(plugin):
            failures.append("it does not inject the core of the sdd-method SKILL.md")
        if "which is older" in t or "the project adopted" not in t:
            failures.append("it does not warn properly about an adopted version older than the loaded one")
        with open(os.path.join(tmp, "poc", "sdd.config.json"), "w", encoding="utf-8") as fh:
            json.dump({"project": "poc", "org_alias": "poc-demo",
                       "method": {"version": "0.0.1", "approver": "Ana", "autonomy": "strict"}}, fh)
        if "sdd-metodo → sdd-method, sdd-ayuda → sdd-help" not in t:
            failures.append("in a 0.3.0 project it does not give the line with the name equivalences (CA-VOC-01.4)")
        new = context(inside, plugin) or ""
        if not re.search(r"^\[[^\]]*\] Proyecto sdd ", t) or not new.startswith("[") or "] sdd project " not in new:
            failures.append("the project line does not keep the 0.3.0 label that its CLAUDE.md looks for, or the new "
                            "projects do not get the English one (CA-VOC-01.4)")
        without_legacy = "\n".join(x for x in t.replace("] Proyecto sdd ", "] sdd project ", 1).split("\n")
                                   if "sdd-metodo → sdd-method" not in x)
        if new != without_legacy or "autonomy strict" not in t:
            failures.append("with English keys, the context is not the 0.3.0 one without the equivalences line "
                            "(CA-VOC-01.4)")
        # Review round 12, F-001 and F-002: a 0.3.0 config that gains an English «method» is still a 0.3.0 project,
        # and its equivalences line names every token the checks read.
        with open(os.path.join(tmp, "poc", "sdd.config.json"), "w", encoding="utf-8") as fh:
            json.dump({"proyecto": "poc", "org_alias": "poc-demo", "method": {"language": "es"},
                       "metodo": {"version": "0.0.1", "aprobador": "Ana", "autonomia": "estricta"}}, fh)
        mixed = context(inside, plugin) or ""
        if not re.search(r"^\[[^\]]*\] Proyecto sdd ", mixed) or "approver Ana, autonomy strict" not in mixed \
                or "sdd-metodo → sdd-method" not in mixed:
            failures.append("with «metodo» plus an English «method», the context is no longer that of a 0.3.0 project "
                            "(F-001)")
        def tokens(v):
            out = [x for k in ("fields", "sections", "evidence_states") for x in
                   (v[k].values() if isinstance(v[k], dict) else v[k])]
            out += [v["markers"]["to_close"], v["markers"]["except"], v["spec"]["requirements_end"],
                    v["change_log"]["section"], "## " + v["status"]["section"], v["paths"]["step_reports"]]
            out += [x for x in v["negation"]["phrases"] if "'" not in x]  # the contracted forms have no pair
            return out + [P.V._label(x["label"]) for x in v["verifications"]]
        line = next((x for x in mixed.split("\n") if "sdd-metodo → sdd-method" in x), "")
        missing = [a for a, b in zip(tokens(P.V.TRACEABILITY["en"]), tokens(P.V.TRACEABILITY["es"]))
                   if a != b and "%s = %s" % (a, b) not in line]
        if missing:
            failures.append("the equivalences line misses tokens the checks read: %s (F-002)" % ", ".join(missing))
        with open(os.path.join(tmp, "poc", "sdd.config.json"), "w", encoding="utf-8") as fh:
            json.dump({"org_alias": "poc-demo", "method": {"autonomy": "critical"}, "metodo": {"autonomia": "estricta"}},
                      fh)
        if not any(x.startswith("Warning: config: method.autonomy") for x in (context(inside, plugin) or "").split("\n")):
            failures.append("a value that differs between «method» and «metodo» gives no warning in the context (F-001)")
        markers = os.path.join(tmp, "markers")
        ask = {"hook_event_name": "UserPromptSubmit", "session_id": "s-1", "cwd": inside}
        r = respond(ask, plugin, markers)
        if not r or r["hookSpecificOutput"]["hookEventName"] != "UserPromptSubmit" or \
                core(plugin) not in r["hookSpecificOutput"]["additionalContext"]:
            failures.append("UserPromptSubmit without a marker does not inject the core (CA-GUI-02.1)")
        if respond(ask, plugin, markers) is not None:
            failures.append("UserPromptSubmit with the marker set injects the core again (CA-GUI-02.1)")
        start = {"hook_event_name": "SessionStart", "source": "startup", "session_id": "s-2", "cwd": inside}
        if not respond(start, plugin, markers) or respond(dict(ask, session_id="s-2"), plugin, markers):
            failures.append("after SessionStart, UserPromptSubmit repeats the core (CA-GUI-02.1)")
        if respond(dict(ask, session_id="s-3", cwd=outside), plugin, markers) is not None or \
                respond(dict(ask, session_id="s-4", cwd=sfdx), plugin, markers) is not None:
            failures.append("UserPromptSubmit outside an sdd project injects something (CA-GUI-02.1)")
        if respond(dict(ask, session_id=""), plugin, markers) is not None:
            failures.append("UserPromptSubmit without a session_id injects something")
        blocked = os.path.join(tmp, "blocked")
        open(blocked, "w").write("a file, not a folder")
        if respond(dict(ask, session_id="s-5"), plugin, blocked) is not None:
            failures.append("unable to write the marker, UserPromptSubmit injects the core (and would repeat it)")
        if not respond(dict(start, session_id="s-6"), plugin, blocked):
            failures.append("unable to write the marker, SessionStart stops injecting the core")
        # CA-LIG-01.2 and 01.7: a light project gets the core and then the light block; full or without a profile, only
        # the core
        for cfg, expected in (({"method": {"profile": "light"}}, True), ({"metodo": {"perfil": "ligero"}}, True),
                              ({"method": {"profile": "full"}}, False), ({"method": {}}, False)):
            with open(os.path.join(tmp, "poc", "sdd.config.json"), "w", encoding="utf-8") as fh:
                json.dump(dict(cfg, org_alias="poc-demo"), fh)
            t = context(inside, plugin) or ""
            has = bool(light(plugin)) and light(plugin) in t
            if has != expected or core(plugin) not in t or (has and t.index(core(plugin)) > t.index(light(plugin))):
                failures.append("with %r, the light block is %s (CA-LIG-01.2)" % (cfg, "missing" if expected else
                                                                                  "injected"))
            if expected and ("profile light" not in t or "autonomy critical" not in t):
                failures.append("with %r, the project line does not say profile light and autonomy critical" % cfg)
        if not light(plugin) or "Light profile" not in light(plugin):
            failures.append("the sdd-method SKILL.md has no light block")
        with open(os.path.join(tmp, "poc", "sdd.config.json"), "w", encoding="utf-8") as fh:
            json.dump({"org_alias": "poc-demo", "metodo": {"version": "99.0.0"}}, fh)
        if "older: update the plugin" not in (context(inside, plugin) or ""):
            failures.append("it does not ask to update a plugin older than the adopted one")
        with open(os.path.join(tmp, "poc", "sdd.config.json"), "w", encoding="utf-8") as fh:
            fh.write("{ broken")
        t = context(inside, plugin) or ""
        if "cannot be read" not in t or core(plugin) not in t:
            failures.append("with a corrupt sdd.config.json it does not warn or does not inject the core")
    for f in failures:
        print("FAIL:", f)
    print("self-test: %s" % ("OK" if not failures else "%d failures" % len(failures)))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in P.argv(sys.argv[1:]) else main())
