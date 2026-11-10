#!/usr/bin/env python3
"""Local traceability check of a Salesforce SDD project: spec → traceability.md → steps → evidence.

Reads the requirements and AC of the specs, the traceability.md table, the steps of the delivery plan, the scopes of
integration.md, the «Steps» table of status.md, the evidence sources and the environment inventory, and checks:

- spec: duplicate requirements, or without priority or AC; duplicate AC; AC cited in Part 1 (before the marker of the
  design part) that are not defined in canonical form («- AC-XXX-NN.N — …»);
- table: AC that do not exist, are duplicated or have the wrong requirement; spec AC with neither a row nor an
  exclusion; exclusions without a reason or without who agreed to them; verifications outside the closed vocabulary;
  steps that do not exist; a «Step» column that does not match the steps of the verification; an unknown evidence
  state;
- steps: duplicates, dependencies on steps that do not exist, ranges across waves, cycles, a «Parallel with» that
  includes a step it depends on (or that depends on it), and the «Steps without AC» table;
- the «Satisfies» of each step against the table, both ways (with R-XX expanded);
- the «Skill» of each step against the environment inventory (the one from check-environment.py): a skill that is not
  there or is missing is an error; shadowed, a warning; a sub-agent of the inventory is fine. Without an inventory,
  a warning and no check;
- change log: each requirement or AC added, modified or removed since the latest tag (release-N or, if there is none,
  design-approved) has a row naming it in the «Change log» of its spec; a change in whitespace or in the «Status» of
  the requirement does not count. Without git or without tags, nothing is compared;
- evidence that cites unknown AC, and step reports or named tests that cite an AC their step does not have (warning);
- rows in the initial state («planned») whose steps (not counting the demo closing step) are integrated or closed in
  the «Steps» table of status.md and whose evidence is already cited in the file of its type (warning: they still
  have to move to «exists» or «passes»).

With --step W2.1 (repeatable) it requires, for each AC whose verification that step builds, a citation in the file of
the type the verification asks for (Apex test in the classes of its «Test first», demo case in its step report,
review in its reviews/… folder). For the demo closing step (if the configuration defines one), each AC with a «demo
step» cited in the demo walkthrough. With --no-review, missing reviews are warnings (the author's step report, before
the review).

With --graph it prints the total size per wave and per scope, the critical path (with ties) and the size rule (AC per
step and external dependency); it exits with 1 if a size breaks the rule. If there is a cycle, it does not compute the
critical path: it says so and exits with 1, with the list of errors.

A citation does not count on a line that denies coverage («does not cover», «not covered», «does not verify», as words
and case-insensitive) or that carries the TODO mark in capitals; a lowercase «todo» does not cancel it. In step
reports only the citations under «## Verification cases» count. In «Depends on», the «to close» segment runs up to the
next «;» that is not inside parentheses.

With --self-test it runs, with the default configuration, its own mutations of the negation filter, the step report
section, the «Depends on» parser, the graph with a cycle, the reading of the «Steps» table of status.md, the expansion
of AC and step lists and the reading of «Skill», and exits with 1 if any of them fails.

Configuration: the «traceability» section of <project>/sdd.config.json (or of --config). Whatever it lacks takes the
defaults of the project's vocabulary (sdd_vocab.py): those of «en» are the ones in sdd.config.example.json, documented
in its «_doc», and those of «es», the ones of a 0.2 or 0.3 project, whose Spanish keys are also accepted. A list
replaces the default one and an evidence type set to null is removed. The environment inventory is read from
«environment.inventory».

Usage, from the project root: python3 scripts/check-traceability.py [--project PATH] [--config PATH]
  [--step W2.1 ...] [--no-review] [--graph] [--self-test]
Exits with 0 if there are no errors, with 1 if there are and with 2 if the configuration is not valid. Python 3.9,
standard library only.
"""
import argparse
import copy
import fnmatch
import json
import pathlib
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))  # also with python3 -I
import sdd_vocab as V  # noqa: E402  the defaults of each vocabulary and the aliases of the 0.2 and 0.3 keys

MODES = ("classes", "sources", "report", "review", "validations")
FIELDS = ("depends", "satisfies", "test_first", "parallel", "size", "skill")
MAX_CHAINS = 20

K = None  # the compiled configuration (Config)


class ConfigError(Exception):
    """The configuration is not valid: the check exits with 2."""


class CycleError(Exception):
    """The graph has a cycle: there is no earliest finish."""


# --- Configuration -------------------------------------------------------------------------------------------------

def merge(base, extra):
    """Dictionaries are merged key by key; anything else (lists included) replaces. Keys «_…» are ignored."""
    out = copy.deepcopy(base)
    for k, v in extra.items():
        if k.startswith("_"):
            continue
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def non_capturing(p):
    """Turns the capture groups (named or not) into non-capturing groups, to embed the pattern."""
    p = re.sub(r"\(\?P<\w+>", "(?:", p)
    return re.sub(r"(?<!\\)\((?!\?)", "(?:", p)


def prefix_groups(p, prefix):
    """Adds a prefix to the named groups, to use the pattern twice in the same expression."""
    p = re.sub(r"\(\?P<(\w+)>", r"(?P<%s\1>" % prefix, p)
    return re.sub(r"\(\?P=(\w+)\)", r"(?P=%s\1)" % prefix, p)


def as_list(v):
    return [v] if isinstance(v, str) else list(v or [])


def unknown_key_warnings(raw, base, where, out):
    """Configuration keys the check does not know (probably a typo)."""
    for k, v in raw.items():
        if k.startswith("_"):
            continue
        if k not in base:
            out.append("config: unknown key %s.%s (ignored)" % (where, k))
        elif isinstance(v, dict) and isinstance(base[k], dict) and k not in ("types", "sizes", "per_ac"):
            unknown_key_warnings(v, base[k], "%s.%s" % (where, k), out)


