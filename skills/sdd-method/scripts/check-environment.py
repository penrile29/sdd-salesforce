#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Environment check of an sdd-salesforce project (Plan stage).

Looks for the skills the project needs (the method's, the base ones and those of its
areas, per the skills-by-area.json catalog) in every layer Claude Code can load them
from, classifies each one as present, missing or shadowed, and compares the tools and
the org API with the minimums the skills themselves declare (metadata.cliTools and
metadata.minApiVersion).

Standard library only (Python 3.9), no network.

Org safety: the script runs no sf command against an org except with --query-org, and
then only `sf org display --target-org <org_alias> --json`, with the org_alias of
sdd.config.json. Without that option, the org API comes from --api-org or is left as
not checked.

Usage:
  python3 check-environment.py                                  # project = cwd
  python3 check-environment.py --project . --areas agentforce,flow --api-org 66.0
  python3 check-environment.py --quick                         # bootstrap: warns, does not block
  python3 check-environment.py --self-test
  python3 check-environment.py --validate-catalog <skills/ folder of sf-skills>

Exit code: 1 if there is any error (a needed skill missing or shadowed, a tool missing
or below its minimum, the org API below the minimum or not checked); 0 otherwise; 2 if
the call is wrong (also a malformed catalog). --quick exits with 0 even with gaps, and
there an unchecked API is only a warning.

A skill is shadowed when it is in two layers and any file in its folder differs, not
only its SKILL.md.

