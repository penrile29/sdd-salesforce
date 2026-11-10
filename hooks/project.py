"""Shared helpers of the sdd-salesforce hooks: find the project and read its configuration.

An sdd project is a folder with sdd.config.json; the hooks only act inside one. Standard library only.
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "skills", "sdd-method",
                                "scripts"))
try:
    import sdd_vocab as V  # noqa: E402
except ImportError:  # the plugin is incomplete: config() says so and the guard denies what touches an org
    V = None


def argv(args):
    """The command line with the options of 0.2 and 0.3 changed to the current ones."""
    return V.argv(args) if V else list(args)


def project_root(cwd):
    """The nearest folder, from cwd upwards, that has sdd.config.json; None if there is none."""
    d = os.path.abspath(cwd or os.getcwd())
    while True:
        if os.path.isfile(os.path.join(d, "sdd.config.json")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def sfdx_root(cwd):
    """The nearest folder, from cwd upwards, with sfdx-project.json; None if there is none."""
    d = os.path.abspath(cwd or os.getcwd())
    while True:
        if os.path.isfile(os.path.join(d, "sfdx-project.json")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def read_json(path):
    """(data, error): data is {} if the file does not exist, cannot be read or is not a JSON object."""
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        return {}, None
    except (OSError, ValueError) as e:
        return {}, str(e) or e.__class__.__name__
    if not isinstance(data, dict):
        return {}, "not a JSON object"
    return data, None


def config(root):
    """(org_alias, method, config, problem). problem explains why sdd.config.json is not usable, or is None.

    config and method (its "method") come with English keys and values, also when the project is from 0.2 or 0.3 and
    has them in Spanish."""
    c, error = read_json(os.path.join(root, "sdd.config.json"))
    if V is None:
        return "", {}, {}, "sdd_vocab.py is missing from the plugin (reinstall it)"
    c, warnings = V.normalize(c)
    c["_warnings"] = warnings  # the hook shows them in the context
    method = c.get("method") if isinstance(c.get("method"), dict) else {}
    org = str(c.get("org_alias") or "").strip()
    problem = None
    if error:
        problem = "sdd.config.json cannot be read (%s)" % error
    elif not org:
        problem = "sdd.config.json has no org_alias"
    return org, method, c, problem


def legacy_names(root):
    """In a project bootstrapped with 0.2 or 0.3 (vocabulary "es"), the line with the names that changed; otherwise
    None."""
    c, error = read_json(os.path.join(root, "sdd.config.json"))
    if V is None:
        return None
    # With an unreadable sdd.config.json, the seed decision of 0.2/0.3 still tells an old project apart.
    decisions = os.path.join(root, "knowledge", "decisions")
    old_seed = os.path.isdir(decisions) and any(f.endswith(V.LEGACY_SEED) for f in os.listdir(decisions))
    if (V.vocabulary(c)[0] if not error else ("es" if old_seed else "en")) != "es":
        return None
    return ("This project was bootstrapped with sdd-salesforce 0.2 or 0.3, and its documents cite names that have "
            "changed: %s. Its documents keep the Spanish headings, fields and paths of that time, which the checks read "
            "as they are: copy them from this project's own documents, never from the plugin's templates, which are "
            "English. What the method and the templates call (left) is in this project (right): %s. The Spanish "
            "options of the scripts still work." % (", ".join("%s → %s" % x for x in V.LEGACY_NAMES),
                                                    "; ".join("%s = %s" % x for x in V.legacy_terms())))


def local_target_org(root):
    """The target-org of the project's local sf configuration (.sf/config.json), or ''."""
    return str(read_json(os.path.join(root, ".sf", "config.json"))[0].get("target-org") or "").strip()


def plugin_root():
    """The plugin root: CLAUDE_PLUGIN_ROOT in the hooks or, failing that, the folder above hooks/."""
    return os.environ.get("CLAUDE_PLUGIN_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def plugin_version():
    m = read_json(os.path.join(plugin_root(), ".claude-plugin", "plugin.json"))[0]
    return str(m.get("name") or "sdd-salesforce"), str(m.get("version") or "")


def version_tuple(v):
    parts = re.findall(r"\d+", str(v or ""))
    return tuple(int(x) for x in parts[:3]) if parts else None


def version_warning(name, adopted, loaded):
    """The warning text if the version the project adopted and that of the loaded plugin differ, or None."""
    if not adopted or not loaded or adopted == loaded:
        return None
    a, c = version_tuple(adopted), version_tuple(loaded)
    if a and c and c < a:
        return ("Warning: the project adopted %s %s and the loaded plugin is %s, which is older: update the plugin "
                "before working." % (name, adopted, loaded))
    return ("Warning: the project adopted %s %s and the loaded plugin is %s. Check the plugin's CHANGELOG and, if "
            "anything affects the project, record it with a decision." % (name, adopted, loaded))