class Config:
    def __init__(self, tz, environment, root, vocab="en"):
        self.root = root
        self.vocab = vocab
        self.g = V.GRAMMAR[vocab]

        def rx(key, pat, flags=0):
            if not isinstance(pat, str):
                raise ConfigError("traceability.%s: must be a regular expression (text)" % key)
            try:
                return re.compile(pat, flags)
            except re.error as e:
                raise ConfigError("traceability.%s: invalid expression «%s» (%s)" % (key, pat, e))

        r = tz["paths"]
        self.specs = as_list(r.get("specs"))
        self.steps = as_list(r.get("steps"))
        for key, pats in (("paths.specs", self.specs), ("paths.steps", self.steps)):
            for p in pats:
                if pathlib.PurePath(p).is_absolute():
                    raise ConfigError("traceability.%s: globs are relative to the project («%s»)" % (key, p))
        self.trace = self.path(r.get("traceability"))
        self.integ = self.path(r.get("integration"))
        self.status = self.path(r.get("status"))
        self.reports = self.path(r.get("step_reports"))
        self.prior = self.path(r.get("prior_validations"))
        self.walkthrough = self.path(r.get("demo_walkthrough"))
        self.reviews = self.path(r.get("reviews"))
        self.exclude = set(as_list(r.get("exclude")))
        self.inventory = self.path((environment or {}).get("inventory", V.INVENTORY_PATH[vocab]))

        ids = tz["ids"]
        step, ac = ids.get("step"), ids.get("ac")
        if not isinstance(step, str) or "(?P<num>" not in step:
            raise ConfigError("traceability.ids.step: needs the group (?P<num>…), the number that varies in a range")
        if not isinstance(ac, str) or "(?P<req>" not in ac or "(?P<num>" not in ac \
                or ac.index("(?P<req>") > ac.index("(?P<num>"):
            raise ConfigError("traceability.ids.ac: needs the groups (?P<req>…) and, after it, (?P<num>…), at the top "
                              "level: the short form of a list («02.3») starts at (?P<req>")
        step_nc, ac_nc = non_capturing(step), non_capturing(ac)
        r_nc = non_capturing(ids.get("requirement") or "")
        self.STEP = rx("ids.step", step_nc)
        self.step_one = rx("ids.step", step)
        self.step_range = rx("ids.step", r"(?P<a>%s)(?:\s*[-–]\s*(?P<b>%s))?" % (prefix_groups(step, "a_"),
                                                                                  prefix_groups(step, "b_")))
        self.step_head = rx("ids.step", r"### (%s) — " % step_nc)
        self.verif_tagged = rx("ids.step", r"^(.*?)\s*\((%s(?:\s*(?:,|%s)\s*%s)*)\)$" % (step_nc, re.escape(self.g["and"]),
                                                                                   step_nc))
        self.status_row = rx("ids.step", r"\|\s*(?:%s)" % step_nc)
        self.review_dir = rx("ids.step", r"-(?:%s)" % step_nc)
        self.step_example = ids.get("step_example") or "step"
        self.AC = rx("ids.ac", ac_nc)
        short = ac[ac.index("(?P<req>"):]
        y, a = re.escape(self.g["and"]), re.escape(self.g["to"])
        # separators of an AC list in short form («02.1 to 02.3, 02.5 and 02.7»)
        sep = r"(?:,\s*%s|,|;|%s|%s|–)" % (y, y, a)
        self.ac_list = rx("ids.ac", r"(?P<ac>%s)(?P<tail>(?:\s*%s\s*%s)*)" % (ac, sep, non_capturing(short)))
        self.ac_short = rx("ids.ac", r"(?P<sep>%s)\s*(?P<s>%s)" % (sep[3:-1], short))
        self.ac_def = rx("ids.ac", r"^- (%s) — " % ac_nc, re.M)
        self.R = rx("ids.requirement", r_nc)
        self.req_head = rx("ids.requirement", r"(%s) — " % r_nc)
        self.satisfies_span = rx("ids.requirement", r"(%s)(?:\s*\(([^)]*)\))?" % r_nc)
        ext = ids.get("external_dependency")
        self.external = rx("ids.external_dependency", non_capturing(ext)) if ext else None

        sp = tz["spec"]
        self.req_end = sp.get("requirements_end") or None
        self.prio = rx("spec.priority", sp.get("priority"))
        if self.prio.groups < 1:
            raise ConfigError("traceability.spec.priority: needs a group with the priority («(P\\d)»)")
        self.critical_prio = sp.get("critical_priority")
        self.req_state = re.compile(r"\s*·?\s*%s:\s*\S+" % re.escape(self.g["state_field"]))

        fields = tz["fields"]
        missing = [c for c in FIELDS if not fields.get(c)]
        if missing:
            raise ConfigError("traceability.fields: missing %s" % ", ".join(missing))
        self.field = dict((c, fields[c]) for c in FIELDS)
        self.field_by_name = dict((v, k) for k, v in self.field.items())

        sec = tz["sections"]
        self.sec_excl = sec["exclusions"]
        self.sec_no_ac = sec["steps_without_ac"]
        self.sec_scopes = sec["scopes"]
        self.sec_cases = sec["report_cases"]
        self.report_section = rx("sections.report_cases", r"^##\s+%s\s*$" % re.escape(self.sec_cases), re.I)

        mk = tz["markers"]
        self.to_close = mk["to_close"]
        self.except_mark = mk["except"]
        self.satisfies_end = as_list(mk.get("satisfies_end"))

        self.types = dict((k, v) for k, v in tz["types"].items() if v is not None and not k.startswith("_"))
        for name, t in self.types.items():
            if not isinstance(t, dict) or t.get("mode") not in MODES:
                raise ConfigError("traceability.types.%s: «mode» must be one of %s" % (name, ", ".join(MODES)))
            if t["mode"] in ("classes", "sources"):
                t["sources"] = as_list(t.get("sources"))
                for p in t["sources"]:
                    if pathlib.PurePath(p).is_absolute():
                        raise ConfigError("traceability.types.%s.sources: globs are relative to the project" % name)
                t.setdefault("where", ", ".join(t["sources"]) or name)
            if t["mode"] == "classes":
                if t.get("field") not in FIELDS:
                    raise ConfigError("traceability.types.%s.field: must be one of %s"
                                      % (name, ", ".join(FIELDS)))
                t["_names"] = rx("types.%s.names" % name, t.get("names"))
                if t["_names"].groups != 1:
                    raise ConfigError("traceability.types.%s.names: needs exactly one group (the class name)"
                                      % name)
                t.setdefault("with", name)
        self.verifications = []
        for i, v in enumerate(tz["verifications"]):
            if not isinstance(v, dict) or v.get("type") not in self.types:
                raise ConfigError("traceability.verifications[%d]: «type» must be one of traceability.types" % i)
            pat = rx("verifications[%d].label" % i, v.get("label"))
            if pat.groups > 1:
                raise ConfigError("traceability.verifications[%d].label: at most one group (the step)" % i)
            self.verifications.append((pat, v["type"]))
        self.closing_step = tz.get("demo_closing_step") or None

        neg = tz["negation"]
        phrases = as_list(neg.get("phrases"))
        marks = as_list(neg.get("marks"))
        self.negation = re.compile(r"\b(?:%s)\b" % "|".join(re.escape(f) for f in phrases), re.I) if phrases else None
        self.mark = re.compile(r"\b(?:%s)\b" % "|".join(re.escape(m) for m in marks)) if marks else None

        self.states = tuple(as_list(tz.get("evidence_states")))
        if not self.states:
            raise ConfigError("traceability.evidence_states: at least one is needed (the first is the initial one)")

        st = tz["status"]
        self.status_section = st["section"]
        self.status_col = int(st["state_column"])
        self.integrated = rx("status.integrated", st["integrated"], re.I)
        self.not_integrated = rx("status.not_integrated", st["not_integrated"], re.I)

        self.sizes = dict(tz["sizes"])
        if not self.sizes or not all(isinstance(v, int) and v > 0 for v in self.sizes.values()):
            raise ConfigError("traceability.sizes: each size needs a positive whole number of units")
        self.size_name = dict((v, k) for k, v in self.sizes.items())
        letters = sorted(self.sizes, key=lambda t: self.sizes[t])
        self.sizes_text = letters[0] if len(letters) == 1 else "%s or %s" % (", ".join(letters[:-1]), letters[-1])
        self.size_re = re.compile(r"\*\*%s:\*\*\s*(%s)\b" % (re.escape(self.field["size"]),
                                                             "|".join(re.escape(t) for t in
                                                                      sorted(self.sizes, key=len, reverse=True))))
        rule = tz["size_rule"]
        per_ac = sorted(((int(d), t) for t, d in (rule.get("per_ac") or {}).items()), reverse=True)
        for _, t in per_ac:
            if t not in self.sizes:
                raise ConfigError("traceability.size_rule.per_ac: %s is not a size of «sizes»" % t)
        self.rule_per_ac, previous = [], None
        for since, t in per_ac:
            more = "" if t == letters[-1] else " or larger"
            text = ("more than %d AC → %s%s" % (since - 1, t, more) if previous is None
                    else "%d to %d AC → %s%s" % (since, previous - 1, t, more))
            self.rule_per_ac.append((since, t, text))
            previous = since
        self.external_size = rule.get("external_dependency") or None
        if self.external_size and self.external_size not in self.sizes:
            raise ConfigError("traceability.size_rule.external_dependency: %s is not a size" % self.external_size)

        log = tz["change_log"]
        self.change_log_section = log.get("section") or V.TRACEABILITY[vocab]["change_log"]["section"]
        self.tags = as_list(log.get("tags"))

    def path(self, p):
        return (self.root / p) if p else None


def load(project, config_arg):
    """(Config, warnings) from --project and --config. Raises ConfigError if it is not valid."""
    root = pathlib.Path(project).resolve()
    if not root.is_dir():
        raise ConfigError("--project: %s is not a folder" % project)
    cpath = pathlib.Path(config_arg) if config_arg else root / "sdd.config.json"
    warnings, raw = [], {}
    if cpath.exists():
        try:
            raw = json.loads(cpath.read_text(encoding="utf-8"))
        except ValueError as e:
            raise ConfigError("%s is not valid JSON (%s)" % (cpath, e))
        if not isinstance(raw, dict):
            raise ConfigError("%s: a JSON object is expected" % cpath)
    elif config_arg:
        raise ConfigError("--config: %s does not exist" % config_arg)
    else:
        warnings.append("config: there is no sdd.config.json in the project; the defaults are used")
    vocab, error = V.vocabulary(raw)
    if error:
        raise ConfigError(error)
    raw, doubles = V.normalize(raw)
    warnings.extend(doubles)
    tz = raw.get("traceability", {})
    if not isinstance(tz, dict):
        raise ConfigError("«traceability» must be an object")
    defaults = V.traceability_defaults(vocab)
    unknown_key_warnings(tz, defaults, "traceability", warnings)
    environment = raw.get("environment", {})
    if not isinstance(environment, dict):
        raise ConfigError("«environment» must be an object")
    try:
        return Config(merge(defaults, tz), environment, root, vocab), warnings
    except (KeyError, TypeError, ValueError, AttributeError) as e:
        raise ConfigError("traceability: invalid value (%s: %s)" % (type(e).__name__, e))


# --- Utilities -----------------------------------------------------------------------------------------------------

def rel(p):
    if p is None:
        return "(no path)"
    try:
        return str(p.relative_to(K.root))
    except ValueError:
        return str(p)


def relparts(f):
    try:
        return f.relative_to(K.root).parts
    except ValueError:
        return f.parts


def glob_files(patterns):
    found = set()
    for p in patterns:
        for f in K.root.glob(p):
            if f.is_file() and not (K.exclude & set(relparts(f))):
                found.add(f)
    return sorted(found)


def glob_dir(d, pattern):
    if d is None or not d.is_dir():
        return []
    return sorted(set(f for f in d.glob(pattern) if f.is_file() and not (K.exclude & set(relparts(f)))))