The result describes the file system. The source of truth is the skill list of the
Claude session: check it against that list.
"""

import argparse
import datetime as _dt
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sdd_vocab as V  # noqa: E402

SOURCE_OF_TRUTH_NOTE = ('This inventory comes from a script that reads the file system. The source of truth is the '
                        'skill list of the Claude session: check it against that list.')
CATALOG_NAME = 'skills-by-area.json'

# Variables that keep the CLIs off the network when they are asked for their version.
OFFLINE_ENV = {
    'SF_AUTOUPDATE_DISABLE': 'true',
    'SFDX_AUTOUPDATE_DISABLE': 'true',
    'SF_DISABLE_TELEMETRY': 'true',
    'SFDX_DISABLE_TELEMETRY': 'true',
    'SF_SKIP_NEW_VERSION_CHECK': 'true',
    'SFDX_SKIP_NEW_VERSION_CHECK': 'true',
    'NO_UPDATE_NOTIFIER': '1',
    'npm_config_update_notifier': 'false',
}

# Tool names come from the frontmatter of the skills: only simple names are run,
# looked up on the PATH, and only with --version / -version.
_RE_TOOL_NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._+-]*$')
_RE_ALIAS = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._@+-]*$')


class UsageError(Exception):
    """Wrong call (exit code 2)."""


# ---------------------------------------------------------------------------
# Frontmatter: a YAML subset that is enough for SKILL.md files (no pyyaml).
# Covers maps and lists by indentation, lists of maps («- tool: [...]»), inline
# lists and maps, quoted or unquoted scalars (also over several lines), «|» and
# «>» blocks, and comments.
# ---------------------------------------------------------------------------

_RE_KEY = re.compile(
    r'''^(?P<k>"(?:[^"\\]|\\.)*"|'(?:[^']|'')*'|[A-Za-z0-9_$][^:#]*?)\s*:(?:\s+(?P<v>.*))?$''')


def _strip_comment(s):
    quote = None
    for i, ch in enumerate(s):
        if quote:
            if ch == quote:
                quote = None
        elif ch in '"\'':
            quote = ch
        elif ch == '#' and (i == 0 or s[i - 1] in ' \t'):
            return s[:i]
    return s


def _scalar(t):
    t = t.strip()
    if len(t) >= 2 and t[0] == '"' and t[-1] == '"':
        try:
            return json.loads(t)
        except ValueError:
            return t[1:-1].replace('\\"', '"').replace('\\\\', '\\')
    if len(t) >= 2 and t[0] == "'" and t[-1] == "'":
        return t[1:-1].replace("''", "'")
    return t


def _skip_blanks(t, i):
    while i < len(t) and t[i] in ' \t':
        i += 1
    return i


def _flow_scalar(t, i, stops):
    i = _skip_blanks(t, i)
    if i < len(t) and t[i] in '"\'':
        q = t[i]
        j = i + 1
        buf = []
        while j < len(t):
            ch = t[j]
            if q == '"' and ch == '\\' and j + 1 < len(t):
                buf.append(t[j:j + 2])
                j += 2
                continue
            if ch == q:
                if q == "'" and j + 1 < len(t) and t[j + 1] == "'":
                    buf.append("''")
                    j += 2
                    continue
                return _scalar(q + ''.join(buf) + q), j + 1
            buf.append(ch)
            j += 1
        raise ValueError('unclosed quote')
    j = i
    while j < len(t) and t[j] not in stops:
        j += 1
    return t[i:j].strip(), j


def _flow(t, i=0):
    i = _skip_blanks(t, i)
    if i >= len(t):
        raise ValueError('incomplete flow')
    if t[i] == '[':
        items = []
        i += 1
        while True:
            i = _skip_blanks(t, i)
            if i >= len(t):
                raise ValueError('missing ]')
            if t[i] == ']':
                return items, i + 1
            before = i
            v, i = _flow(t, i)
            items.append(v)
            i = _skip_blanks(t, i)
            if i < len(t) and t[i] == ',':
                i += 1
            elif i == before or (i < len(t) and t[i] != ']'):
                raise ValueError('malformed list')
    if t[i] == '{':
        mapping = {}
        i += 1
        while True:
            i = _skip_blanks(t, i)
            if i >= len(t):
                raise ValueError('missing }')
            if t[i] == '}':
                return mapping, i + 1
            before = i
            k, i = _flow_scalar(t, i, ':,}')
            i = _skip_blanks(t, i)
            v = None
            if i < len(t) and t[i] == ':':
                v, i = _flow(t, i + 1)
            mapping[str(k)] = v
            i = _skip_blanks(t, i)
            if i < len(t) and t[i] == ',':
                i += 1
            elif i == before or (i < len(t) and t[i] != '}'):
                raise ValueError('malformed map')
    return _flow_scalar(t, i, ',]}')


def _scalar_or_flow(text):
    t = text.strip()
    if not t:
        return ''
    if t[0] in '[{':
        try:
            v, _ = _flow(t, 0)
            return v
        except (ValueError, IndexError):
            raise ValueError('unclosed list or map: %s' % t[:40])
    return _scalar(t)


def _is_item(t):
    return t == '-' or t.startswith('- ')


def _is_map_entry(t):
    if not t or t[0] in '[{':
        return False
    if t[0] in '"\'':
        try:
            _, j = _flow_scalar(t, 0, '')
        except ValueError:
            return False
        rest = t[j:].lstrip()
        return rest == ':' or rest.startswith(': ')
    return bool(_RE_KEY.match(t))


class _Yaml(object):
    def __init__(self, lines):
        self.l = [x.replace('\t', '    ').rstrip() for x in lines]
        self.i = 0

    @staticmethod
    def _indent(s):
        return len(s) - len(s.lstrip(' '))

    def _skip(self):
        while self.i < len(self.l):
            t = self.l[self.i].strip()
            if t == '' or t.startswith('#'):
                self.i += 1
            else:
                return

    def block(self, minimum):
        self._skip()
        if self.i >= len(self.l):
            return None
        s = self.l[self.i]
        n = self._indent(s)
        if n < minimum:
            return None
        if _is_item(s.strip()):
            return self.sequence(n)
        return self.mapping(n)

    def mapping(self, n):
        res = {}
        while True:
            self._skip()
            if self.i >= len(self.l):
                break
            s = self.l[self.i]
            k = self._indent(s)
            t = s.strip()
            if k < n or (k == n and _is_item(t)):
                break
            if k > n:
                self.i += 1  # orphan line: ignored
                continue
            m = _RE_KEY.match(t)
            self.i += 1
            if not m:
                continue
            res[str(_scalar(m.group('k')))] = self.value(m.group('v') or '', n)
        return res

    def sequence(self, n):
        res = []
        while True:
            self._skip()
            if self.i >= len(self.l):
                break
            s = self.l[self.i]
            k = self._indent(s)
            t = s.strip()
            if k != n or not _is_item(t):
                break
            cont = t[1:].lstrip()
            if cont == '':
                self.i += 1
                res.append(self.block(n + 1))
                continue
            offset = k + (len(t) - len(cont))
            if _is_map_entry(cont):
                self.l[self.i] = ' ' * offset + cont
                res.append(self.mapping(offset))
            elif _is_item(cont):
                self.l[self.i] = ' ' * offset + cont
                res.append(self.sequence(offset))
            else:
                self.i += 1
                res.append(self.value(cont, n))
        return res

    def value(self, rest, n):
        rest = _strip_comment(rest).strip()
        if re.match(r'^[|>][-+0-9]*$', rest):
            return self.block_scalar(n, rest[0] == '>')
        if rest == '':
            self._skip()
            if self.i < len(self.l):
                s = self.l[self.i]
                k = self._indent(s)
                if _is_item(s.strip()) and k >= n:
                    return self.sequence(k)
                if k > n:
                    return self.mapping(k)
            return None
        parts = [rest]
        while True:  # scalar or flow that continues on more indented lines
            j = self.i
            while j < len(self.l) and self.l[j].strip() == '':
                j += 1
            if j >= len(self.l) or self._indent(self.l[j]) <= n:
                break
            parts.append(self.l[j].strip())
            self.i = j + 1
        return _scalar_or_flow(' '.join(parts))

    def block_scalar(self, n, folded):
        lines = []
        indent = None
        while self.i < len(self.l):
            s = self.l[self.i]
            if s.strip() == '':
                lines.append('')
                self.i += 1
                continue
            k = self._indent(s)
            if k <= n:
                break
            if indent is None:
                indent = k
            lines.append(s[min(indent, k):])
            self.i += 1
        while lines and lines[-1] == '':
            lines.pop()
        return (' ' if folded else '\n').join(lines)


def _header(text):
    """Only the frontmatter block (with its two «---»), or ''."""
    lines = text.lstrip('\ufeff').splitlines()
    if not lines or lines[0].strip() != '---':
        return ''
    for k in range(1, len(lines)):
        if lines[k].strip() in ('---', '...'):
            return '\n'.join(lines[:k + 1])
    return ''


def read_frontmatter(text, problems=None):
    """Frontmatter as a dictionary. If it cannot be read, {} and the reason in problems (if given)."""
    head = _header(text)
    if not head:
        return {}
    body = head.splitlines()[1:-1]
    try:
        r = _Yaml(body).block(0)
    except Exception as e:  # an unreadable frontmatter must not bring the inventory down
        if problems is not None:
            problems.append(str(e) or e.__class__.__name__)
        return {}
    return r if isinstance(r, dict) else {}


def _as_list(x):
    if x is None:
        return []
    if isinstance(x, list):
        return [str(e).strip() for e in x if e is not None and not isinstance(e, (dict, list)) and str(e).strip()]
    if isinstance(x, (dict,)):
        return []
    s = str(x).strip()
    return [s] if s else []


def skill_data(fm):
    """The frontmatter fields the check uses."""
    md = fm.get('metadata') if isinstance(fm.get('metadata'), dict) else {}
    tools = []
    cli = md.get('cliTools')
    for item in cli if isinstance(cli, list) else []:
        if isinstance(item, dict):
            rng = str(item.get('semver') or '*').strip() or '*'
            for t in _as_list(item.get('tool')):
                tools.append((t, rng))
        elif isinstance(item, str) and item.strip():
            tools.append((item.strip(), '*'))
    version = md.get('version') if md.get('version') not in (None, '') else fm.get('version')
    api = md.get('minApiVersion')
    return {
        'name': str(fm.get('name') or '').strip(),
        'version': str(version).strip() if version not in (None, '') else None,
        'domains': _as_list(md.get('domains')),
        'cliTools': tools,
        'minApiVersion': str(api).strip() if api not in (None, '') else None,
        'relatedSkills': _as_list(md.get('relatedSkills')),
    }


# ---------------------------------------------------------------------------
# Versions and semver ranges
# ---------------------------------------------------------------------------

_RE_VERSION = re.compile(r'(?<![\w.])v?(\d+\.\d+(?:\.\d+)?)')


def _vtuple(v):
    if v is None:
        return None
    nums = re.findall(r'\d+', str(v))
    return tuple(int(x) for x in nums[:4]) if nums else None


def _cmp(a, b):
    n = max(len(a), len(b))
    a = tuple(a) + (0,) * (n - len(a))
    b = tuple(b) + (0,) * (n - len(b))
    return (a > b) - (a < b)


def _extract_version(text, allow_integer=False):
    for line in (text or '').splitlines():
        m = _RE_VERSION.search(line)
        if m:
            return m.group(1)
    if allow_integer:  # «awk version 20200816»; never a bare number from an error message
        m = re.search(r'\bversion\s+v?(\d+)\b', text or '', re.I)
        if m:
            return m.group(1)
    return None


# Tools that do not answer to --version.
_VERSION_ARGS = {'openssl': (['version'],)}


_RE_COMPARATOR = re.compile(r'(>=|<=|>|<|==|=|\^|~)?\s*v?(\d+(?:\.\d+)*)')


def _satisfies(version, rng):
    """True / False, or None if the range is not understood."""
    rng = (rng or '').strip()
    if rng in ('', '*', 'x', 'X', 'any', 'latest'):
        return True
    v = _vtuple(version)
    if v is None:
        return None
    understood = False
    for alternative in rng.split('||'):
        comps = _RE_COMPARATOR.findall(alternative)
        if not comps:
            continue
        understood = True
        good = True
        for op, ver in comps:
            r = _vtuple(ver)
            c = _cmp(v, r)
            if op == '>=':
                good = good and c >= 0
            elif op in ('', '=', '=='):  # exact version; «3.10» matches 3.10.x
                good = good and _cmp(v[:len(r)], r) == 0
            elif op == '>':
                good = good and c > 0
            elif op == '<=':
                good = good and c <= 0
            elif op == '<':
                good = good and c < 0
            elif op == '^':
                top = (r[0] + 1,) if r[0] > 0 else (0, (r[1] if len(r) > 1 else 0) + 1)
                good = good and c >= 0 and _cmp(v, top) < 0
            elif op == '~':
                top = (r[0], (r[1] if len(r) > 1 else 0) + 1)
                good = good and c >= 0 and _cmp(v, top) < 0
        if good:
            return True
    return False if understood else None


def _bound(rng):
    bounds = [_vtuple(ver) for op, ver in _RE_COMPARATOR.findall(rng or '') if op in ('>=', '>', '=', '==', '^', '~', '')]
    bounds = [b for b in bounds if b]
    return max(bounds) if bounds else (0,)


def _strictest_range(ranges):
    real = [r for r in ranges if r and r.strip() not in ('*', '')]
    if not real:
        return '*'
    best = real[0]
    for r in real[1:]:
        if _cmp(_bound(r), _bound(best)) > 0:
            best = r
    return best


# ---------------------------------------------------------------------------
# External commands (all of them go through here; the self-tests check the log)
# ---------------------------------------------------------------------------

COMMANDS_RUN = []
_TOOL_CACHE = {}


def _run(cmd, timeout=60, extra_env=None):
    COMMANDS_RUN.append(list(cmd))
    env = dict(os.environ)
    env.update(OFFLINE_ENV)
    env.update(extra_env or {})
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
                           timeout=timeout, env=env)
        return p.returncode, p.stdout.decode('utf-8', 'replace'), p.stderr.decode('utf-8', 'replace')
    except FileNotFoundError:
        return None, '', 'not found'
    except subprocess.TimeoutExpired:
        return None, '', 'no answer in %d s' % timeout
    except OSError as e:
        return None, '', str(e)


def tool_version(name):
    """(version | '?' | None, path, note). None = not on the PATH."""
    key = (name, os.environ.get('PATH', ''))
    if key in _TOOL_CACHE:
        return _TOOL_CACHE[key]
    path = shutil.which(name)
    if not path:
        res = (None, None, 'not on the PATH')
    else:
        first = ''
        res = None
        for args in _VERSION_ARGS.get(name, (['--version'], ['-version'])):
            rc, out, err = _run([path] + list(args))
            v = _extract_version(out, rc == 0) or _extract_version(err, rc == 0)
            if v:
                res = (v, path, '')
                break
            first = first or next((x.strip() for x in (out + '\n' + err).splitlines() if x.strip()), '')
        if res is None:
            note = 'could not read the version of %s' % path
            if first:
                note += ' (it says: «%s»)' % (first[:120] + ('…' if len(first) > 120 else ''))
            res = ('?', path, note)
    _TOOL_CACHE[key] = res
    return res


def my_domain_of(instance_url):
    """The My Domain name of an org («acme-dev-ed» for https://acme-dev-ed.develop.my.salesforce.com), or None. A
    sandbox keeps its suffix («acme--uat»): it is another org than production."""
    m = re.match(r'https?://([^/:]+)', str(instance_url or ''))
    if not m or '.' not in m.group(1):
        return None
    return m.group(1).lower().split('.', 1)[0] or None


def query_org_api(alias, details=None):
    """Org API with `sf org display --target-org <alias> --json`. Returns (version | None, note).

    The output of that command includes the org access token: it is neither printed nor saved;
    only result.apiVersion and the My Domain name of result.instanceUrl (into details['my_domain']) are extracted.
    """
    if not alias:
        return None, 'org_alias is missing from sdd.config.json'
    if not _RE_ALIAS.match(alias):
        return None, 'org_alias has invalid characters: %r' % alias
    sf = shutil.which('sf')
    if not sf:
        return None, 'sf is not on the PATH'
    extra = {} if 'SFDX_DISABLE_DNS_CHECK' in os.environ else {'SFDX_DISABLE_DNS_CHECK': 'true'}
    _, out, _ = _run([sf, 'org', 'display', '--target-org', alias, '--json'], timeout=180, extra_env=extra)
    try:
        d = json.loads(out)
    except ValueError:
        return None, 'the output of sf org display is not JSON'
    if d.get('status') != 0:
        msg = str(d.get('message') or d.get('name') or 'error with no message')
        return None, 'sf org display --target-org %s failed: %s' % (alias, msg[:200])
    v = (d.get('result') or {}).get('apiVersion')
    if details is not None:
        details['my_domain'] = my_domain_of((d.get('result') or {}).get('instanceUrl'))
    return (str(v), '') if v else (None, 'sf org display returned no apiVersion')


def playwright_cache(home, explicit_home):
    """Folder of Playwright's browsers: PLAYWRIGHT_BROWSERS_PATH (not in tests) or the default one of the system."""
    if not explicit_home and os.environ.get('PLAYWRIGHT_BROWSERS_PATH') not in (None, '', '0'):
        return os.path.expanduser(os.environ['PLAYWRIGHT_BROWSERS_PATH'])
    if sys.platform == 'darwin':
        return os.path.join(home, 'Library', 'Caches', 'ms-playwright')
    if sys.platform.startswith('win'):
        return os.path.join(home, 'AppData', 'Local', 'ms-playwright')
    return os.path.join(home, '.cache', 'ms-playwright')


def browser_gaps(project, home, browser, explicit_home=False):
    """(errors, warnings, inventory entry) of the browser requirement (rule M-12): the project's .mcp.json with the
    pinned Playwright MCP and the Chromium revision it needs."""
    errors, warnings = [], []
    package = '%s@%s' % (browser.get('package') or '@playwright/mcp', browser.get('version') or 'latest')
    revision = str(browser.get('chromium_revision') or '')
    install = 'npx -y %s install-browser chromium --no-shell' % package
    entry = OrderedDict([('mcp', package), ('mcp_json', 'missing'), ('chromium_revision', revision or None),
                         ('chromium', 'not_checked')])
    path = os.path.join(project, '.mcp.json')
    server = None
    try:
        data = _read_json(path)
        server = ((data.get('mcpServers') or {}) if isinstance(data, dict) else {}).get('playwright')
    except FileNotFoundError:
        pass
    except (OSError, ValueError) as e:
        errors.append('Browser: .mcp.json cannot be read (%s).' % e)
    if server is None:
        if not errors:
            errors.append('Browser: the project has no .mcp.json with the «playwright» server (rule M-12). Run '
                          'sdd-bootstrap with --add-missing, which creates it with %s, or set environment.browser to '
                          'false in sdd.config.json if this project does not test in the browser.' % package)
    else:
        args = server.get('args') if isinstance(server, dict) else None
        args = args if isinstance(args, list) else []
        if package in args:
            entry['mcp_json'] = 'present'
        else:
            entry['mcp_json'] = 'other_version'
            warnings.append('Browser: the «playwright» server of .mcp.json is not the pinned %s (%s): its Chromium '
                            'revision may not be %s.' % (package, ' '.join(str(a) for a in args[:3]) or '?',
                                                         revision or '?'))
    if revision:
        cache = playwright_cache(home, explicit_home)
        if os.path.isdir(os.path.join(cache, 'chromium-' + revision)):
            entry['chromium'] = 'present'
        else:
            entry['chromium'] = 'missing'
            errors.append('Browser: Playwright\'s Chromium %s is not in %s. Install it, with the user\'s OK (it '
                          'downloads from Playwright\'s CDN): %s' % (revision, cache, install))
    return errors, warnings, entry


# ---------------------------------------------------------------------------
# Skill layers
# ---------------------------------------------------------------------------

def _norm(s):
    return re.sub(r'[^a-z0-9]', '', str(s).lower())


def _folder_digest(d):
    """sha256 of every file in a skill folder: relative paths and content, without hidden files or caches."""
    h = hashlib.sha256()
    for root, dirs, files in os.walk(d):
        dirs[:] = sorted(x for x in dirs if not x.startswith('.') and x != '__pycache__')
        for f in sorted(files):
            if f.startswith('.') or f.endswith('.pyc'):
                continue
            path = os.path.join(root, f)
            try:
                with open(path, 'rb') as fh:
                    data = fh.read()
            except OSError:
                data = b''
            rel = os.path.relpath(path, d).replace(os.sep, '/')
            h.update(rel.encode('utf-8') + b'\0' + hashlib.sha256(data).digest())
    return h.hexdigest()


class SkillCopy(object):
    """One copy of a skill (a folder with a SKILL.md) in a layer."""

    def __init__(self, name, layer, kind, order, path, content, plugin=None, digest=None):
        self.name = name
        self.layer = layer        # 'project' | 'parent' | 'user' | 'plugin:<name>'
        self.kind = kind          # 'project' | 'parent' | 'user' | 'plugin'
        self.order = order        # lower = loads first (user 0, project 1, parent 2+)
        self.path = path
        self.plugin = plugin
        self.hash = digest or hashlib.sha256(content).hexdigest()
        self._head = _header(content.decode('utf-8', 'replace'))
        self._data = None
        self.fm_problem = None

    @property
    def data(self):
        if self._data is None:
            problems = []
            self._data = skill_data(read_frontmatter(self._head, problems))
            self.fm_problem = problems[0] if problems else None
        return self._data

    @property
    def version(self):
        return self.data['version']


def _list_skills(skills_dir, layer, kind, order, warnings, plugin=None):
    res = []
    try:
        entries = sorted(os.listdir(skills_dir))
    except OSError:
        return res
    for name in entries:
        if name.startswith('.'):
            continue
        d = os.path.join(skills_dir, name)
        if os.path.islink(d) and not os.path.exists(d):
            warnings.append('Broken symlink in the %s layer: %s -> %s.' % (layer, d, os.readlink(d)))
            continue
        f = os.path.join(d, 'SKILL.md')
        if not os.path.isfile(f):
            continue
        try:
            with open(f, 'rb') as fh:
                content = fh.read()
        except OSError as e:
            warnings.append('Could not read %s: %s.' % (f, e))
            continue
        res.append(SkillCopy(name, layer, kind, order, f, content, plugin, digest=_folder_digest(d)))
    return res


def _list_agents(agents_dir):
    res = []
    try:
        entries = sorted(os.listdir(agents_dir))
    except OSError:
        return res
    for f in entries:
        if not f.endswith('.md'):
            continue
        path = os.path.join(agents_dir, f)
        name = f[:-3]
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as fh:
                name = str(read_frontmatter(fh.read()).get('name') or name).strip()
        except OSError:
            pass
        res.append((name, path))
    return res


def _parents(project, home):
    """Folders above the project, from the nearest to the farthest, up to $HOME exclusive."""
    res = []
    home_real = os.path.realpath(home)
    previous, current = project, os.path.dirname(project)
    while current and current != previous:
        if os.path.realpath(current) == home_real:
            break
        res.append(current)
        previous, current = current, os.path.dirname(current)
    return res


def _enabled_plugins(home, project, warnings):
    res = {}
    for f in (os.path.join(home, '.claude', 'settings.json'),
              os.path.join(project, '.claude', 'settings.json'),
              os.path.join(project, '.claude', 'settings.local.json')):
        if not os.path.isfile(f):
            continue
        try:
            with open(f, encoding='utf-8') as fh:
                d = json.load(fh)
        except (OSError, ValueError):
            warnings.append('Could not read %s: its enabledPlugins are ignored.' % f)
            continue
        ep = d.get('enabledPlugins') if isinstance(d, dict) else None
        if isinstance(ep, dict):
            for k, v in ep.items():
                if isinstance(v, bool):
                    res[k] = v
    return res


class Environment(object):
    """Every copy of skills and agents visible to a project."""

    def __init__(self, project, home, standalone_layers=True, own_plugin=False):
        self.project = project
        self.home = home
        self.warnings = []
        self.layers = []      # (label, folder, number of skills)
        self.copies = {}      # bare name -> [SkillCopy]
        self.plugins = OrderedDict()  # name -> info
        self.agents = {}      # name -> [(source, path)]
        self.plugins_note = ''
        if standalone_layers:
            self._load_standalone()
        self._load_plugins()
        self.own = self._load_own_plugin() if own_plugin else None

    def short(self, path):
        if not path:
            return ''
        h = self.home.rstrip(os.sep)
        return '~' + path[len(h):] if path == h or path.startswith(h + os.sep) else path

    def _layer(self, folder, label, kind, order, seen):
        if not os.path.isdir(folder):
            return
        real = os.path.realpath(folder)
        if real in seen:
            return
        seen.add(real)
        copies = _list_skills(folder, label, kind, order, self.warnings)
        for c in copies:
            self.copies.setdefault(c.name, []).append(c)
        self.layers.append((label, folder, len(copies)))

    def _load_standalone(self):
        seen = set()
        # The user layer is registered first: if the project were $HOME, its skills are the user ones.
        self._layer(os.path.join(self.home, '.claude', 'skills'), 'user', 'user', 0, seen)
        self._layer(os.path.join(self.project, '.claude', 'skills'), 'project', 'project', 1, seen)
        for k, d in enumerate(_parents(self.project, self.home)):
            self._layer(os.path.join(d, '.claude', 'skills'), 'parent', 'parent', 2 + k, seen)
        for label, d in (('project', os.path.join(self.project, '.claude', 'agents')),
                         ('user', os.path.join(self.home, '.claude', 'agents'))):
            for name, path in _list_agents(d):
                self.agents.setdefault(name, []).append((label, path))

    def _load_plugins(self):
        f = os.path.join(self.home, '.claude', 'plugins', 'installed_plugins.json')
        if not os.path.isfile(f):
            self.plugins_note = 'no ~/.claude/plugins/installed_plugins.json'
            return
        try:
            with open(f, encoding='utf-8') as fh:
                data = json.load(fh)
        except (OSError, ValueError) as e:
            self.warnings.append('Could not read %s (%s): plugins are not visible.' % (f, e))
            return
        registry = data.get('plugins') if isinstance(data, dict) and isinstance(data.get('plugins'), dict) else {}
        enabled = _enabled_plugins(self.home, self.project, self.warnings)
        project_real = os.path.realpath(self.project)
        for key in sorted(registry):
            entries = registry[key]
            if isinstance(entries, dict):
                entries = [entries]
            if not isinstance(entries, list):
                continue
            name = key.split('@', 1)[0]
            chosen = None
            for e in entries:
                if not isinstance(e, dict):
                    continue
                if e.get('scope') in ('project', 'local'):
                    pp = e.get('projectPath')
                    if not pp:
                        continue
                    ppr = os.path.realpath(pp).rstrip(os.sep)
                    if project_real == ppr or project_real.startswith(ppr + os.sep):
                        chosen = e  # the project install is the most specific one
                        break
                elif chosen is None:
                    chosen = e
            if chosen is None:
                continue
            path = str(chosen.get('installPath') or '')
            if not os.path.isdir(path):
                self.warnings.append('Plugin %s is in installed_plugins.json but its folder does not exist: %s.'
                                     % (key, path))
                continue
            if name in self.plugins:
                self.warnings.append('Plugin %s is installed from two marketplaces (%s and %s); the first one is used.'
                                     % (name, self.plugins[name]['key'], key))
                continue
            info = {'key': key, 'version': str(chosen.get('version') or ''), 'path': path,
                    'scope': str(chosen.get('scope') or 'user'), 'enabled': enabled.get(key) is not False,
                    'skills': 0, 'agents': []}
            self.plugins[name] = info
            label = 'plugin:' + name
            copies = _list_skills(os.path.join(path, 'skills'), label, 'plugin', 50, self.warnings, name)
            for c in copies:
                self.copies.setdefault(c.name, []).append(c)
            info['skills'] = len(copies)
            for an, ap in _list_agents(os.path.join(path, 'agents')):
                info['agents'].append(an)
                self.agents.setdefault(an, []).append((label, ap))

    def _load_own_plugin(self):
        """The plugin this script runs from (skills/<skill>/scripts/): it is the one the session loads, also with
        --plugin-dir, even if it is not in installed_plugins.json. Returns (name, version, root) or None."""
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        manifest = os.path.join(root, '.claude-plugin', 'plugin.json')
        try:
            with open(manifest, encoding='utf-8') as fh:
                m = json.load(fh)
        except (OSError, ValueError):
            return None
        name, version = str(m.get('name') or ''), str(m.get('version') or '')
        if not name:
            return None
        previous = self.plugins.get(name)
        if previous and os.path.realpath(previous['path']) == os.path.realpath(root):
            return name, version, root
        if previous:
            self.warnings.append('This session uses plugin %s from %s (%s), not the one installed in %s (%s).'
                                 % (name, self.short(root), version or 'no version', self.short(previous['path']),
                                    previous['version'] or 'no version'))
            for copies in self.copies.values():
                copies[:] = [c for c in copies if not (c.kind == 'plugin' and c.plugin == name)]
        label = 'plugin:' + name
        copies = _list_skills(os.path.join(root, 'skills'), label, 'plugin', 50, self.warnings, name)
        for c in copies:
            self.copies.setdefault(c.name, []).append(c)
        self.plugins[name] = {'key': name + ' (this session)', 'version': version, 'path': root,
                              'scope': 'session', 'enabled': True, 'skills': len(copies), 'agents': []}
        return name, version, root

    def plugin_ok(self, name):
        info = self.plugins.get(name)
        return info is not None and info['enabled']

    def domain_index(self):
        idx = {}
        for name, copies in self.copies.items():
            for c in copies:
                if c.kind == 'plugin' and not self.plugin_ok(c.plugin):
                    continue
                for d in c.data['domains']:
                    e = idx.setdefault(_norm(d), {'domain': d, 'skills': set()})
                    e['skills'].add(name)
        return idx

    def _where(self, copies):
        return ', '.join('%s (%s)' % (c.layer, self.short(c.path)) for c in copies)

    def resolve(self, name, plugin=None, strict=False):
        """State of a needed skill.

        plugin + strict: it only counts if it comes from that plugin («plugin:skill» in the catalog).
        plugin without strict (method skills): that plugin or a standalone copy; other plugins do not count.
        no plugin: any layer.
        """
        r = {'name': name, 'state': 'missing', 'layer': None, 'path': None, 'version': None, 'copy': None,
             'reason': '', 'missing_plugin': None, 'warnings': [], 'shadowed': None, 'identical': []}
        everything = self.copies.get(name, [])
        standalone = sorted([c for c in everything if c.kind != 'plugin'], key=lambda c: c.order)
        in_plugins = sorted([c for c in everything if c.kind == 'plugin' and self.plugin_ok(c.plugin)],
                            key=lambda c: c.plugin)
        disabled = [c for c in everything if c.kind == 'plugin' and not self.plugin_ok(c.plugin)]

        def settle(c, state='present'):
            r.update(state=state, layer=c.layer, path=c.path, version=c.version, copy=c)

        if plugin:
            own = next((c for c in in_plugins if c.plugin == plugin), None)
            others = [c for c in in_plugins if c.plugin != plugin]
            if own:
                settle(own)
                if standalone:
                    r['warnings'].append(
                        '%s duplicated: it comes from plugin %s and there is also a standalone copy in %s. The bare '
                        'name invokes the standalone copy; the plugin one is %s:%s.'
                        % (name, plugin, self._where(standalone), plugin, name))
                if others:
                    r['warnings'].append(
                        'There is another skill called %s in %s: with both plugins enabled, invoke the method one as '
                        '%s:%s.' % (name, ', '.join('plugin ' + c.plugin for c in others), plugin, name))
                return r
            info = self.plugins.get(plugin)
            if info is None:
                reason = 'plugin %s is not installed' % plugin
                r['missing_plugin'] = plugin
            elif not info['enabled']:
                reason = 'plugin %s is installed but disabled in enabledPlugins' % plugin
                r['missing_plugin'] = plugin
            else:
                reason = 'plugin %s %s does not include this skill' % (plugin, info['version'])
            if strict or not standalone:
                if standalone:
                    reason += '; there is a standalone copy in %s, which does not replace the plugin' % (
                        self._where(standalone))
                if others:
                    reason += '; %s is a different skill' % ', '.join('%s:%s' % (c.plugin, name) for c in others)
                r['reason'] = reason
                return r
            r['missing_plugin'] = None
            r['warnings'].append('%s does not come from plugin %s (%s): the standalone copy is used.'
                                 % (name, plugin, reason))
            in_plugins = []  # for the method, other plugins do not count

        if standalone:
            winner = standalone[0]
            different = [c for c in standalone if c.hash != winner.hash]
            if not different:
                settle(winner)
                r['identical'] = [c.layer for c in standalone[1:]]
            else:
                settle(winner, 'shadowed')
                if winner.kind == 'user':
                    loads = ('the user copy loads (verified in this workspace: the personal one wins over the project '
                             'one)')
                else:
                    loads = 'the %s copy probably loads, the closest to the project' % winner.layer
                vw = _vtuple(winner.version)
                vs = [_vtuple(c.version) for c in different]
                if vw is None or any(v is None for v in vs):
                    verdict = 'Cannot tell which one is newer: some copy does not declare metadata.version.'
                elif any(_cmp(vw, v) < 0 for v in vs):
                    verdict = 'The one that loads is older than another copy.'
                elif all(_cmp(vw, v) > 0 for v in vs):
                    verdict = 'The one that loads is the newest; the other copies are redundant and confusing.'
                else:
                    verdict = 'Same version with different content: cannot tell which one is up to date.'
                others = '; '.join('%s %s (%s)' % (c.layer, c.version or 'no version', self.short(c.path))
                                   for c in different)
                r['shadowed'] = {'loads': loads, 'verdict': verdict, 'others': others}
                r['reason'] = '%s: %s (%s); other copies: %s. %s' % (
                    loads, winner.version or 'no version', self.short(winner.path), others, verdict)
            if in_plugins:
                r['warnings'].append(
                    '%s duplicated: it is standalone in %s and in %s. The bare name invokes the standalone copy; the '
                    'plugin one goes with its namespace.' % (name, self._where(standalone[:1]),
                                                              ', '.join('plugin ' + c.plugin for c in in_plugins)))
            return r

        if in_plugins:
            settle(in_plugins[0])
            if len(in_plugins) > 1:
                r['warnings'].append('%s duplicated in several plugins (%s): invoke it with its namespace.'
                                     % (name, ', '.join(c.plugin for c in in_plugins)))
            return r

        r['reason'] = 'not in any layer (project, parents, user or enabled plugins)'
        if disabled:
            r['reason'] += '; only in %s, disabled' % ', '.join('plugin ' + c.plugin for c in disabled)
        return r


# ---------------------------------------------------------------------------
# Check
# ---------------------------------------------------------------------------

def _read_json(path):
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


def _default_catalog():
    here = os.path.dirname(os.path.abspath(__file__))
    for c in (os.path.join(here, CATALOG_NAME), os.path.join(here, '..', 'assets', CATALOG_NAME)):
        if os.path.isfile(c):
            return os.path.normpath(c)
    return None


def _python_hint(rng):
    for minor in range(15, 9, -1):
        exe = 'python3.%d' % minor
        if shutil.which(exe):
            v = tool_version(exe)[0]
            if v and v != '?' and _satisfies(v, rng):
                return (' %s (%s) is on the PATH: the scripts of those skills can run with it; do not change the '
                        'system python3.' % (exe, v))
    return ''


CONFIG_KEYS = {'project', 'org_alias', 'areas', 'environment', 'traceability', 'method', 'dev_hub'}
ENVIRONMENT_KEYS = {'inventory', 'extra_skills', 'excluded_skills', 'browser'}


def _check_catalog_shape(catalog, path):
    """Minimum structure of the catalog; if it is not there, UsageError (exit code 2) with what fails."""
    def bad(what):
        raise UsageError('The catalog %s is malformed: %s.' % (path, what))
    if not isinstance(catalog, dict):
        bad('it is not a JSON object')
    if not isinstance(catalog.get('method', []), list):
        bad('«method» must be a list')
    base = catalog.get('base', {})
    if not isinstance(base, dict):
        bad('«base» must be an object')
    for k in ('skills', 'tools'):
        if not isinstance(base.get(k, []), list):
            bad('«base.%s» must be a list' % k)
    browser = catalog.get('browser', {})
    if not isinstance(browser, dict):
        bad('«browser» must be an object')
    for k in ('areas', 'tools'):
        if not isinstance(browser.get(k, []), list):
            bad('«browser.%s» must be a list' % k)
    areas = catalog.get('areas', {})
    if not isinstance(areas, dict):
        bad('«areas» must be an object')
    for name, d in areas.items():
        if not isinstance(d, dict):
            bad('area «%s» must be an object' % name)
        for k in ('skills', 'plugins', 'agents', 'tools'):
            if not isinstance(d.get(k, []), list):
                bad('«areas.%s.%s» must be a list' % (name, k))


def check(args):
    """Runs the check and returns a dictionary with the result (prints nothing)."""
    errors, warnings = [], []
    project = os.path.abspath(args.project or os.getcwd())
    home = os.path.abspath(os.path.expanduser(args.home)) if args.home else os.path.expanduser('~')
    if not os.path.isdir(project):
        raise UsageError('The project folder does not exist: %s' % project)
    catalog_path = args.catalog or _default_catalog()
    if not catalog_path or not os.path.isfile(catalog_path):
        raise UsageError('Catalog %s not found (pass it with --catalog).' % (catalog_path or CATALOG_NAME))
    try:
        catalog = _read_json(catalog_path)
    except (OSError, ValueError) as e:
        raise UsageError('The catalog %s is not valid JSON: %s' % (catalog_path, e))
    _check_catalog_shape(catalog, catalog_path)

    config = {}
    config_path = os.path.join(project, 'sdd.config.json')
    if os.path.isfile(config_path):
        try:
            config = _read_json(config_path)
            if not isinstance(config, dict):
                raise ValueError('not an object')
        except (OSError, ValueError) as e:
            errors.append('sdd.config.json cannot be read (%s): the defaults are used.' % e)
            config = {}
    vocab, vocab_error = V.vocabulary(config)
    if vocab_error:
        raise UsageError(vocab_error)  # like a malformed catalog: exit code 2 (CA-VOC-01.5)
    config, doubles = V.normalize(config)
    warnings.extend(doubles)
    env_cfg = config.get('environment') if isinstance(config.get('environment'), dict) else {}
    for k in config:
        if not str(k).startswith('_') and k not in CONFIG_KEYS:
            warnings.append('Unknown key in sdd.config.json: «%s» (ignored).' % k)
    for k in env_cfg:
        if not str(k).startswith('_') and k not in ENVIRONMENT_KEYS:
            warnings.append('Unknown key in sdd.config.json: «environment.%s» (ignored).' % k)
    if args.areas is not None:
        areas = V.areas([a.strip() for a in args.areas.split(',') if a.strip()])
    else:
        areas = _as_list(config.get('areas'))

    env = Environment(project, home, own_plugin=not args.home)
    warnings.extend(env.warnings)
    adopted = str((config.get('method') or {}).get('version') or '') if isinstance(config.get('method'), dict) else ''
    if env.own and adopted and env.own[1] and adopted != env.own[1]:
        if _vtuple(env.own[1]) and _vtuple(adopted) and _cmp(_vtuple(env.own[1]), _vtuple(adopted)) < 0:
            errors.append('The project adopted %s %s and this session uses %s, which is older: update the plugin.'
                          % (env.own[0], adopted, env.own[1]))
        else:
            warnings.append('The project adopted %s %s and this session uses %s: check the plugin CHANGELOG and, if '
                            'something that affects the project changed, record it with a decision.'
                            % (env.own[0], adopted, env.own[1]))

    # -- Set of needed skills ---------------------------------------------------------------------
    needed = OrderedDict()   # bare name -> {'plugin', 'strict', 'by', 'entry'}

    def add(entry, by, method_plugin=None):
        entry = str(entry).strip()
        if not entry:
            return
        plugin, name = entry.split(':', 1) if ':' in entry else (None, entry)
        strict = plugin is not None
        if method_plugin and plugin is None:
            plugin, strict = method_plugin, False
        spec = needed.setdefault(name, {'plugin': plugin, 'strict': strict, 'by': [], 'entry': entry})
        if by not in spec['by']:
            spec['by'].append(by)

    requested = OrderedDict()      # tool -> {range: [who]}

    def request(tool, rng, who):
        q = requested.setdefault(str(tool).strip(), OrderedDict()).setdefault(rng or '*', [])
        if who not in q:
            q.append(who)

    base = catalog.get('base') or {}
    if not args.quick:
        for n in catalog.get('method') or []:
            add(n, 'base', method_plugin=catalog.get('method_plugin'))
    for n in base.get('skills') or []:
        add(n, 'base')
    for t in base.get('tools') or []:
        request(t, '*', 'base')

    cat_areas = catalog.get('areas') or {}
    by_norm = {_norm(k): k for k in cat_areas}
    areas_used, areas_to_review = [], []
    plugins_requested = OrderedDict()   # plugin -> [area]
    agents_requested = OrderedDict()    # agent -> {'plugins': [...], 'by': [...]}
    domains = None
    for a in areas:
        k = by_norm.get(_norm(a))
        if k:
            if k in areas_used:
                continue
            areas_used.append(k)
            d = cat_areas[k] or {}
            for n in d.get('skills') or []:
                add(n, k)
            for p in d.get('plugins') or []:
                plugins_requested.setdefault(p, []).append(k)
            for ag in d.get('agents') or []:
                e = agents_requested.setdefault(ag, {'plugins': [], 'by': []})
                e['plugins'].extend(p for p in d.get('plugins') or [] if p not in e['plugins'])
                e['by'].append(k)
            for t in d.get('tools') or []:
                request(t, '*', k)
            continue
        if domains is None:
            domains = env.domain_index()
        e = domains.get(_norm(a))
        if e:
            areas_used.append(a)
            areas_to_review.append(a)
            for n in sorted(e['skills']):
                add(n, a)
            warnings.append('Area «%s» has no entry in the catalog: the %d installed skills with metadata.domains '
                            '«%s» have been taken. Review it by hand: move the ones you need to extra_skills and remove '
                            'the area, or add it to the catalog.' % (a, len(e['skills']), e['domain']))
        else:
            errors.append('Unknown area «%s»: it is not in the catalog and matches no metadata.domains of the '
                          'installed skills. Catalog areas: %s. Domains seen: %s.'
                          % (a, ', '.join(sorted(cat_areas)),
                             ', '.join(sorted(v['domain'] for v in domains.values())) or 'none'))
    if not areas:
        warnings.append('No areas declared («areas» in sdd.config.json or --areas): only the base is checked.')

    # -- Browser (rule M-12): environment.browser or, without it, an area of browser.areas -----------
    bcat = catalog.get('browser') or {}
    wants = env_cfg.get('browser')
    if not isinstance(wants, bool):
        # A project from before 0.5 has no environment.browser: nothing breaks. The browser is required if it already
        # has the «playwright» server; with UI areas and without it, a warning says how to add it.
        try:
            mcp = _read_json(os.path.join(project, '.mcp.json'))
            wants = isinstance(mcp, dict) and 'playwright' in (mcp.get('mcpServers') or {})
        except (OSError, ValueError, AttributeError):
            wants = False
        ui = sorted(set(bcat.get('areas') or []) & set(areas_used))
        if not wants and ui and bcat:
            warnings.append('Browser: the project has UI areas (%s) and no browser for its tests (rule M-12). To add '
                            'it, run sdd-bootstrap with --add-missing, which writes .mcp.json, and set '
                            'environment.browser to true in sdd.config.json.' % ', '.join(ui))
    browser_entry = None
    if wants and bcat:
        for t in bcat.get('tools') or []:
            request(t, '*', 'browser')
        b_errors, b_warnings, browser_entry = browser_gaps(project, home, bcat, explicit_home=bool(args.home))
        errors.extend(b_errors)
        warnings.extend(b_warnings)

    if not args.quick:
        for n in _as_list(env_cfg.get('extra_skills')):
            add(n, 'extra')
    removed = []
    for n in _as_list(env_cfg.get('excluded_skills')):
        bare = str(n).split(':', 1)[-1].strip()
        if bare in needed:
            del needed[bare]
            removed.append(bare)
    if removed:
        warnings.append('Excluded by excluded_skills (not checked): %s.' % ', '.join(removed))

    # -- Resolution -------------------------------------------------------------------------------
    rows = []
    for name, spec in needed.items():
        r = env.resolve(name, spec['plugin'], spec['strict'])
        r['needed_by'] = list(spec['by'])
        r['entry'] = spec['entry']
        rows.append(r)
        warnings.extend(r['warnings'])

    agent_rows = []
    for ag, d in agents_requested.items():
        sources = [o for o in env.agents.get(ag, [])
                   if not o[0].startswith('plugin:') or env.plugin_ok(o[0][len('plugin:'):])]
        preferred = next((o for o in sources if o[0][len('plugin:'):] in d['plugins']),
                         sources[0] if sources else None)
        row = {'name': ag, 'by': d['by'], 'state': 'present' if preferred else 'missing',
               'source': preferred[0] if preferred else None, 'path': preferred[1] if preferred else None,
               'missing_plugin': None}
        if not preferred:
            row['missing_plugin'] = next((p for p in d['plugins'] if not env.plugin_ok(p)), None)
        agent_rows.append(row)
    inventory_agents = set(a['name'] for a in agent_rows if a['state'] == 'present')
    for p in plugins_requested:
        if env.plugin_ok(p):
            inventory_agents.update(env.plugins[p]['agents'])

    # -- Skill and plugin errors -----------------------------------------------------------------
    groups = OrderedDict()

    def group(p):
        return groups.setdefault(p, {'by': [], 'skills': [], 'agents': [], 'notes': []})

    for p, by in plugins_requested.items():
        if not env.plugin_ok(p):
            g = group(p)
            g['by'].extend(x for x in by if x not in g['by'])
    for r in rows:
        if r['state'] == 'missing' and r['missing_plugin']:
            g = group(r['missing_plugin'])
            g['skills'].append(r['name'])
            g['by'].extend(x for x in r['needed_by'] if x not in g['by'])
            if '; ' in r['reason']:  # e.g., a standalone copy that does not replace the plugin
                g['notes'].append('%s: %s' % (r['name'], r['reason'].split('; ', 1)[1]))
    for a in agent_rows:
        if a['state'] == 'missing' and a['missing_plugin']:
            g = group(a['missing_plugin'])
            g['agents'].append(a['name'])
            g['by'].extend(x for x in a['by'] if x not in g['by'])
    for p, g in groups.items():
        info = env.plugins.get(p)
        state = 'is not installed' if info is None else 'is installed but disabled in enabledPlugins'
        lacking = []
        if g['skills']:
            lacking.append('the skills ' + ', '.join(g['skills']))
        if g['agents']:
            lacking.append('the agents ' + ', '.join(g['agents']))
        action = 'Install it from its marketplace' if info is None else 'Enable it'
        notes = (' Also: %s.' % '; '.join(g['notes'])) if g['notes'] else ''
        errors.append('Plugin %s %s (needed by: %s). Without it, %s are missing. %s and open a new session.%s'
                      % (p, state, ', '.join(g['by']), ' and '.join(lacking) or 'its skills', action, notes))
    for r in rows:
        by = ', '.join(r['needed_by'])
        if r['state'] == 'missing' and not r['missing_plugin']:
            errors.append('Skill %s missing (needed by %s): %s.' % (r['name'], by, r['reason']))
        elif r['state'] == 'shadowed':
            errors.append('Skill %s shadowed (needed by %s): %s Keep a single copy, or make them identical, and open '
                          'a new session.' % (r['name'], by, r['reason']))
        if r['copy'] is not None and r['copy'].data['name'] and r['copy'].data['name'] != r['name']:
            warnings.append('Folder %s declares name: %s in its frontmatter.' % (r['name'], r['copy'].data['name']))
        if r['copy'] is not None and r['copy'].data is not None and r['copy'].fm_problem:
            warnings.append('The frontmatter of %s (%s) cannot be read (%s): its cliTools, minApiVersion and version '
                            'are not checked.' % (r['name'], r['copy'].path, r['copy'].fm_problem))
    for a in agent_rows:
        if a['state'] == 'missing' and not a['missing_plugin']:
            errors.append('Agent %s missing (requested by: %s): not in plugins %s nor in .claude/agents/.'
                          % (a['name'], ', '.join(a['by']), ', '.join(plugins_requested) or '-'))

    # -- Derived requirements: tools -------------------------------------------------------------
    for r in rows:
        if r['copy'] is not None:
            for t, rng in r['copy'].data['cliTools']:
                request(t, rng, r['name'])
    tool_rows = []
    for t in sorted(requested):
        ranges = requested[t]
        who = []
        for qs in ranges.values():
            who.extend(q for q in qs if q not in who)
        strictest = _strictest_range(list(ranges))
        if not _RE_TOOL_NAME.match(t):
            warnings.append('Tool with an invalid name in cliTools: %r (requested by %s); it is not run.'
                            % (t, ', '.join(who)))
            continue
        version, path, note = tool_version(t)
        detail = ''
        if version is None:
            state = 'missing'
            errors.append('Tool %s missing (%s): required %s; requested by %s.' % (t, note, strictest, ', '.join(who)))
        elif version == '?':
            really_strict = strictest != '*'
            state = 'below_minimum' if really_strict else 'ok'
            detail = note
            if really_strict:
                errors.append('Tool %s: %s, so %s cannot be checked (requested by %s).'
                              % (t, note, strictest, ', '.join(who)))
        else:
            failing, odd = [], []
            for rg, qs in ranges.items():
                c = _satisfies(version, rg)
                if c is False:
                    failing.append((rg, qs))
                elif c is None:
                    odd.append((rg, qs))
            for rg, qs in odd:
                warnings.append('Unrecognised version range for %s: %r (requested by %s).' % (t, rg, ', '.join(qs)))
            if failing:
                state = 'below_minimum'
                failing.sort(key=lambda x: _bound(x[0]), reverse=True)
                parts = '; '.join('%s (requested by %s)' % (rg, ', '.join(qs)) for rg, qs in failing)
                msg = 'Tool %s %s is below what is required: %s.' % (t, version, parts)
                if t == 'python3':
                    msg += _python_hint(failing[0][0])
                errors.append(msg)
                detail = 'does not satisfy ' + ', '.join(rg for rg, _ in failing)
            else:
                state = 'ok'
        tool_rows.append({'name': t, 'required': strictest,
                          'installed': version if version not in (None, '?') else None,
                          'state': state, 'who': who, 'path': path, 'detail': detail})

    # -- Derived requirements: org API -----------------------------------------------------------
    api_reqs = []
    for r in rows:
        if r['copy'] is not None and r['copy'].data['minApiVersion']:
            v = r['copy'].data['minApiVersion']
            if _vtuple(v):
                api_reqs.append((v, r['name']))
    required_api = None
    for v, _ in api_reqs:
        if required_api is None or _cmp(_vtuple(v), _vtuple(required_api)) > 0:
            required_api = v
    org_api, api_source, org_details = None, '', {}
    if args.api_org:
        org_api, api_source = args.api_org.strip(), '--api-org'
        if args.query_org:
            warnings.append('--api-org was given: the org is not queried (--query-org ignored).')
    elif args.query_org:
        alias = str(config.get('org_alias') or '').strip()
        org_api, note = query_org_api(alias, org_details)
        api_source = 'sf org display --target-org %s' % alias if alias else ''
        if org_api is None:
            errors.append('Could not read the org API with --query-org: %s.' % note)
    if org_api is not None and not _vtuple(org_api):
        errors.append('Unrecognised org API: %r.' % org_api)
        org_api = None
    if org_api is None:
        api_state = 'not_checked'
        if not args.query_org and args.quick:
            warnings.append('Org API not checked: pass --api-org <version> or --query-org (it uses the org_alias '
                            'of sdd.config.json).')
        elif not args.query_org:
            errors.append('Org API not checked: in the full check this is a blocker. Run again with --query-org, '
                          'which reads the API only from the org_alias of sdd.config.json (%s), or pass '
                          '--api-org <version>; if that alias has no login, record it as a blocker in questions.md.'
                          % (str(config.get('org_alias') or '').strip() or 'empty'))
    elif required_api is None or _cmp(_vtuple(org_api), _vtuple(required_api)) >= 0:
        api_state = 'ok'
    else:
        api_state = 'below_minimum'
        below = sorted(((v, n) for v, n in api_reqs if _cmp(_vtuple(v), _vtuple(org_api)) > 0),
                       key=lambda x: _vtuple(x[0]), reverse=True)
        errors.append('Org API %s is below the minimum %s: requested by %s.'
                      % (org_api, required_api, ', '.join('%s (%s)' % (n, v) for v, n in below)))

    # -- Warnings for recommended skills and other shadowed ones ---------------------------------
    needed_names = set(needed)
    missing_rel = OrderedDict()
    for r in rows:
        if r['copy'] is None:
            continue
        for rel in r['copy'].data['relatedSkills']:
            bare = rel.split(':', 1)[-1]
            if bare in needed_names:
                continue
            there = any(c.kind != 'plugin' or env.plugin_ok(c.plugin) for c in env.copies.get(bare, []))
            if not there:
                missing_rel.setdefault(bare, []).append(r['name'])
    for s, who in missing_rel.items():
        warnings.append('Recommended skill %s is not in any layer (cited in relatedSkills by: %s).'
                        % (s, ', '.join(who)))
    other_shadowed = []
    for name, copies in env.copies.items():
        if name in needed_names:
            continue
        if len(set(c.hash for c in copies if c.kind != 'plugin')) > 1:
            other_shadowed.append(name)
    if other_shadowed:
        other_shadowed.sort()
        warnings.append('%d other shadowed skills outside the needed set (same name, different content in several '
                        'layers): %s%s.' % (len(other_shadowed), ', '.join(other_shadowed[:25]),
                                            ', …' if len(other_shadowed) > 25 else ''))

    # -- Inventory -------------------------------------------------------------------------------
    now = _dt.datetime.now().astimezone()
    inventory = OrderedDict()
    inventory['generated'] = now.isoformat(timespec='seconds')
    inventory['areas'] = list(areas_used)
    inventory['skills'] = OrderedDict(
        (r['name'], OrderedDict([('state', r['state']), ('layer', r['layer']), ('path', r['path']),
                                 ('version', r['version']), ('needed_by', r['needed_by'])]))
        for r in rows)
    inventory['agents'] = sorted(inventory_agents)
    inventory['tools'] = OrderedDict(
        (h['name'], OrderedDict([('required', h['required']), ('installed', h['installed']), ('state', h['state'])]))
        for h in tool_rows)
    inventory['org_api'] = OrderedDict([('required', required_api), ('org', org_api), ('state', api_state)])
    # The My Domain is what the browser guard compares; without a new query, that of the previous inventory is kept.
    rel_inv = str(env_cfg.get('inventory') or V.INVENTORY_PATH[vocab])
    previous = {}
    try:
        previous = _read_json(rel_inv if os.path.isabs(rel_inv) else os.path.join(project, rel_inv))
        previous = previous.get('org') if isinstance(previous, dict) and isinstance(previous.get('org'), dict) else {}
    except (OSError, ValueError):
        previous = {}
    alias_now = str(config.get('org_alias') or '').strip()
    kept = previous.get('my_domain') if str(previous.get('alias') or '').strip() == alias_now else None
    my_domain = org_details.get('my_domain') or kept
    inventory['org'] = OrderedDict([('alias', str(config.get('org_alias') or '').strip() or None),
                                    ('my_domain', my_domain or None)])
    if browser_entry is not None:
        inventory['browser'] = browser_entry
    # Light profile (rule M-11): the gaps are warnings that the approver sees at the Plan gate.
    light = V.profile(config.get('method') if isinstance(config.get('method'), dict) else {}) == 'light'
    if light and errors:
        warnings.extend('Gap (light profile: a warning; record it in questions.md): %s' % e for e in errors)
        errors = []

    res = {
        'project': project, 'home': home, 'environment': env, 'catalog': catalog_path,
        'release': str(catalog.get('sf_skills_release') or '?'),
        'project_name': str(config.get('project') or os.path.basename(project.rstrip(os.sep)) or project),
        'date': now.date().isoformat(), 'quick': bool(args.quick), 'areas_to_review': areas_to_review,
        'rows': rows, 'agent_rows': agent_rows, 'tool_rows': tool_rows,
        'api': {'required': required_api, 'org': org_api, 'state': api_state, 'source': api_source,
                'who': api_reqs},
        'errors': errors, 'warnings': warnings, 'inventory': inventory, 'files': [],
    }
    res['light'] = light
    res['exit_code'] = 1 if errors and not args.quick else 0

    if not args.quick and not args.no_write:
        md = os.path.join(project, 'docs', 'baseline', V.REPORT_NAME[vocab] % res['date'])
        rel = str(env_cfg.get('inventory') or V.INVENTORY_PATH[vocab])
        inv = rel if os.path.isabs(rel) else os.path.join(project, rel)
        for path, content in ((md, report_md(res)),
                              (inv, json.dumps(inventory, ensure_ascii=False, indent=2) + '\n')):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write(content)
            res['files'].append(path)
    return res


# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------

def _cell(s):
    return str(s if s not in (None, '') else '-').replace('|', '\\|').replace('\n', ' ')


def _skill_detail(r):
    if r['state'] == 'missing':
        return r['reason']
    if r['state'] == 'shadowed':
        t = r['shadowed']
        return '%s. Others: %s. %s' % (t['loads'], t['others'], t['verdict'])
    if r['identical']:
        return 'also in %s, identical' % ', '.join(r['identical'])
    return ''


def report_md(res):
    inv = res['inventory']
    env = res['environment']
    L = []
    L.append('# Environment inventory · %s · %s' % (res['project_name'], res['date']))
    L.append('')
    L.append('Generated by `check-environment.py` on %s for `%s`. Catalog: sf-skills %s. Areas: %s.'
             % (inv['generated'], env.short(res['project']), res['release'], ', '.join(inv['areas']) or 'none (base only)'))
    if res['areas_to_review']:
        L.append('')
        L.append('Areas taken from `metadata.domains`, to review by hand: %s.' % ', '.join(res['areas_to_review']))
    L.append('')
    if res['errors']:
        L.append('**Result: %d errors and %d warnings.** Each error is a blocker in `questions.md`: the Plan gate does '
                 'not pass until it is resolved or the approver accepts the gap as a decision.'
                 % (len(res['errors']), len(res['warnings'])))
    else:
        L.append('**Result: no errors, %d warnings.**' % len(res['warnings']))
    L.append('')
    L.append('## Skills')
    L.append('')
    L.append('| Skill | Needed by | Layer | Version | State | Detail |')
    L.append('|---|---|---|---|---|---|')
    for r in res['rows']:
        L.append('| %s | %s | %s | %s | %s | %s |' % (
            _cell(r['name']), _cell(', '.join(r['needed_by'])), _cell(r['layer']), _cell(r['version']),
            _cell(r['state']), _cell(_skill_detail(r))))
    L.append('')
    layers = ['%s `%s` (%d)' % (e, env.short(c), n) for e, c, n in env.layers]
    layers += ['plugin %s %s (%d skills%s)' % (p, i['version'], i['skills'], '' if i['enabled'] else ', disabled')
               for p, i in env.plugins.items()]
    L.append('Layers scanned: %s.' % ('; '.join(layers) or 'none'))
    if res['agent_rows']:
        L.append('')
        L.append('## Agents')
        L.append('')
        L.append('| Agent | Requested by | Source | State |')
        L.append('|---|---|---|---|')
        for a in res['agent_rows']:
            L.append('| %s | %s | %s | %s |' % (_cell(a['name']), _cell(', '.join(a['by'])), _cell(a['source']),
                                              _cell(a['state'])))
    L.append('')
    L.append('## Tools')
    L.append('')
    L.append('| Tool | Required | Installed | State | Requested by |')
    L.append('|---|---|---|---|---|')
    for h in res['tool_rows']:
        L.append('| %s | %s | %s | %s | %s |' % (_cell(h['name']), _cell(h['required']), _cell(h['installed']),
                                               _cell(h['state'] + (' (%s)' % h['detail'] if h['detail'] else '')),
                                               _cell(', '.join(h['who']))))
    L.append('')
    L.append('## Org API')
    L.append('')
    a = res['api']
    L.append('| Required | Org | State | Source |')
    L.append('|---|---|---|---|')
    L.append('| %s | %s | %s | %s |' % (_cell(a['required']), _cell(a['org']), _cell(a['state']), _cell(a['source'])))
    L.append('')
    if a['who']:
        L.append('Required = the highest `minApiVersion` of the needed skills (%s).'
                 % ', '.join('%s %s' % (n, v) for v, n in sorted(a['who'], key=lambda x: _vtuple(x[0]), reverse=True)[:8]))
    else:
        L.append('No needed skill declares `minApiVersion`.')
    for title, items in (('Errors', res['errors']), ('Warnings', res['warnings'])):
        L.append('')
        L.append('## %s' % title)
        L.append('')
        L.extend('- %s' % x for x in items) if items else L.append('_None._')
    L.append('')
    L.append('---')
    L.append('')
    L.append(SOURCE_OF_TRUTH_NOTE)
    L.append('')
    return '\n'.join(L)


def print_text(res, out):
    def w(s=''):
        out.write(s + '\n')
    inv = res['inventory']
    env = res['environment']
    w('check-environment · %s · %s%s' % (res['project_name'], res['date'], ' · quick check' if res['quick'] else ''))
    w('Project: %s' % env.short(res['project']))
    w('Catalog: %s (sf-skills %s)' % (env.short(res['catalog']), res['release']))
    w('Areas: %s%s' % (', '.join(inv['areas']) or 'none (base only)',
                       ' · by domain, to review: %s' % ', '.join(res['areas_to_review']) if res['areas_to_review'] else ''))
    w('Layers: %s' % ('; '.join('%s %s (%d)' % (e, env.short(c), n) for e, c, n in env.layers) or 'none'))
    w('Plugins: %s' % ('; '.join('%s %s (%d skills, %d agents%s)' % (p, i['version'], i['skills'], len(i['agents']),
                                                                     '' if i['enabled'] else ', disabled')
                                 for p, i in env.plugins.items()) or env.plugins_note or 'none'))
    w()
    count = OrderedDict((e, 0) for e in ('present', 'missing', 'shadowed'))
    for r in res['rows']:
        count[r['state']] += 1
    w('Needed skills: %d · %s' % (len(res['rows']), ' · '.join('%s %d' % (k, v) for k, v in count.items())))
    for r in res['rows']:
        if r['state'] != 'present':
            w('  %-8s %-44s %s' % (r['state'], r['name'], ', '.join(r['needed_by'])))
    if res['agent_rows']:
        w('Agents: %s' % ', '.join('%s %s' % (a['name'], a['state']) for a in res['agent_rows']))
    w('Tools:')
    for h in res['tool_rows']:
        w('  %-10s %-12s %-12s %s' % (h['name'], h['required'], h['installed'] or '-', h['state']))
    a = res['api']
    w('Org API: required %s · org %s%s · %s' % (a['required'] or '-', a['org'] or '-',
                                               ' (%s)' % a['source'] if a['source'] and a['org'] else '', a['state']))
    for title, items in (('Errors', res['errors']), ('Warnings', res['warnings'])):
        w()
        w('%s (%d):' % (title, len(items)))
        for x in items:
            w('  - ' + x)
    if res['files']:
        w()
        w('Written: %s' % ', '.join(os.path.relpath(f, res['project']) for f in res['files']))
    w()
    if res['quick']:
        w('Quick check (base and areas): it warns, it does not block. The full check runs at the start of Plan.')
    w(SOURCE_OF_TRUTH_NOTE)


def json_output(res):
    return json.dumps(OrderedDict([('inventory', res['inventory']), ('errors', res['errors']),
                                   ('warnings', res['warnings']), ('areas_to_review', res['areas_to_review']),
                                   ('files', res['files']), ('exit_code', res['exit_code'])]),
                      ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Catalog maintenance
# ---------------------------------------------------------------------------

def validate_catalog(catalog_path, sf_dir, home, out):
    cat = _read_json(catalog_path)
    if not os.path.isdir(sf_dir):
        raise UsageError('The sf-skills folder does not exist: %s' % sf_dir)
    existing = set(d for d in os.listdir(sf_dir) if os.path.isfile(os.path.join(sf_dir, d, 'SKILL.md')))
    env = Environment(home, home, standalone_layers=False)
    problems, notes = [], []
    entries = [('base', n) for n in (cat.get('base') or {}).get('skills') or []]
    for a, d in (cat.get('areas') or {}).items():
        if not re.match(r'^[a-z0-9]+(-[a-z0-9]+)*$', a):
            problems.append('Invalid area ID: %r (lowercase letters, digits and hyphens).' % a)
        if not (d or {}).get('description'):
            problems.append('Area %s has no description.' % a)
        if not (d or {}).get('skills') and not (d or {}).get('agents'):
            problems.append('Area %s has no skills or agents.' % a)
        seen = set()
        for n in (d or {}).get('skills') or []:
            if n in seen:
                problems.append('Area %s: %s repeated.' % (a, n))
            seen.add(n)
            entries.append((a, n))
        for ag in (d or {}).get('agents') or []:
            ps = (d or {}).get('plugins') or []
            if not any(env.plugin_ok(p) for p in ps):
                notes.append('Area %s: agent %s cannot be checked (plugin %s not installed here).'
                             % (a, ag, ', '.join(ps) or '-'))
            elif not any(ag in env.plugins[p]['agents'] for p in ps if env.plugin_ok(p)):
                problems.append('Area %s: agent %s is not in %s.' % (a, ag, ', '.join(ps)))
    checked = 0
    for by, n in entries:
        if ':' in n:
            p, s = n.split(':', 1)
            if p not in env.plugins:
                notes.append('%s: %s cannot be checked (plugin %s not installed here).' % (by, n, p))
            elif not any(c.plugin == p for c in env.copies.get(s, [])):
                problems.append('%s: plugin %s %s does not include skill %s.' % (by, p, env.plugins[p]['version'], s))
            else:
                checked += 1
            continue
        checked += 1
        if n not in existing:
            problems.append('%s: %s does not exist in %s.' % (by, n, sf_dir))
    out.write('Catalog %s (sf-skills %s) against %s (%d skills).\n'
              % (catalog_path, cat.get('sf_skills_release'), sf_dir, len(existing)))
    out.write('%d names checked, %d problems.\n' % (checked, len(problems)))
    for p in problems:
        out.write('  ERROR %s\n' % p)
    for note in notes:
        out.write('  warning %s\n' % note)
    return 1 if problems else 0


# ---------------------------------------------------------------------------
# Self-tests (simulated layers in a temporary folder, with a fake $HOME)
# ---------------------------------------------------------------------------

_TEST_FRONTMATTER = '''---
name: parser-test
description: >
  Folded description
  on two lines.
allowed-tools: Bash(sf org display:*) Read
metadata:
  relatedSkills:
  - "other-skill"
  - third-skill   # comment
  version: '1.4'
  domains: ["Consumer Goods", 'Data 360']
  minApiVersion: "66.0"
  cliTools:
  - tool:
    - curl
    semver: '>=7.0'
  - tool: ["jq"]
    semver: ">=1.6"
  - tool: [sf]
    semver: ">=2.0.0"
  mcpTools:
    test-mcp:
      tools: ["describe", "discover"]
    skill_bridge: { tools: ["load_skill", "search_skills"], semver: ">=1.0.0" }
---
Body.
'''

_TEST_CATALOG = {
    'sf_skills_release': 'self-test',
    'method_plugin': 'sdd-salesforce',
    'method': ['sdd-bootstrap'],
    'base': {'skills': ['base-one'], 'tools': []},
    'areas': {
        'agentforce': {'description': 'ADLC', 'plugins': ['agentforce-adlc'],
                       'skills': ['agentforce-adlc:agentforce-generate', 'agentforce-adlc:agentforce-test',
                                  'agentforce-adlc:agentforce-observe'],
                       'agents': ['adlc-author', 'adlc-engineer', 'adlc-qa']},
        'shadowed': {'description': 'shadowed', 'skills': ['skill-dup']},
        'tools': {'description': 'tools', 'skills': ['skill-tools']},
        'api': {'description': 'api', 'skills': ['skill-api']},
        'ui': {'description': 'ui', 'skills': ['base-one']},
    },
    'browser': {'package': '@playwright/mcp', 'version': '0.0.1', 'chromium_revision': '1', 'areas': ['ui'],
                'tools': []},
}

_ADLC = ['agentforce-generate', 'agentforce-test', 'agentforce-observe']


def _md_skill(name, version='1.0', meta='', body='Test body.'):
    return '---\nname: %s\ndescription: "Test skill."\nmetadata:\n  version: "%s"\n%s---\n\n%s\n' % (
        name, version, (meta.rstrip('\n') + '\n') if meta else '', body)


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(text)


def _skill(folder, name, **kw):
    _write(os.path.join(folder, name, 'SKILL.md'), _md_skill(name, **kw))


def _install_plugin(home, name, skills=(), agents=(), version='0.0.1'):
    path = os.path.join(home, '.claude', 'plugins', 'cache', 'tests', name, version)
    for s in skills:
        _skill(os.path.join(path, 'skills'), s)
    for a in agents:
        _write(os.path.join(path, 'agents', a + '.md'), '---\nname: %s\ndescription: test\n---\n' % a)
    f = os.path.join(home, '.claude', 'plugins', 'installed_plugins.json')
    data = _read_json(f) if os.path.isfile(f) else {'version': 2, 'plugins': {}}
    data['plugins'][name + '@tests'] = [{'scope': 'user', 'installPath': path, 'version': version}]
    _write(f, json.dumps(data, indent=2))


def _uninstall_plugin(home, name):
    f = os.path.join(home, '.claude', 'plugins', 'installed_plugins.json')
    data = _read_json(f)
    data['plugins'].pop(name + '@tests', None)
    _write(f, json.dumps(data, indent=2))


def self_test(out):
    results = []

    def ok(cond, ca, text):
        results.append((bool(cond), ca, text))
        out.write('%s  %-12s %s\n' % ('OK   ' if cond else 'FAIL ', ca, text))

    tmp = tempfile.mkdtemp(prefix='check-environment-self-test-')
    original_path = os.environ.get('PATH', '')
    initial_log = len(COMMANDS_RUN)
    try:
        bin_dir = os.path.join(tmp, 'bin')
        fake = os.path.join(bin_dir, 'sdd-fake-tool')
        _write(fake, '#!/bin/sh\necho "sdd-fake-tool 1.2.3"\n')
        os.chmod(fake, 0o755)
        os.environ['PATH'] = bin_dir + os.pathsep + original_path
        counter = [0]

        def scenario():
            counter[0] += 1
            root = os.path.join(tmp, 'e%d' % counter[0])
            home = os.path.join(root, 'home')
            project = os.path.join(home, 'work', 'acme')
            os.makedirs(project)
            catalog = os.path.join(root, CATALOG_NAME)
            _write(catalog, json.dumps(_TEST_CATALOG, ensure_ascii=False))
            _install_plugin(home, 'sdd-salesforce', skills=['sdd-bootstrap'])
            _skill(os.path.join(home, '.claude', 'skills'), 'base-one')
            return home, project, catalog

        def run(home, project, catalog, *extra, **kw):
            argv = ['--home', home, '--project', project, '--catalog', catalog]
            if not kw.get('write'):
                argv.append('--no-write')
            return check(_parser().parse_args(argv + list(extra)))

        user = lambda h: os.path.join(h, '.claude', 'skills')            # noqa: E731
        of_project = lambda p: os.path.join(p, '.claude', 'skills')      # noqa: E731

        # -- Frontmatter parser ----------------------------------------------------------------
        fm = read_frontmatter(_TEST_FRONTMATTER)
        d = skill_data(fm)
        ok(d['cliTools'] == [('curl', '>=7.0'), ('jq', '>=1.6'), ('sf', '>=2.0.0')], 'parser',
           'cliTools as a block and inline: %s' % d['cliTools'])
        ok(d['version'] == '1.4' and d['minApiVersion'] == '66.0' and d['domains'] == ['Consumer Goods', 'Data 360'],
           'parser', 'version, minApiVersion and domains')
        ok(d['relatedSkills'] == ['other-skill', 'third-skill'], 'parser', 'relatedSkills with a comment')
        ok(fm.get('description') == 'Folded description on two lines.' and
           fm.get('allowed-tools') == 'Bash(sf org display:*) Read', 'parser', '«>» block and a value with a colon')
        ok(fm['metadata']['mcpTools']['skill_bridge'] == {'tools': ['load_skill', 'search_skills'], 'semver': '>=1.0.0'},
           'parser', 'inline map')
        ok(_satisfies('2.139.6', '>=2.139.6') and not _satisfies('2.100.0', '>=2.139.6') and _satisfies('3.12.1', '>=3.10')
           and not _satisfies('3.9.6', '>=3.10.0') and _satisfies('22.1.0', '^22.0.0')
           and not _satisfies('23.0.0', '^22.0.0'),
           'semver', 'range comparison')
        ok(_extract_version('@salesforce/cli/2.139.6 darwin-arm64 node-v22.22.3') == '2.139.6' and
           _extract_version('jq-1.7.1') == '1.7.1' and _extract_version('Python 3.9.6') == '3.9.6' and
           _extract_version('git version 2.39.5 (Apple Git-154)') == '2.39.5' and
           _extract_version('v22.22.3') == '22.22.3',
           'semver', 'reading --version (sf, jq, python3, git, node)')
        ok(_extract_version("openssl:Error: '--version' is an invalid command.\naes-128-cbc") is None and
           _extract_version('awk version 20200816', True) == '20200816' and _extract_version('LibreSSL 3.3.6') == '3.3.6',
           'semver', 'no false positives in error messages; BSD awk and LibreSSL')

        # -- CA-ENV-01.1: agentforce area without the ADLC plugin ------------------------------
        home, proj, cat = scenario()
        r = run(home, proj, cat, '--areas', 'agentforce', '--api-org', '66.0')
        sk = r['inventory']['skills']
        ok(all(sk[n]['state'] == 'missing' for n in _ADLC), 'CA-ENV-01.1', 'without ADLC, its three skills are missing')
        ok(r['exit_code'] == 1, 'CA-ENV-01.1', 'exit code 1')
        ok(any('agentforce-adlc' in e and 'is not installed' in e for e in r['errors']), 'CA-ENV-01.1',
           'the error names the missing plugin')
        ok(not r['inventory']['agents'] and all(a['state'] == 'missing' for a in r['agent_rows']),
           'CA-ENV-01.1', 'no adlc-* agents')
        _install_plugin(home, 'agentforce-adlc', skills=_ADLC,
                        agents=['adlc-author', 'adlc-engineer', 'adlc-qa', 'adlc-orchestrator'])
        r = run(home, proj, cat, '--areas', 'agentforce', '--api-org', '66.0')
        sk = r['inventory']['skills']
        ok(all(sk[n]['state'] == 'present' and sk[n]['layer'] == 'plugin:agentforce-adlc' for n in _ADLC)
           and r['exit_code'] == 0 and 'adlc-author' in r['inventory']['agents'], 'CA-ENV-01.1',
           'control: with the plugin, present from plugin:agentforce-adlc and exit code 0')
        _write(os.path.join(home, '.claude', 'settings.json'),
               json.dumps({'enabledPlugins': {'agentforce-adlc@tests': False}}))
        r = run(home, proj, cat, '--areas', 'agentforce', '--api-org', '66.0')
        ok(r['inventory']['skills']['agentforce-test']['state'] == 'missing' and r['exit_code'] == 1 and
           any('disabled' in e for e in r['errors']), 'CA-ENV-01.1', 'disabled plugin = missing')
        os.remove(os.path.join(home, '.claude', 'settings.json'))
        _uninstall_plugin(home, 'agentforce-adlc')
        _skill(of_project(proj), 'agentforce-generate')
        r = run(home, proj, cat, '--areas', 'agentforce', '--api-org', '66.0')
        ok(r['inventory']['skills']['agentforce-generate']['state'] == 'missing' and
           any('standalone copy' in e for e in r['errors']), 'CA-ENV-01.1',
           'a standalone copy does not replace the plugin')
        r = run(home, proj, cat, '--areas', 'agentforce', '--quick')
        ok(r['exit_code'] == 0 and not r['files'] and 'sdd-bootstrap' not in r['inventory']['skills'],
           '--quick', 'warns without blocking (exit code 0), writes nothing and skips the method skills')

        # -- CA-ENV-01.2: same skill in user and project with different content ----------------
        home, proj, cat = scenario()
        _skill(user(home), 'skill-dup', version='1.0', body='Personal copy.')
        _skill(of_project(proj), 'skill-dup', version='2.0', body='Project copy.')
        r = run(home, proj, cat, '--areas', 'shadowed', '--api-org', '66.0')
        s = r['inventory']['skills']['skill-dup']
        ok(s['state'] == 'shadowed' and s['layer'] == 'user', 'CA-ENV-01.2', 'shadowed; the user copy loads')
        ok(any(e.startswith('Skill skill-dup shadowed') and 'the user copy loads' in e and 'older' in e
               for e in r['errors']) and r['exit_code'] == 1, 'CA-ENV-01.2',
           'error that says which copy loads and that it is the older one')
        _skill(of_project(proj), 'skill-dup', version='1.0', body='Personal copy.')
        r = run(home, proj, cat, '--areas', 'shadowed', '--api-org', '66.0')
        ok(r['inventory']['skills']['skill-dup']['state'] == 'present' and r['exit_code'] == 0, 'CA-ENV-01.2',
           'control: identical copies = present')
        shutil.rmtree(os.path.join(user(home), 'skill-dup'))
        _skill(os.path.join(home, 'work', '.claude', 'skills'), 'skill-dup', version='0.9', body='Parent.')
        _skill(of_project(proj), 'skill-dup', version='1.1', body='Project.')
        r = run(home, proj, cat, '--areas', 'shadowed', '--api-org', '66.0')
        s = r['inventory']['skills']['skill-dup']
        ok(s['state'] == 'shadowed' and s['layer'] == 'project' and
           any('the project copy probably loads' in e and 'the newest' in e for e in r['errors']),
           'CA-ENV-01.2', 'parent versus project: the project copy probably loads')

        # -- CA-ENV-01.3: cliTools asks for an impossible version ------------------------------
        home, proj, cat = scenario()
        meta = ('  cliTools:\n'
                '    - tool: ["sdd-fake-tool"]\n      semver: ">=99.0.0"\n'
                '    - tool: ["sf"]\n      semver: ">=99.0.0"\n'
                '    - tool:\n      - sdd-missing-tool\n      semver: ">=1.0.0"\n')
        _skill(user(home), 'skill-tools', meta=meta)
        r = run(home, proj, cat, '--areas', 'tools', '--api-org', '66.0')
        h = r['inventory']['tools']
        ok(h['sdd-fake-tool']['state'] == 'below_minimum' and h['sdd-fake-tool']['installed'] == '1.2.3' and
           h['sdd-fake-tool']['required'] == '>=99.0.0', 'CA-ENV-01.3', 'tool below the minimum = below_minimum')
        ok(any(e.startswith('Tool sdd-fake-tool') and 'skill-tools' in e and '>=99.0.0' in e
               for e in r['errors']), 'CA-ENV-01.3', 'the error names the skill and the required version')
        ok(h['sf']['state'] in ('below_minimum', 'missing') and
           any(e.startswith('Tool sf ') and '>=99.0.0' in e and 'skill-tools' in e for e in r['errors']),
           'CA-ENV-01.3', 'sf >=99.0.0: error with the skill and the version (sf %s)' % (h['sf']['installed'] or 'missing'))
        ok(h['sdd-missing-tool']['state'] == 'missing' and
           any(e.startswith('Tool sdd-missing-tool missing') and 'skill-tools' in e
               for e in r['errors']) and r['exit_code'] == 1, 'CA-ENV-01.3', 'nonexistent tool = missing; exit code 1')
        _skill(user(home), 'skill-tools',
               meta='  cliTools:\n    - tool: ["sdd-fake-tool"]\n      semver: ">=1.0.0"\n')
        r = run(home, proj, cat, '--areas', 'tools', '--api-org', '66.0')
        ok(r['inventory']['tools']['sdd-fake-tool']['state'] == 'ok' and r['exit_code'] == 0,
           'CA-ENV-01.3', 'control: high enough version = ok')

        # -- CA-ENV-01.4: minApiVersion above the org API --------------------------------------
        home, proj, cat = scenario()
        _skill(user(home), 'skill-api', meta='  minApiVersion: "70.0"\n')
        r = run(home, proj, cat, '--areas', 'api', '--api-org', '66.0')
        a = r['inventory']['org_api']
        ok(a == {'required': '70.0', 'org': '66.0', 'state': 'below_minimum'} and r['exit_code'] == 1 and
           any(e.startswith('Org API 66.0') and 'skill-api (70.0)' in e for e in r['errors']),
           'CA-ENV-01.4', 'API 66.0 < 70.0: error with the skill that requires it')
        r = run(home, proj, cat, '--areas', 'api', '--api-org', '70.0')
        ok(r['inventory']['org_api']['state'] == 'ok' and r['exit_code'] == 0, 'CA-ENV-01.4', 'control: API 70.0 = ok')
        # -- CA-ENV-01.7: without --api-org or --query-org, the unchecked API blocks -----------
        r = run(home, proj, cat, '--areas', 'api')
        ok(r['inventory']['org_api']['state'] == 'not_checked' and r['exit_code'] == 1 and
           any(e.startswith('Org API not checked') and 'blocker' in e for e in r['errors']), 'CA-ENV-01.7',
           'full check without API: error (exit code 1)')
        r = run(home, proj, cat, '--areas', 'api', '--quick')
        ok(r['exit_code'] == 0 and any('not checked' in x for x in r['warnings']) and
           not any('not checked' in e for e in r['errors']), 'CA-ENV-01.7', '--quick without API: only a warning')

        # -- CA-ENV-01.8: same SKILL.md in two layers, another file different ----------------------
        home, proj, cat = scenario()
        for layer, text in ((user(home), 'Old rule.'), (of_project(proj), 'New rule.')):
            _skill(layer, 'skill-dup', version='1.0', body='Same in both.')
            _write(os.path.join(layer, 'skill-dup', 'references', 'rules.md'), text + '\n')
        r = run(home, proj, cat, '--areas', 'shadowed', '--api-org', '66.0')
        ok(r['inventory']['skills']['skill-dup']['state'] == 'shadowed' and r['exit_code'] == 1, 'CA-ENV-01.8',
           'different references/ with the same SKILL.md: shadowed')
        _write(os.path.join(of_project(proj), 'skill-dup', 'references', 'rules.md'), 'Old rule.\n')
        _write(os.path.join(of_project(proj), 'skill-dup', '.DS_Store'), 'x')
        r = run(home, proj, cat, '--areas', 'shadowed', '--api-org', '66.0')
        ok(r['inventory']['skills']['skill-dup']['state'] == 'present', 'CA-ENV-01.8',
           'control: identical folders (except hidden files) = present')

        # -- CA-ENV-01.9: configuration with loose types, unknown keys and a malformed catalog -----
        # The configuration uses the Spanish keys of 0.3.0 on purpose: they must work as aliases.
        home, proj, cat = scenario()
        _skill(user(home), 'skill-broken', meta='  cliTools:\n    - tool: ["sf"\n      semver: ">=2.0.0"\n')
        _write(os.path.join(proj, 'sdd.config.json'), json.dumps({
            'proyecto': 'acme', 'areas': 'api', 'odd_key': 1,
            'entorno': {'skills_extra': 'skill-broken', 'skills_excluidas': 'base-one', 'other': 2}}))
        r = run(home, proj, cat, '--api-org', '66.0')
        sk = r['inventory']['skills']
        ok('skill-api' in sk and not any('Unknown area «a»' in e for e in r['errors']), 'CA-ENV-01.9',
           '«areas» as text: a one-item list')
        ok('skill-broken' in sk and 'base-one' not in sk and not any(len(n) == 1 for n in sk), 'CA-ENV-01.9',
           'extra_skills and excluded_skills as text')
        ok(any('«odd_key»' in x for x in r['warnings']) and any('«environment.other»' in x for x in r['warnings']),
           'CA-ENV-01.9', 'unknown key: warning')
        ok(any(x.startswith('The frontmatter of skill-broken') for x in r['warnings']), 'CA-ENV-01.9',
           'frontmatter with an unclosed list: warning that names the skill')
        broken = os.path.join(tmp, 'broken-catalog.json')
        _write(broken, json.dumps({'base': {'skills': []}, 'areas': {'api': ['skill-api']}}))
        buf = io.StringIO()
        old, sys.stderr = sys.stderr, buf
        try:
            code = main(['--project', proj, '--home', home, '--catalog', broken, '--api-org', '66.0',
                         '--no-write', '--json'])
        finally:
            sys.stderr = old
        ok(code == 2 and 'area «api»' in buf.getvalue() and 'Traceback' not in buf.getvalue(), 'CA-ENV-01.9',
           'malformed catalog: exit code 2 and a message, no traceback')

        # -- Configuration, domains, recommended skills, duplicates and writing ----------------
        home, proj, cat = scenario()
        _skill(user(home), 'domain-one', meta='  domains: ["Consumer Goods"]\n')
        _skill(user(home), 'skill-rel', meta='  relatedSkills:\n    - "skill-that-does-not-exist"\n')
        _install_plugin(home, 'other-plugin', skills=['sdd-bootstrap', 'base-one'])
        _write(os.path.join(proj, 'sdd.config.json'), json.dumps({
            'project': 'acme', 'areas': ['consumer-goods', 'made-up'],
            'environment': {'inventory': 'docs/baseline/environment.json', 'extra_skills': ['skill-rel'],
                            'excluded_skills': []}}))
        r = run(home, proj, cat, '--api-org', '66.0', write=True)
        sk = r['inventory']['skills']
        ok(sk.get('domain-one', {}).get('needed_by') == ['consumer-goods'] and
           'consumer-goods' in r['areas_to_review'] and any('review it by hand' in x.lower() for x in r['warnings']),
           'domains', 'area outside the catalog: falls back to metadata.domains and is flagged for review')
        ok(any('Unknown area «made-up»' in e for e in r['errors']), 'domains', 'unknown area = error')
        ok(sk.get('skill-rel', {}).get('needed_by') == ['extra'] and
           any('skill-that-does-not-exist' in x for x in r['warnings']), 'config',
           'extra_skills and relatedSkills warning')
        ok(any(x.startswith('base-one duplicated') for x in r['warnings']) and
           any('There is another skill called sdd-bootstrap' in x for x in r['warnings']), 'config',
           'standalone/plugin duplicates and a method name in another plugin')
        ok(sk['sdd-bootstrap']['layer'] == 'plugin:sdd-salesforce', 'config', 'method skills from their plugin')
        md = os.path.join(proj, 'docs', 'baseline', 'environment-%s.md' % r['date'])
        js = os.path.join(proj, 'docs', 'baseline', 'environment.json')
        inv = _read_json(js) if os.path.isfile(js) else {}
        ok(os.path.isfile(md) and SOURCE_OF_TRUTH_NOTE in open(md, encoding='utf-8').read() and
           list(inv) == ['generated', 'areas', 'skills', 'agents', 'tools', 'org_api', 'org'] and
           set(inv['skills']['base-one']) == {'state', 'layer', 'path', 'version', 'needed_by'},
           'outputs', 'writes environment-<date>.md with the note and environment.json with the fixed format')
        _write(os.path.join(proj, 'sdd.config.json'),
               json.dumps({'areas': [], 'environment': {'excluded_skills': ['base-one']}}))
        r = run(home, proj, cat, '--api-org', '66.0')
        ok('base-one' not in r['inventory']['skills'] and any('Excluded' in x for x in r['warnings']), 'config',
           'excluded_skills')
        # «metodo» is the Spanish key of 0.3.0: with it, the inventory keeps its Spanish path.
        for cfg, fname in (({'metodo': {'version': '0.3.0'}}, 'entorno.json'), ({'method': {}}, 'environment.json'),
                           ({'metodo': {'vocabulary': 'en'}}, 'environment.json')):
            home, proj, cat = scenario()
            _write(os.path.join(proj, 'sdd.config.json'), json.dumps(dict(cfg, areas=[])))
            r = run(home, proj, cat, '--api-org', '66.0', write=True)
            ok([os.path.basename(f) for f in r['files'] if f.endswith('.json')] == [fname] and
               [os.path.basename(f).split('-')[0] for f in r['files'] if f.endswith('.md')] == [fname.split('.')[0]],
               'CA-VOC-01.2', "the inventory and the report go to the paths of the project's vocabulary (%s)" % fname)
        _write(os.path.join(proj, 'sdd.config.json'), json.dumps({'areas': [], 'method': {'vocabulary': 'fr'}}))
        try:
            run(home, proj, cat, '--api-org', '66.0')
            raised = False
        except UsageError as e:
            raised = 'method.vocabulary' in str(e)
        ok(raised, 'CA-VOC-01.5', 'unknown vocabulary: usage error (exit code 2)')
        # The Spanish area IDs of 0.2 and 0.3, in sdd.config.json or in --areas, are the current ones.
        real = os.path.join(os.path.dirname(os.path.abspath(__file__)), CATALOG_NAME)
        _write(os.path.join(proj, 'sdd.config.json'), json.dumps({'metodo': {}, 'areas': ['voz', 'integracion']}))
        r1 = run(home, proj, real, '--api-org', '66.0')
        r2 = run(home, proj, real, '--api-org', '66.0', '--areas', 'voz,integracion')
        ok(all(r['inventory']['areas'] == ['voice', 'integration'] and not any('Unknown area' in e for e in r['errors'])
               for r in (r1, r2)), 'CA-VOC-01.2', 'Spanish area IDs of 0.3.0 are read as the current ones')

        # -- CA-ENV-02.1: the plugin the script runs from counts, even if it is not installed ---
        home, proj, cat = scenario()
        env = Environment(proj, home, own_plugin=True)
        if env.own:
            ok(env.plugin_ok(env.own[0]) and any(c.kind == 'plugin' and c.plugin == env.own[0]
                                                 for c in env.copies.get('sdd-method', [])),
               'CA-ENV-02.1', 'the own plugin (%s %s) makes its skills present' % env.own[:2])
        else:
            ok(True, 'CA-ENV-02.1', 'the script does not run from a plugin: not tested')

        # -- CA-NAV-01.2: browser in a UI area; CA-LIG-01.5: in light, gaps are warnings ---------
        ok(my_domain_of('https://acme-dev-ed.develop.my.salesforce.com') == 'acme-dev-ed' and
           my_domain_of('https://ACME--uat.sandbox.my.salesforce.com/') == 'acme--uat' and my_domain_of('') is None,
           'CA-NAV-01.3', 'My Domain name from instanceUrl')
        home, proj, cat = scenario()
        r = run(home, proj, cat, '--areas', 'ui', '--api-org', '66.0')
        ok(r['exit_code'] == 0 and 'browser' not in r['inventory'] and
           any(w.startswith('Browser: the project has UI areas') for w in r['warnings']), 'CA-NAV-01.2',
           'a 0.4 project (no environment.browser) with a UI area: a warning, exit code 0 (review round 14, F-002)')
        _write(os.path.join(proj, 'sdd.config.json'), json.dumps({'environment': {'browser': True}}))
        r = run(home, proj, cat, '--areas', 'ui', '--api-org', '66.0')
        ok(r['exit_code'] == 1 and any('.mcp.json' in e and '--add-missing' in e for e in r['errors']) and
           any('install-browser chromium' in e for e in r['errors']), 'CA-NAV-01.2',
           'UI area without .mcp.json or Chromium: two errors with the command that fixes each one')
        _write(os.path.join(proj, '.mcp.json'), json.dumps({'mcpServers': {'playwright': {
            'command': 'npx', 'args': ['-y', '@playwright/mcp@0.0.1', '--browser', 'chromium']}}}))
        os.makedirs(os.path.join(playwright_cache(home, True), 'chromium-1'))
        r = run(home, proj, cat, '--areas', 'ui', '--api-org', '66.0')
        ok(r['exit_code'] == 0 and r['inventory']['browser']['mcp_json'] == 'present' and
           r['inventory']['browser']['chromium'] == 'present', 'CA-NAV-01.2', 'control: with both, exit code 0')
        h2, p2, c2 = scenario()
        r = run(h2, p2, c2, '--areas', 'agentforce,tools', '--api-org', '66.0')
        ok('browser' not in r['inventory'] and not any(w.startswith('Browser') for w in r['warnings']), 'CA-NAV-01.2',
           'without a UI area or .mcp.json, the browser is not checked')
        home, proj, cat = scenario()
        _write(os.path.join(proj, 'sdd.config.json'), json.dumps({'environment': {'browser': False}}))
        r = run(home, proj, cat, '--areas', 'ui', '--api-org', '66.0')
        ok(r['exit_code'] == 0 and not any('Browser' in e for e in r['errors']), 'CA-NAV-01.2',
           'environment.browser false: not required')
        _write(os.path.join(proj, 'sdd.config.json'), json.dumps({'method': {'profile': 'light'},
                                                                  'environment': {'browser': True}}))
        r = run(home, proj, cat, '--areas', 'ui')
        ok(r['exit_code'] == 0 and not r['errors'] and r['light'] and
           sum(w.startswith('Gap (light profile') for w in r['warnings']) >= 3, 'CA-LIG-01.5',
           'light: the browser gaps and the unchecked API are warnings, exit code 0')
        _write(os.path.join(proj, 'sdd.config.json'), json.dumps({'method': {'profile': 'full'},
                                                                  'environment': {'browser': True}}))
        r = run(home, proj, cat, '--areas', 'ui')
        ok(r['exit_code'] == 1 and len(r['errors']) >= 3, 'CA-LIG-01.5', 'control: in full they are errors')
        js = os.path.join(proj, 'docs', 'baseline', 'environment.json')
        _write(os.path.join(proj, 'sdd.config.json'), json.dumps({'org_alias': 'acme-demo'}))
        _write(js, json.dumps({'org': {'alias': 'acme-demo', 'my_domain': 'acme-dev-ed'}}))
        r = run(home, proj, cat, '--areas', 'ui', '--api-org', '66.0', write=True)
        ok(_read_json(js)['org']['my_domain'] == 'acme-dev-ed', 'CA-NAV-01.3',
           'without a new query, the My Domain of the previous inventory is kept')
        _write(os.path.join(proj, 'sdd.config.json'), json.dumps({'org_alias': 'other-demo'}))
        r = run(home, proj, cat, '--areas', 'ui', '--api-org', '66.0', write=True)
        ok(_read_json(js)['org']['my_domain'] is None, 'CA-NAV-01.3',
           'with another org_alias, the previous My Domain is not kept (review round 14, F-004)')

        # -- Org safety ------------------------------------------------------------------------
        home, proj, cat = scenario()
        before = len(COMMANDS_RUN)
        r = run(home, proj, cat, '--query-org')
        ok(any('org_alias' in e for e in r['errors']) and
           not any('org' in c for c in COMMANDS_RUN[before:]), 'orgs',
           '--query-org without org_alias: error and no command against an org')
        ok(not any('org' in c for c in COMMANDS_RUN[initial_log:]), 'orgs',
           'no sf org command in the whole self-test (%d commands, all --version)'
           % (len(COMMANDS_RUN) - initial_log))
    finally:
        os.environ['PATH'] = original_path
        shutil.rmtree(tmp, ignore_errors=True)

    failures = [x for x in results if not x[0]]
    out.write('\nSelf-test: %d/%d passed.\n' % (len(results) - len(failures), len(results)))
    return 1 if failures else 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parser():
    p = argparse.ArgumentParser(
        prog='check-environment.py',
        description='Checks the Salesforce skills, tools and org API that an sdd-salesforce project needs, and '
                    'writes the inventory to docs/baseline/.')
    p.add_argument('--project', help='project folder (default: the current one)')
    p.add_argument('--areas', help='comma-separated areas; they replace those of sdd.config.json')
    p.add_argument('--catalog', help='path to %s (default: next to the script or in ../assets/)' % CATALOG_NAME)
    p.add_argument('--home', help='folder that acts as $HOME (for tests)')
    p.add_argument('--api-org', help='org API version, e.g. 66.0 (the org is not queried)')
    p.add_argument('--query-org', action='store_true',
                   help='reads the API with sf org display --target-org <org_alias of sdd.config.json> --json')
    p.add_argument('--quick', action='store_true',
                   help='base and areas only; prints, writes nothing and exits with 0 even with gaps')
    p.add_argument('--no-write', action='store_true', help='does not write docs/baseline/')
    p.add_argument('--json', action='store_true', help='JSON output on stdout')
    p.add_argument('--self-test', action='store_true', help='runs the self-tests with simulated layers')
    p.add_argument('--validate-catalog', metavar='SF_SKILLS_DIR',
                   help='checks that every skill in the catalog exists in that sf-skills folder')
    return p


def main(argv=None):
    args = _parser().parse_args(V.argv(sys.argv[1:] if argv is None else argv))
    try:
        if args.self_test:
            return self_test(sys.stdout)
        if args.validate_catalog:
            path = args.catalog or _default_catalog()
            if not path:
                raise UsageError('Catalog not found (pass it with --catalog).')
            home = os.path.abspath(os.path.expanduser(args.home)) if args.home else os.path.expanduser('~')
            return validate_catalog(path, os.path.abspath(args.validate_catalog), home, sys.stdout)
        res = check(args)
    except UsageError as e:
        sys.stderr.write('check-environment: %s\n' % e)
        return 2
    if args.json:
        sys.stdout.write(json_output(res) + '\n')
    else:
        print_text(res, sys.stdout)
    return res['exit_code']


if __name__ == '__main__':
    sys.exit(main())