def field_prefix(key):
    return "- **%s:**" % K.field[key]


def _with_num(text, ini, end, n):
    """The ID `text` with the number between ini and end replaced by n (without leading zeros)."""
    return text[:ini] + str(n) + text[end:]


def expand_steps(text, errors=None, where=""):
    """W1.1-W1.4 (or W1.1–W1.4) → W1.1, W1.2, W1.3, W1.4; single IDs are returned as they are."""
    out = []
    for m in K.step_range.finditer(text):
        a, off = m.group("a"), m.start("a")
        ai, af = m.start("a_num") - off, m.end("a_num") - off
        first = int(m.group("a_num"))
        if m.group("b") is None:
            out.append(_with_num(a, ai, af, first))
            continue
        b, boff = m.group("b"), m.start("b")
        bi, bf = m.start("b_num") - boff, m.end("b_num") - boff
        if a[:ai] + a[af:] != b[:bi] + b[bf:]:
            if errors is not None:
                errors.append("%s: range across waves %s (write the steps of each wave)" % (where, m.group(0)))
            out.extend([_with_num(a, ai, af, first), b])
        else:
            out.extend(_with_num(a, ai, af, n) for n in range(first, int(m.group("b_num")) + 1))
    return out


def expand_acs(text):
    """AC-PED-02.1 to 02.3, 02.5 and 02.7 → the five full IDs.

    Separators: «,», «;» and «and»; «to» and «–» for ranges within the same requirement (the words come from the
    vocabulary: «y» and «a» in «es»).
    """
    out = []
    for m in K.ac_list.finditer(text):
        ac, off = m.group("ac"), m.start("ac")
        prefix = ac[:m.start("req") - off]
        short = ac[m.start("req") - off:]
        ni, nf = m.start("num") - m.start("req"), m.end("num") - m.start("req")
        num = int(m.group("num"))
        out.append(prefix + _with_num(short, ni, nf, num))
        prev = (m.group("req"), num)
        for t in K.ac_short.finditer(m.group("tail")):
            s, soff = t.group("s"), t.start("s")
            ti, tf = t.start("num") - soff, t.end("num") - soff
            r2, n2 = t.group("req"), int(t.group("num"))
            if t.group("sep").strip() in (K.g["to"], "–") and r2 == prev[0]:
                out.extend(prefix + _with_num(s, ti, tf, k) for k in range(prev[1] + 1, n2 + 1))
            else:
                out.append(prefix + _with_num(s, ti, tf, n2))
            prev = (r2, n2)
    return out


def _natural(x):
    return (0, int(x), "") if x.isdigit() else (1, 0, x)


def step_key(s):
    """Natural order of the steps: by wave and number (W2.10 after W2.9)."""
    m = K.step_one.fullmatch(s)
    if not m:
        return ((2, 0, s), (0, 0, ""))
    gd = m.groupdict()
    wave = gd.get("wave", gd.get("oleada"))  # «oleada» is the group name of the «es» vocabulary
    if wave is None:
        wave = s[:m.start("num")]
    return (_natural(wave), _natural(m.group("num")))


def wave_of(s):
    """The wave of a step: up to the end of the «wave» group (W2.1 → W2) or, without it, what precedes the number."""
    m = K.step_one.fullmatch(s)
    if not m:
        return s
    for g in ("wave", "oleada"):
        if m.groupdict().get(g) is not None:
            return s[:m.end(g)]
    return s[:m.start("num")].rstrip(".-_")


# --- Reading -------------------------------------------------------------------------------------------------------

def read_spec(errors, warnings):
    files = glob_files(K.specs)
    if not files:
        warnings.append("spec: there are no specs in %s yet" % ", ".join(K.specs))
    several = len(files) > 1
    reqs, acs, cited = {}, {}, {}
    for f in files:
        where = " (%s)" % f.name if several else ""
        text = f.read_text(encoding="utf-8")
        if K.req_end:
            text = text.split(K.req_end)[0]
        n = 0
        for block in re.split(r"^### ", text, flags=re.M)[1:]:
            m = K.req_head.match(block)
            if not m:
                continue
            n += 1
            rid = m.group(1)
            if rid in reqs:
                errors.append("spec: duplicate requirement %s%s" % (rid, where))
            prio = K.prio.search(block)
            if not prio:
                errors.append("spec: %s has no «%s»%s" % (rid, K.g["priority_field"], where))
            reqs[rid] = prio.group(1) if prio else "?"
            ids = K.ac_def.findall(block)
            if not ids:
                errors.append("spec: %s has no AC%s" % (rid, where))
            for cid in ids:
                if cid in acs:
                    errors.append("spec: duplicate AC %s%s" % (cid, where))
                acs[cid] = rid
        if n == 0:
            warnings.append("spec: %s has no requirements or AC yet" % rel(f))
        for cid in K.AC.findall(text):
            cited.setdefault(cid, f)
    for cid in sorted(set(cited) - set(acs)):
        errors.append("spec: %s is cited in Part 1, but is not defined as «- %s — …»%s"
                      % (cid, cid, " (%s)" % cited[cid].name if several else ""))
    return reqs, acs


def part1_ids(text):
    """{ID: normalized text} of Part 1.

    A requirement is its heading and its lines that are not AC (source, priority…), without the «Status», which is not
    a contract change. An AC is its requirement plus its line and continuations: moving it to another requirement
    modifies it."""
    if K.req_end:
        text = text.split(K.req_end)[0]
    out = {}
    for block in re.split(r"^### ", text, flags=re.M)[1:]:
        m = K.req_head.match(block)
        if not m:
            continue
        rid = m.group(1)
        block = re.split(r"^#{1,2}\s", block, maxsplit=1, flags=re.M)[0]  # the requirement ends at the next «#» or «##»
        lines = block.splitlines()
        own, i = [lines[0]], 1
        while i < len(lines):
            line = lines[i]
            c = K.ac_def.match(line)
            if c:
                parts = [line]
                for nxt in lines[i + 1:]:
                    if not nxt.startswith((" ", "\t")) or not nxt.strip():
                        break
                    parts.append(nxt)
                out[c.group(1)] = rid + " | " + " ".join(" ".join(parts).split())
                i += len(parts)
                continue
            if line.strip():
                own.append(K.req_state.sub("", line))
            i += 1
        out[rid] = " ".join(" ".join(own).split())
    return out


def change_log_rows(text):
    """IDs named by the rows of the «Change log» section of a spec."""
    m = re.search(r"^##\s+%s\s*$" % re.escape(K.change_log_section), text, flags=re.M)
    if not m:
        return set()
    section = re.split(r"^#{1,2}\s", text[m.end():], maxsplit=1, flags=re.M)[0]
    ids = set()
    for line in section.splitlines():
        if line.startswith("|") and not re.match(r"^\|[\s|:-]+\|?\s*$", line):
            clean = line.replace("`", "")
            ids.update(K.R.findall(clean))
            ids.update(expand_acs(clean))
            ids.update(K.AC.findall(clean))
    return ids


def git(*args):
    """git output at the project root, or None if git is not there or fails."""
    try:
        r = subprocess.run(["git", "-C", str(K.root)] + list(args), capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout if r.returncode == 0 else None


def base_tag():
    """The tag the deltas are counted from: the most recent one of the first pattern that has any (by default,
    release-* and then design-approved). None if there is no git or no tag."""
    for pattern in K.tags:
        output = git("tag", "--list", pattern, "--sort=-v:refname")
        if output is None:
            return None
        tags = [x.strip() for x in output.splitlines() if x.strip()]
        if tags:
            return tags[0]
    return None


def specs_at(base):
    """Paths (relative to the project) of the specs that existed at the base tag."""
    prefix = git("rev-parse", "--show-prefix")
    output = git("ls-tree", "-r", "--name-only", "--full-tree", base)
    if output is None or prefix is None:
        return []
    prefix = prefix.strip()
    paths = [r[len(prefix):] for r in output.splitlines() if r.startswith(prefix)]
    return [r for r in paths if any(fnmatch.fnmatch(r, pat) for pat in K.specs)]


def check_change_log(errors):
    """Each requirement or AC added, modified or removed since the base tag has a row in some «Change log». The set of
    all specs is compared, so deleting a spec removes its IDs and renaming it changes nothing. Returns the tag
    compared with, or None if nothing is compared."""
    base = base_tag()
    if not base:
        return None
    before, now, rows, where = {}, {}, set(), {}
    for r in specs_at(base):
        previous = part1_ids(git("show", "%s:./%s" % (base, r)) or "")
        before.update(previous)
        for i in previous:
            where.setdefault(i, r)
    for f in glob_files(K.specs):
        current = f.read_text(encoding="utf-8")
        for i in part1_ids(current):
            where[i] = rel(f)
        now.update(part1_ids(current))
        rows |= change_log_rows(current)
    changes = [(i, "added") for i in now if i not in before]
    changes += [(i, "removed") for i in before if i not in now]
    changes += [(i, "modified") for i in now if i in before and now[i] != before[i]]
    for i, kind in sorted(changes, key=lambda x: _natural(x[0])):
        if i not in rows:
            errors.append("change_log: %s %s since %s without a row in «%s» (%s)"
                          % (i, kind, base, K.change_log_section, where[i]))
    return base


def read_steps(errors):
    """Steps («### W1.1 — …») with their fields «- **Depends on:**», «Satisfies», «Test first», «Parallel with»,
    «Size» and «Skill», continuation lines included (indented with two spaces)."""
    steps, fields = {}, {}
    for f in glob_files(K.steps):
        current, field = None, None
        for line in f.read_text(encoding="utf-8").splitlines():
            m = K.step_head.match(line)
            if m:
                current, field = m.group(1), None
                if current in steps:
                    errors.append("steps: duplicate %s (%s)" % (current, f.name))
                steps[current] = f.name
                fields[current] = dict((c, "") for c in FIELDS)
                continue
            if current is None:
                continue
            if line.startswith("## "):
                current, field = None, None
                continue
            m = re.match(r"- \*\*([^*:]+):\*\*", line)
            if m:
                field = K.field_by_name.get(m.group(1))
                if field:
                    fields[current][field] = line
            elif line.startswith("  ") and field:
                fields[current][field] += " " + line.strip()
            else:
                field = None
    return steps, fields


def split_outside_parens(text, sep=";"):
    """Splits on «;» that are not inside parentheses («(real data; the controller)» does not split)."""
    out, depth, cur = [], 0, []
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if ch == sep and depth == 0:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    out.append("".join(cur))
    return out


def outside_parens(text):
    """The text without what is inside parentheses."""
    out, depth = [], 0
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif depth == 0:
            out.append(ch)
    return "".join(out)


def parse_deps(fields, errors):
    """FS: a plain «Depends on»; FF: the «to close: …» segment (up to the next «;» outside parentheses)."""
    fs, ff = {}, {}
    for s, v in fields.items():
        fs[s], ff[s] = [], []
        text = v["depends"].replace(field_prefix("depends"), "")
        for seg in split_outside_parens(text):
            target = ff[s] if K.to_close in seg else fs[s]
            target.extend(expand_steps(seg, errors, "steps: %s «%s»" % (s, K.field["depends"])))
    return fs, ff


def find_cycles(deps):
    color, cycles = {}, []

    def visit(node, path):
        color[node] = 1
        for nxt in deps.get(node, []):
            if color.get(nxt) == 1:
                cycles.append(" → ".join(path[path.index(nxt):] + [nxt]) if nxt in path else node + " → " + nxt)
            elif color.get(nxt) is None and nxt in deps:
                visit(nxt, path + [nxt])
        color[node] = 2

    for n in deps:
        if color.get(n) is None:
            visit(n, [n])
    return cycles


def ancestors(deps, node, seen=None):
    seen = set() if seen is None else seen
    for d in deps.get(node, []):
        if d not in seen and d in deps:
            seen.add(d)
            ancestors(deps, d, seen)
    return seen


def satisfied_acs(line, req_acs):
    """AC cited by a «Satisfies»: a whole R-XX, R-XX (AC-…), R-XX (except AC-…) or single AC.

    What follows the end markers («**Source:**», «validates the design of») is ignored.
    """
    text = line.replace(field_prefix("satisfies"), "")
    for cut in K.satisfies_end:
        text = text.split(cut)[0]
    out = set()
    for m in K.satisfies_span.finditer(text):
        rid, paren = m.group(1), m.group(2) or ""
        allc = set(req_acs.get(rid, []))
        listed = set(expand_acs(paren))
        if K.except_mark in paren:
            out |= allc - listed
        elif listed:
            out |= listed
        else:
            out |= allc
    out |= set(expand_acs(K.satisfies_span.sub(" ", text)))
    return out


def skill_names(line):
    """Skills of a «Skill» field: the names between backticks, outside parentheses, without repeats."""
    text = outside_parens(line.replace(field_prefix("skill"), ""))
    out = []
    for n in re.findall(r"`([^`]+)`", text):
        if n.strip() and n.strip() not in out:
            out.append(n.strip())
    return out


def norm_skill(name):
    """«plugin:skill» → «skill»."""
    return name.split(":")[-1].strip()


def classify(label):
    for pat, kind in K.verifications:
        m = pat.fullmatch(label)
        if m:
            return kind, (m.group(1) if m.groups() else None)
    return None, None


def parse_verif(cid, cell, row_steps, errors):
    """«Apex test (W2.1); demo step (W2.16)» → [(label, type, [steps])]."""
    items = []
    builders = [s for s in row_steps if s != K.closing_step]
    for raw in [x.strip() for x in cell.split(";")]:
        if not raw:
            continue
        m = K.verif_tagged.match(raw)
        label, tagged = (m.group(1).strip(), expand_steps(m.group(2))) if m else (raw, None)
        kind, step_label = classify(label)
        if kind is None:
            errors.append("traceability: %s has a verification outside the vocabulary: «%s»" % (cid, raw))
            continue
        if step_label:
            steps = [step_label]
        elif tagged:
            steps = tagged
        elif len(builders) == 1:
            steps = builders
        else:
            errors.append("traceability: %s: «%s» does not say which step builds it (add «(%s)»)"
                          % (cid, raw, K.step_example))
            continue
        items.append((label, kind, steps))
    return items


def line_cites(line):
    """AC cited on a line, unless the line denies coverage."""
    if (K.negation and K.negation.search(line)) or (K.mark and K.mark.search(line)):
        return set()
    return set(K.AC.findall(line))


def text_cites(text, only_section=False):
    """AC cited in a text; with only_section, only under «## Verification cases» (up to the next «#»/«##»)."""
    cited, inside = set(), not only_section
    for line in text.splitlines():
        if only_section and re.match(r"^#{1,2}\s", line):
            inside = bool(K.report_section.match(line))
            continue
        if inside:
            cited |= line_cites(line)
    return cited


def files_cites(paths, only_section=False):
    """{file: AC cited outside negation lines} (in step reports, only in their cases section)."""
    out = {}
    for f in paths:
        out[f] = text_cites(f.read_text(encoding="utf-8", errors="replace"), only_section)
    return out


def review_files():
    """Review reports: the .md files of the «reviews/<date>-<step>/» folders (and their subfolders)."""
    out = []
    if K.reviews is not None and K.reviews.is_dir():
        for d in K.reviews.iterdir():
            if d.is_dir() and K.review_dir.search(d.name):
                out.extend(glob_dir(d, "**/*.md"))
    return sorted(set(out))


def evidence_index():
    """Evidence files by group: one per type with sources, plus «step_reports», «validations», «reviews» and
    «walkthrough»."""
    index = {}
    for name, t in K.types.items():
        if t["mode"] in ("classes", "sources"):
            index[name] = glob_files(t["sources"])
    index["step_reports"] = glob_dir(K.reports, "*.md")
    index["validations"] = [K.prior] if K.prior is not None and K.prior.is_file() else []
    index["reviews"] = review_files()
    index["walkthrough"] = [K.walkthrough] if K.walkthrough is not None and K.walkthrough.is_file() else []
    return index


def required_files(kind, step, index, named):
    t = K.types[kind]
    mode = t["mode"]
    if mode == "classes":
        names = named.get(kind, {}).get(step, set())
        files = [f for f in index[kind] if not names or f.stem in names]
        where = ("the classes %s" % ", ".join(sorted(names))) if names else t["where"]
        return files, where
    if mode == "report":
        f = K.reports / ("%s.md" % step) if K.reports is not None else None
        return [x for x in index["step_reports"] if x == f], rel(f)
    if mode == "review":
        return ([f for f in index["reviews"] if any(p.endswith("-" + step) for p in relparts(f))],
                "%s/<date>-%s/" % (rel(K.reviews), step))
    if mode == "validations":
        return index["validations"], rel(K.prior)
    return index[kind], t["where"]


def read_lanes():
    """Scope → steps, from the «Scopes and files» table of integration.md (None if there is no integration.md)."""
    if K.integ is None or not K.integ.is_file():
        return None
    lanes, in_table = {}, False
    lines = K.integ.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        if line.startswith("## "):
            in_table = line.startswith("## " + K.sec_scopes)
            continue
        if in_table and line.startswith("| ") and not line.startswith("|---"):
            if i + 1 < len(lines) and lines[i + 1].startswith("|---"):
                continue  # the table header
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) > 1:
                lanes[cells[0]] = expand_steps(cells[1])
    return lanes


def integrated_steps(text):
    """Steps that the «Steps» table of status.md gives as integrated or closed («State» column, the fourth).

    «W1.7b + W2.18 · …» counts both steps; «in the org», «pending», «absorbed» or «not integrated» do not count.
    """
    out, inside = set(), False
    col = K.status_col - 1
    for line in text.splitlines():
        if line.startswith("## "):
            inside = line.strip() == "## " + K.status_section
            continue
        if not inside or not K.status_row.match(line):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) > col and K.integrated.search(cells[col]) and not K.not_integrated.search(cells[col]):
            out.update(K.STEP.findall(cells[0].split("·")[0]))
    return out


def check_skills(steps, fields, errors, warnings):
    """The «Skill» of each step against the environment inventory (docs/baseline/environment.json, from
    check-environment.py)."""
    if not steps:
        return
    inv = K.inventory
    if inv is None or not inv.is_file():
        warnings.append("environment: no environment inventory (%s): run check-environment.py; the «%s» of the steps "
                        "is not checked" % (rel(inv), K.field["skill"]))
        return
    try:
        data = V.inventory(json.loads(inv.read_text(encoding="utf-8")))
    except (ValueError, OSError) as e:
        errors.append("environment: cannot read the inventory %s (%s)" % (rel(inv), e))
        return
    skills = data.get("skills") if isinstance(data, dict) else None
    if not isinstance(skills, dict):
        errors.append("environment: the inventory %s has no «skills»" % rel(inv))
        return
    state = dict((norm_skill(k), (v.get("state") if isinstance(v, dict) else None)) for k, v in skills.items())
    agents = set(norm_skill(a) for a in (data.get("agents") or []) if isinstance(a, str))
    for s in sorted(steps, key=step_key):
        line = fields[s]["skill"]
        if not line:
            warnings.append("steps: %s has no «%s»: it does not say which skill runs it" % (s, K.field["skill"]))
            continue
        names = skill_names(line)
        if not names:
            warnings.append("steps: %s: «%s» names no skill between backticks" % (s, K.field["skill"]))
        for name in names:
            n = norm_skill(name)
            if n in state:
                e = state[n]
                if e == "missing":
                    errors.append("steps: %s uses the skill `%s`, which is missing in the environment inventory"
                                  % (s, name))
                elif e == "shadowed":
                    warnings.append("steps: %s uses the skill `%s`, which is shadowed by another copy (see the "
                                    "environment inventory)" % (s, name))
                elif e != "present":
                    warnings.append("steps: %s uses the skill `%s`, with an unknown state in the inventory: «%s»"
                                    % (s, name, e))
            elif n not in agents:
                errors.append("steps: %s uses the skill `%s`, which is not in the environment inventory" % (s, name))


# --- Graph ---------------------------------------------------------------------------------------------------------

def schedule(steps, size, fs, ff):
    """Earliest finish of each step: it starts after its FS and does not finish before its FF.

    It marks the steps being visited: a cycle raises CycleError instead of exhausting the recursion.
    """
    start, finish, visiting = {}, {}, []

    def end(s):
        if s not in finish:
            if s in visiting:
                raise CycleError(" → ".join(visiting[visiting.index(s):] + [s]))
            visiting.append(s)
            start[s] = max([end(d) for d in fs[s] if d in steps] or [0])
            finish[s] = max([start[s] + size[s]] + [end(d) for d in ff[s] if d in steps])
            visiting.pop()
        return finish[s]

    for s in steps:
        end(s)
    return start, finish


def critical_chains(steps, size, fs, ff, start, finish, limit=MAX_CHAINS):
    end = max(finish.values())
    chains = []

    def back(s, tail):
        drivers = []
        if start[s] + size[s] == finish[s]:
            drivers += [d for d in fs[s] if d in steps and finish[d] == start[s] and start[s] > 0]
        drivers += [d for d in ff[s] if d in steps and finish[d] == finish[s]]
        if not drivers:
            if len(chains) < limit:
                chains.append([s] + tail)
            return
        for d in sorted(set(drivers), key=step_key):
            back(d, [s] + tail)

    for s in sorted([s for s in steps if finish[s] == end], key=step_key):
        back(s, [])
    return end, chains


def graph(steps, fields, fs, ff, rows):
    errors = []
    size = {}
    for s, v in fields.items():
        m = K.size_re.search(v["size"])
        if not m:
            errors.append("graph: %s has no «%s» %s" % (s, K.field["size"], K.sizes_text))
        size[s] = K.sizes[m.group(1)] if m else 0
    n_ac = dict((s, sum(1 for ps in rows.values() if s in ps)) for s in steps)
    for s in sorted(steps, key=step_key):
        letter = K.size_name.get(size[s], "?")
        if letter == "?":
            continue  # it already has its «has no Size» error
        for since, name, text in K.rule_per_ac:
            if n_ac[s] >= since:
                if size[s] < K.sizes[name]:
                    errors.append("size rule: %s has %d AC and is %s (%s)" % (s, n_ac[s], letter, text))
                break
        external = K.external.findall(fields[s]["depends"]) if K.external else []
        if external and K.external_size and size[s] < K.sizes[K.external_size]:
            errors.append("size rule: %s depends on %s and is %s (external dependency → %s)"
                          % (s, ", ".join(sorted(set(external))), letter, K.external_size))
    waves, wave_key = {}, {}
    for s in steps:
        w = wave_of(s)
        waves.setdefault(w, []).append(size[s])
        wave_key.setdefault(w, step_key(s)[0])
    print("Size: %d units in %d steps (%s)" % (sum(size.values()), len(steps), " · ".join(
        "%s %d" % (w, sum(waves[w])) for w in sorted(waves, key=lambda w: (wave_key[w], w)))))
    lanes = read_lanes()
    if lanes is None:
        print("  no %s: the scopes are not checked" % rel(K.integ))
    else:
        for lane, ls in lanes.items():
            print("  scope %s: %d units (%s)" % (lane, sum(size.get(s, 0) for s in ls), ", ".join(ls)))
        missing = sorted(set(steps) - set(s for ls in lanes.values() for s in ls), key=step_key)
        if missing:
            errors.append("graph: steps without a scope in %s: %s" % (K.integ.name, ", ".join(missing)))
    if not steps:
        print("Critical path: no steps")
        return errors
    try:
        start, finish = schedule(steps, size, fs, ff)
    except CycleError as e:
        errors.append("graph: no critical path, because there is a cycle (%s)" % e)
        return errors
    end, chains = critical_chains(steps, size, fs, ff, start, finish)
    print("Critical path: %d units, %d chain(s)%s" % (end, len(chains),
                                                     "" if len(chains) < MAX_CHAINS else " or more"))
    for c in chains:
        print("  " + " → ".join(c))
    crit = sorted(set(s for c in chains for s in c), key=step_key)
    print("Critical steps: %s" % ", ".join(crit))
    print("Earliest start and finish:")
    for s in sorted(steps, key=step_key):
        letter = K.size_name.get(size[s], "?")
        print("  %s %s %2d→%2d · %d AC" % (s, letter, start[s], finish[s], n_ac[s]))
    return errors


def graph_or_warning(cycles, steps, fields, fs, ff, rows, verbose=True):
    """With a cycle there is no critical path: it says so and does not call graph()."""
    if cycles:
        if verbose:
            print("Graph: not computed, because there are %d cycle(s); see the «steps: cycle» errors" % len(cycles))
        return ["graph: no critical path with cycles (%s)" % "; ".join(cycles)]
    return graph(steps, fields, fs, ff, rows)


# --- Self-test -----------------------------------------------------------------------------------------------------

# To repeat the mutations with the «en» vocabulary: the structural tokens of the examples, in order.
_TO_EN = [("CA-", "AC-"), ("Depende de", "Depends on"), ("para cerrar", "to close"), ("Tamaño", "Size"),
          ("Casos de verificación", "Verification cases"), ("No cubre", "Does not cover"),
          ("sin cubrir", "not covered"), ("no verifica", "does not verify"), ("## Pasos\n", "## Steps\n"),
          ("**integrado y desplegado**", "**integrated and deployed**"), ("**integrado**", "**integrated**"),
          ("**cerrado**", "**closed**"), ("sin integrar", "not integrated"), ("| integrado |", "| integrated |"),
          ("en el org (tests verdes)", "in the org (green tests)"), (" a 02.3, 02.5 y 03.1", " to 02.3, 02.5 and 03.1"),
          ("W2.10–W2.11 y W3.2", "W2.10–W2.11 and W3.2"), ("` a `01.2`", "` to `01.2`"), ("# Parte 1", "# Part 1"),
          ("# Parte 2", "# Part 2"), ("Prioridad: ", "Priority: "), ("Estado: ", "Status: "),
          ("## Registro de cambios", "## Change log"), ("diseno-aprobado", "design-approved")]


def _translator(vocab):
    """The examples are written in the «es» vocabulary; with «en», their structural tokens are translated."""
    def t(x):
        if vocab == "es":
            return x
        if isinstance(x, (list, tuple, set)):
            return type(x)(t(e) for e in x)
        if isinstance(x, str):
            for a, b in _TO_EN:
                x = x.replace(a, b)
        return x
    return t


def self_test():
    """Own mutations, with the default configuration of each vocabulary («es» and «en»): the negation filter, the
    step report section, «Depends on», the graph with a cycle, the «Steps» table of status.md, the AC and step lists,
    «Skill», the change log and the reading of the configuration and of the inventory."""
    global K
    failed = total = 0
    for vocab in V.VOCABULARIES[::-1]:
        K = Config(V.traceability_defaults(vocab), {}, pathlib.Path.cwd(), vocab)
        cases = _cases(_translator(vocab)) + _self_test_change_log(_translator(vocab)) + _self_test_config(vocab)
        for name, got, want in cases:
            ok = got == want
            failed += 0 if ok else 1
            print("%s  [%s] %s%s" % ("OK   " if ok else "FAIL ", vocab, name,
                                     "" if ok else " (got %r, expected %r)" % (got, want)))
        total += len(cases)
    print("Self-test: %d of %d" % (total - failed, total))
    return 1 if failed else 0


def _cases(t):
    ac = t("CA-PED-01.2")
    cases = [
        ("A01 a lowercase «todo» inside a word counts", line_cites("// %s: un método por CA" % ac), {ac}),
        ("A02 «todos» counts", line_cites("Se cambian todos los registros (%s)" % ac), {ac}),
        ("A03 «Todo» with an initial capital counts", line_cites("Todo listo: %s" % ac), {ac}),
        ("A04 TODO in capitals does not count", line_cites("// TODO %s" % ac), set()),
        ("A05 «does not cover» does not count", line_cites(t("No cubre todavía %s") % ac), set()),
        ("A06 «not covered» does not count", line_cites(t("%s, sin cubrir") % ac), set()),
        ("A07 «does not verify» does not count", line_cites(t("Esto no verifica %s") % ac), set()),
        ("A08 step report: only the cases section", text_cites(
            t("# Ficha\n%s\n## Casos de verificación\n### Caso 1\nCA-PED-01.3\n## Preparación\nCA-PED-01.4\n") % ac,
            only_section=True), {t("CA-PED-01.3")}),
        ("A09 without the section, the step report cites nothing", text_cites("# Ficha\n%s\n" % ac, only_section=True),
         set()),
    ]
    fields = {"W9.1": {"depends": t("- **Depende de:** W1.1 integrado; para cerrar: W2.3 integrado (datos "
                                    "reales; el controlador) y W2.17")}}
    errs = []
    fs, ff = parse_deps(fields, errs)
    cases.append(("A10 a «;» inside parentheses does not split «to close»", (fs["W9.1"], ff["W9.1"]),
                  (["W1.1"], ["W2.3", "W2.17"])))
    # W2.17 in the «to close» of W2.7, with W2.17 already closing after W2.7
    cycle = {"W2.7": {"depends": t("- **Depende de:** W1.1 integrado; para cerrar: W2.17 integrado"),
                      "size": t("- **Tamaño:** L.")},
             "W2.17": {"depends": t("- **Depende de:** W1.1 integrado; para cerrar: W2.7 integrado"),
                       "size": t("- **Tamaño:** L.")}}
    cfs, cff = parse_deps(cycle, [])
    steps9 = {"W2.7": "W2.md", "W2.17": "W2.md"}
    cycles9 = find_cycles(dict((s, cfs[s] + cff[s]) for s in steps9))
    cases.append(("A11 find_cycles sees the cycle W2.7 → W2.17", bool(cycles9), True))
    try:
        schedule(steps9, {"W2.7": 3, "W2.17": 3}, cfs, cff)
        raised = "no error"
    except CycleError:
        raised = "CycleError"
    except RecursionError:
        raised = "RecursionError"
    cases.append(("A12 schedule() with a cycle raises CycleError, not RecursionError", raised, "CycleError"))
    try:
        errs9 = graph_or_warning(cycles9, steps9, cycle, cfs, cff, {}, verbose=False)
        graph_ok = len(errs9) == 1 and errs9[0].startswith("graph: no critical path")
    except (CycleError, RecursionError) as e:
        graph_ok = type(e).__name__
    cases.append(("A13 --graph with a cycle gives one error and does not break", graph_ok, True))
    status = t("## Pasos\n| Paso | Ámbito | Rama | Estado |\n|---|---|---|---|\n"
               "| W2.4 · Pedidos | a | b | **integrado** (2026-01-10) |\n"
               "| W2.7 · Devoluciones | a | b | **cerrado** (2026-01-10) |\n"
               "| W1.7b + W2.18 · Integración | a | b | **integrado y desplegado** |\n"
               "| W2.14 · Login | a | b | en el org (tests verdes) |\n"
               "| W2.9 · Emails | a | b | listo, sin integrar |\n"
               "| W4.2 · Recorrido | — | — | pendiente |\n"
               "## Otra\n| W3.1 · Agente | a | b | integrado |\n")
    cases.append(("A14 status.md: integrated and closed in the «Steps» table, not «in the org» or «not integrated»",
                  sorted(integrated_steps(status), key=step_key), ["W1.7", "W2.4", "W2.7", "W2.18"]))
    cases.append(("A15 AC list with a range, short form and another requirement",
                  expand_acs(t("CA-PED-02.1 a 02.3, 02.5 y 03.1; CA-FAC-01.1")),
                  t(["CA-PED-02.1", "CA-PED-02.2", "CA-PED-02.3", "CA-PED-02.5", "CA-PED-03.1", "CA-FAC-01.1"])))
    errs15 = []
    cases.append(("A16 step ranges; a range across waves is an error",
                  (expand_steps(t("W1.1-W1.3, W2.10–W2.11 y W3.2"), errs15), expand_steps("W1.4-W2.1", errs15),
                   len(errs15)),
                  (["W1.1", "W1.2", "W1.3", "W2.10", "W2.11", "W3.2"], ["W1.4", "W2.1"], 1)))
    cases.append(("A17 «Skill»: backticks outside parentheses, «plugin:skill» → «skill»",
                  [norm_skill(n) for n in skill_names("- **Skill:** `plugin-x:skill-a`, `skill-b` (con `no-cuenta`), "
                                                      "`skill-a`.")],
                  ["skill-a", "skill-b", "skill-a"]))
    cases.append(("A18 natural order of steps", sorted(["W2.10", "W10.1", "W2.9", "W1.1"], key=step_key),
                  ["W1.1", "W2.9", "W2.10", "W10.1"]))
    return cases


def _self_test_change_log(t):
    """AC-EVO-02.2 and 02.3 on a temporary git repository."""
    global K
    old = K
    spec = t("# Spec\n# Parte 1\n### R-PED-01 — Ver pedidos\n- Prioridad: P0 · Estado: Ready\n"
             "- CA-PED-01.1 — Dado un usuario, cuando abre la página, entonces ve sus pedidos.\n"
             "- CA-PED-01.2 — Dado un usuario sin pedidos, cuando abre la página, entonces ve un aviso.\n"
             "# Parte 2\n## Registro de cambios\n\n| Fecha | Tipo | IDs | Antes → después | ¿Cambia? | Origen | "
             "Aprobación | Commit |\n|---|---|---|---|---|---|---|---|\n")
    row = t("| 2026-11-06 | MODIFICADO | `CA-PED-01.2` | aviso → aviso con enlace | sí | CH-001 | Ana | abc |\n")
    tag = t("diseno-aprobado")
    cases = []
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        K = Config(V.traceability_defaults(old.vocab), {}, root, old.vocab)
        (root / "knowledge/specs").mkdir(parents=True)
        f = root / "knowledge/specs/2026-11-05-001_pedidos.md"
        f.write_text(spec, encoding="utf-8")

        def errors():
            e = []
            return check_change_log(e), e
        cases.append(("A19 without git: no comparison and no error", errors(), (None, [])))
        ident = ["-c", "user.name=t", "-c", "user.email=t@example.com"]
        if git("init", "-q") is None:
            K = old
            return [("A20-A31 git not available: the change log is not tested", True, True)]
        git(*ident, "add", "-A"); git(*ident, "commit", "-q", "-m", "spec")
        cases.append(("A20 without tags: no comparison", errors(), (None, [])))
        git("tag", tag)
        f.write_text(spec.replace("ve un aviso", "ve un aviso con un enlace"), encoding="utf-8")
        base, e = errors()
        cases.append(("A21 modified AC without a row: error with the ID and the tag",
                      (base, len(e), t("CA-PED-01.2 modified since diseno-aprobado") in (e[0] if e else "")),
                      (tag, 1, True)))
        f.write_text(spec.replace("ve un aviso", "ve un aviso con un enlace") + row, encoding="utf-8")
        cases.append(("A22 with its row in the change log: no errors", errors(), (tag, [])))
        f.write_text(spec.replace("cuando abre la página, entonces ve un aviso",
                                  "cuando  abre la página,\n  entonces ve un aviso"), encoding="utf-8")
        cases.append(("A23 only whitespace and line breaks: not a change", errors(), (tag, [])))
        f.write_text(spec.replace(t("- CA-PED-01.2 — Dado un usuario sin pedidos, cuando abre la página, entonces ve "
                                    "un aviso.\n"), "").replace(t("Estado: Ready"), t("Estado: Implemented"))
                     + t("- CA-PED-01.3 — Dado x, cuando y, entonces z.\n"), encoding="utf-8")
        base, e = errors()
        cases.append(("A24 removed AC without a row: error; changing the «Status» of the requirement does not count",
                      sorted(x.split()[1] + " " + x.split()[2] for x in e), t(["CA-PED-01.2 removed"])))
        f.write_text(spec, encoding="utf-8")
        for tg in ("release-9", "release-10"):
            git("tag", tg)
        cases.append(("A25 compares with the most recent release-N (release-10 > release-9)", errors()[0],
                      "release-10"))
        g = root / "knowledge/specs/2026-11-06-002_nueva.md"
        g.write_text(spec.replace("R-PED-01", "R-FAC-01").replace(t("CA-PED-01"), t("CA-FAC-01")), encoding="utf-8")
        cases.append(("A26 a new spec after the tag: its IDs are added",
                      len(errors()[1]), 3))
        g.unlink()
        git(*ident, "add", "-A"); git(*ident, "commit", "-q", "-m", "base"); git("tag", "release-11")
        renamed = root / "knowledge/specs/2026-11-07-001_pedidos-v2.md"
        git("mv", str(f), str(renamed))
        cases.append(("A27 renaming the spec is not a change", errors(), ("release-11", [])))
        renamed.unlink()
        cases.append(("A28 deleting the spec removes its IDs: one error for each",
                      sorted(x.split()[1] + " " + x.split()[2] for x in errors()[1]),
                      t(["CA-PED-01.1 removed", "CA-PED-01.2 removed", "R-PED-01 removed"])))
        f.write_text(spec.replace(t("Prioridad: P0"), t("Prioridad: P1")), encoding="utf-8")
        cases.append(("A29 changing the priority modifies the requirement",
                      [x.split()[1] + " " + x.split()[2] for x in errors()[1]], ["R-PED-01 modified"]))
        two = spec.replace(t("- CA-PED-01.2 — Dado un usuario sin pedidos"), t("### R-PED-02 — Sin pedidos\n"
                           "- Prioridad: P0 · Estado: Ready\n- CA-PED-01.2 — Dado un usuario sin pedidos"))
        f.write_text(two, encoding="utf-8")
        cases.append(("A30 moving an AC to another requirement modifies it",
                      sorted(x.split()[1] + " " + x.split()[2] for x in errors()[1]),
                      t(["CA-PED-01.2 modified", "R-PED-02 added"])))
        f.write_text(two + t("| 2026-11-07 | MODIFICADO | `CA-PED-01.2` a `01.2`; `R-PED-02` | mover | no | CH-2 | Ana | "
                             "x |\n"), encoding="utf-8")
        cases.append(("A31 IDs between backticks and in short form count", errors()[1], []))
        git(*ident, "add", "-A"); git(*ident, "commit", "-q", "-m", "mover"); git("tag", "release-12")
        f.write_text(two.replace(t("# Parte 2"), t("## Supuestos y pendientes\n- Ninguno todavía.\n\n# Parte 2")),
                     encoding="utf-8")  # no rows: if the requirement changed, there would be an error
        cases.append(("A32 a «##» section after the last requirement does not modify it", errors(), ("release-12", [])))
    K = old
    return cases


def _self_test_config(vocab):
    """AC-VOC-01.3 and 01.5: the vocabulary of the configuration, its aliases and the inventory in both languages."""
    global K
    old = K
    cases = []
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)

        def with_config(cfg):
            (root / "sdd.config.json").write_text(json.dumps(cfg), encoding="utf-8")
            try:
                k, warns = load(str(root), None)
                return k.vocab, k.AC.pattern[:2], warns
            except ConfigError as e:
                return "ConfigError", str(e)
        if vocab == "es":
            cases.append(("A33 «metodo» without «method»: vocabulary es", with_config({"metodo": {"version": "0.3.0"}}),
                          ("es", "CA", [])))
            cases.append(("A34 «method» or no method: vocabulary en",
                          (with_config({"method": {}})[:2], with_config({})[:2]), (("en", "AC"), ("en", "AC"))))
            cases.append(("A35 method.vocabulary decides", with_config({"metodo": {"vocabulary": "en"}})[:2],
                          ("en", "AC")))
            cases.append(("A41 «metodo» plus an English «method»: still es, «metodo» keys kept (review 12, F-001)",
                          (with_config({"metodo": {"version": "0.3.0"}, "method": {"language": "es"}})[:2],
                           with_config({"metodo": {}, "method": {"vocabulary": "en"}})[:2]), (("es", "CA"), ("en", "AC"))))
            cases.append(("A36 unknown vocabulary: error", with_config({"method": {"vocabulary": "fr"}})[0],
                          "ConfigError"))
            both = with_config({"method": {"vocabulary": "es"}, "trazabilidad": {"campos": {"tamano": "Talla",
                                                                                         "cumple": "Cubre"}},
                                "traceability": {"fields": {"size": "Medida"}}})
            k, _ = load(str(root), None)
            cases.append(("A37 the same key in both languages: merged key by key; where both differ, the English one "
                          "wins with a warning", (both[0], len(both[2]), "«traceability» wins" in (both[2] or [""])[0],
                                                  k.field["size"], k.field["satisfies"]),
                          ("es", 1, True, "Medida", "Cubre")))
            (root / "sdd.config.json").write_text(json.dumps({"metodo": {}, "trazabilidad": {
                "campos": {"tamano": "Talla"}, "tipos": {"ficha": {"modo": "ficha"}, "ux": {"modo": "fuentes", "fuentes": "ux/*.md"}},
                "regla_tamano": {"por_ca": {"M": 3}}}}), encoding="utf-8")
            k, warns = load(str(root), None)
            cases.append(("A38 Spanish keys and values are translated; type and size names are not",
                          (k.field["size"], k.types["ux"]["mode"], k.types["ux"]["sources"], k.types["ficha"]["mode"],
                           [x[:2] for x in k.rule_per_ac], warns),
                          ("Talla", "sources", ["ux/*.md"], "report", [(11, "L"), (3, "M")], [])))
        K = Config(V.traceability_defaults(vocab), {}, root, vocab)
        K.inventory = root / "inv.json"
        steps = {"W1.1": "W1.md"}
        results = []
        for inv in ({"skills": {"a": {"estado": "presente"}, "b": {"estado": "ausente"}, "c": {"estado": "tapada"}},
                     "agentes": ["d"]},
                    {"skills": {"a": {"state": "present"}, "b": {"state": "missing"}, "c": {"state": "shadowed"}},
                     "agents": ["d"]}):
            K.inventory.write_text(json.dumps(inv), encoding="utf-8")
            errs, warns = [], []
            check_skills(steps, {"W1.1": {"skill": "- **Skill:** `a`, `b`, `c`, `d`"}}, errs, warns)
            results.append((len(errs), len(warns)))
        cases.append(("A39 inventory in Spanish or in English: the same result", results, [(1, 1), (1, 1)]))
        if vocab == "en":
            example = json.loads((pathlib.Path(__file__).resolve().parent / "sdd.config.example.json")
                                 .read_text(encoding="utf-8")).get("traceability", {})
            example.pop("_doc", None)
            cases.append(("A40 sdd.config.example.json has the defaults of the en vocabulary",
                          example == V.traceability_defaults("en"), True))
    K = old
    return cases


# --- Check ---------------------------------------------------------------------------------------------------------

def read_traceability(acs, steps, errors):
    rows, items, states, excluded, no_ac = {}, {}, {}, set(), set()
    if K.trace is None or not K.trace.is_file():
        errors.append("traceability: %s does not exist" % rel(K.trace))
        return rows, items, states, excluded, no_ac
    section = ""
    for line in K.trace.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            section = line[3:].strip().lower()
            continue
        if not line.startswith("| ") or line.startswith("|---"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if section.startswith(K.sec_excl.lower()):
            ids = K.AC.findall(cells[0])
            if not ids:
                continue
            excluded.update(ids)
            reason, who = (cells + ["", "", ""])[1:3]
            for cid in ids:
                if reason in ("", "—", "-") or reason.lower().startswith(K.g["no_reason"]):
                    errors.append("traceability: the exclusion of %s has no reason" % cid)
                if who in ("", "—", "-"):
                    errors.append("traceability: the exclusion of %s does not say who agreed to it" % cid)
            continue
        if section.startswith(K.sec_no_ac.lower()):
            no_ac.update(expand_steps(cells[0], errors, "traceability «%s»" % K.sec_no_ac))
            continue
        if len(cells) < 6 or not K.AC.fullmatch(cells[1]):
            continue
        rid, cid, _, step_cell, verif, state = cells[:6]
        if cid in rows:
            errors.append("traceability: duplicate %s" % cid)
        if cid not in acs:
            errors.append("traceability: %s does not exist in the spec" % cid)
        elif acs[cid] != rid:
            errors.append("traceability: %s belongs to %s, not to %s" % (cid, acs[cid], rid))
        row_steps = expand_steps(step_cell, errors, "traceability: %s" % cid)
        if not row_steps:
            errors.append("traceability: %s has no step" % cid)
        for p in row_steps:
            if p not in steps:
                errors.append("traceability: %s points to %s, which does not exist" % (cid, p))
        its = parse_verif(cid, verif, row_steps, errors)
        if not verif:
            errors.append("traceability: %s has no verification" % cid)
        built = set(s for _, _, ss in its for s in ss)
        if K.closing_step and any(K.types[k].get("closing") for _, k, _ in its):
            built.add(K.closing_step)
        if its and built != set(row_steps):
            errors.append("traceability: %s: the «Step» column (%s) does not match the steps of the verification (%s)"
                          % (cid, " · ".join(row_steps), " · ".join(sorted(built, key=step_key))))
        if not state.startswith(K.states):
            errors.append("traceability: %s has an unknown evidence state: «%s»" % (cid, state))
        rows[cid], items[cid], states[cid] = row_steps, its, state
    return rows, items, states, excluded, no_ac


def main():
    global K
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project", default=".", help="project root (by default, the current folder)")
    ap.add_argument("--config", help="configuration (by default, <project>/sdd.config.json)")
    ap.add_argument("--step", action="append", default=[], help="require the evidence of the AC the step builds")
    ap.add_argument("--no-review", action="store_true", help="missing reviews are warnings")
    ap.add_argument("--graph", action="store_true", help="totals, critical path and size rule")
    ap.add_argument("--self-test", action="store_true", help="own mutations of the filter and the parsers")
    args = ap.parse_args(V.argv(sys.argv[1:]))
    if args.self_test:
        return self_test()
    try:
        K, cfg_warnings = load(args.project, args.config)
    except ConfigError as e:
        print("ERROR  config: %s" % e)
        print("Result: invalid configuration")
        return 2
    errors, warnings = [], list(cfg_warnings)

    reqs, acs = read_spec(errors, warnings)
    log_base = check_change_log(errors)
    req_acs = {}
    for cid, rid in acs.items():
        req_acs.setdefault(rid, []).append(cid)
    steps, fields = read_steps(errors)
    fs, ff = parse_deps(fields, errors)
    deps = dict((s, fs[s] + ff[s]) for s in steps)

    rows, items, states, excluded, no_ac = read_traceability(acs, steps, errors)

    for cid, rid in acs.items():
        if cid not in rows and cid not in excluded:
            errors.append("traceability: missing %s (%s, %s)" % (cid, rid, reqs[rid]))
        if cid in rows and cid in excluded:
            errors.append("traceability: %s has both a row and an exclusion" % cid)
        if cid in excluded and K.critical_prio and reqs[rid] == K.critical_prio:
            warnings.append("traceability: %s is %s and is excluded" % (cid, K.critical_prio))

    for step in sorted(steps, key=step_key):
        has = any(step in ps for ps in rows.values())
        if has and step in no_ac:
            errors.append("traceability: %s is in «%s», but has AC" % (step, K.sec_no_ac))
        if not has and step not in no_ac:
            errors.append("traceability: %s has no AC and is not in «%s»" % (step, K.sec_no_ac))

    for step, ds in deps.items():
        for d in ds:
            if d not in steps:
                errors.append("steps: %s depends on %s, which does not exist" % (step, d))
            elif d == step:
                errors.append("steps: %s depends on itself" % step)
    cycles = find_cycles(deps)
    for c in cycles:
        errors.append("steps: cycle %s" % c)
    anc = dict((s, ancestors(deps, s)) for s in steps)
    for step, v in fields.items():
        for p in expand_steps(v["parallel"], errors, "steps: %s «%s»" % (step, K.field["parallel"])):
            if p not in steps:
                errors.append("steps: %s is parallel with %s, which does not exist" % (step, p))
            elif p in anc[step] or step in anc.get(p, set()):
                errors.append("steps: %s claims to be parallel with %s, but there is a dependency between them"
                              % (step, p))

    cited_by = {}
    for step, v in fields.items():
        cited = satisfied_acs(v["satisfies"], req_acs)
        cited_by[step] = cited
        for cid in sorted(cited):
            if cid not in acs:
                errors.append("steps: %s cites %s, which does not exist" % (step, cid))
            elif cid in excluded:
                errors.append("steps: %s cites %s, which is excluded" % (step, cid))
            elif cid in rows and step not in rows[cid]:
                errors.append("steps: %s cites %s, but its row points to %s" % (step, cid, " · ".join(rows[cid])))
    for cid, row_steps in rows.items():
        for p in row_steps:
            if p != K.closing_step and p in cited_by and cid not in cited_by[p]:
                errors.append("steps: the row of %s assigns %s, but its «%s» does not cite it"
                              % (cid, p, K.field["satisfies"]))

    check_skills(steps, fields, errors, warnings)

    named = {}
    for kind, t in K.types.items():
        if t["mode"] == "classes":
            named[kind] = dict((s, set(t["_names"].findall(v[t["field"]]))) for s, v in fields.items())
    index = evidence_index()
    cites = {}
    for group, paths in index.items():
        cites.update(files_cites(paths, only_section=(group == "step_reports")))
    report_all = files_cites(index["step_reports"])  # to warn about a citation outside its section
    for f, ids in cites.items():
        for cid in sorted(ids - set(acs)):
            errors.append("evidence: %s cites %s, which does not exist" % (rel(f), cid))
    for f in index["step_reports"]:
        step = f.stem
        for cid in sorted(cites[f] & set(rows)):
            if step not in rows[cid]:
                warnings.append("evidence: the step report of %s cites %s, which is not of that step" % (step, cid))
    for kind, per_step in named.items():
        for step, names in per_step.items():
            own = set(cid for cid, its in items.items() if any(k == kind and step in ss for _, k, ss in its))
            for f in index[kind]:
                if f.stem in names:
                    for cid in sorted((cites[f] & set(rows)) - own):
                        warnings.append("evidence: %s (of %s) cites %s, which %s does not test with %s"
                                        % (f.name, step, cid, step, K.types[kind]["with"]))

    # Initial state with the steps integrated in status.md and the evidence already cited: it needs updating (warning)
    integrated = (integrated_steps(K.status.read_text(encoding="utf-8"))
                  if K.status is not None and K.status.is_file() else set())
    initial, following = K.states[0], " or ".join("«%s»" % e for e in K.states[1:])
    for cid in sorted(rows, key=lambda c: (acs.get(c, ""), c)):
        builders = [s for s in rows[cid] if s != K.closing_step]
        if not states[cid].startswith(initial) or not builders or not set(builders) <= integrated:
            continue
        cited = all(any(cid in cites.get(f, set()) for f in required_files(kind, s, index, named)[0])
                    for _, kind, ss in items[cid] for s in ss)
        if cited and following:
            warnings.append("traceability: %s is «%s», but its steps (%s) are integrated in %s and its evidence is "
                            "cited: %s?" % (cid, initial, " · ".join(builders), K.status.name, following))

    for step in args.step:
        if step not in steps:
            errors.append("--step: %s does not exist" % step)
            continue
        for cid in sorted(rows, key=lambda c: (acs.get(c, ""), c)):
            for label, kind, ss in items[cid]:
                if step not in ss:
                    continue
                files, where = required_files(kind, step, index, named)
                if not any(cid in cites.get(f, set()) for f in files):
                    msg = "%s: %s has no «%s» in %s" % (step, cid, label, where)
                    if K.types[kind]["mode"] == "report" and any(cid in report_all.get(f, set()) for f in files):
                        msg += " (the step report cites it, but outside «## %s»)" % K.sec_cases
                    (warnings if K.types[kind]["mode"] == "review" and args.no_review else errors).append(msg)
            if step == K.closing_step:
                demo = [label for label, k, _ in items[cid] if K.types[k].get("closing")]
                if demo and not any(cid in cites.get(f, set()) for f in index["walkthrough"]):
                    errors.append("%s: %s has no %s in %s" % (step, cid, demo[0], rel(K.walkthrough)))

    with_ev = sum(1 for c in rows if any(c in ids for ids in cites.values()))
    if log_base:
        print("Change log: compared with %s" % log_base)
    print("Spec: %d requirements, %d AC · table: %d rows, %d excluded · steps: %d · AC with cited evidence: %d"
          % (len(reqs), len(acs), len(rows), len(excluded), len(steps), with_ev))
    if args.graph:
        errors.extend(graph_or_warning(cycles, steps, fields, fs, ff, rows))
    for w in warnings:
        print("WARNING  " + w)
    for e in errors:
        print("ERROR  " + e)
    print("Result: %s" % ("no errors" if not errors else "%d errors" % len(errors)))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
