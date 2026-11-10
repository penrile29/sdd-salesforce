"""Vocabulary of sdd-salesforce: the only place where the Spanish contract of projects from 0.2 and 0.3 lives.

- Configuration keys are English. The Spanish keys of a 0.2/0.3 sdd.config.json are accepted as aliases at every
  level (normalize). If a section is present in both languages («method» and «metodo»), both are merged key by key;
  where both have the same key with different values, the English one wins, with a warning.
- Each project has one document vocabulary, «en» or «es»: the headings, fields, labels, states, tags and paths that
  check-traceability reads. method.vocabulary sets it; without it, a configuration with «metodo» (what bootstrap wrote
  in 0.2 and 0.3) is «es», also if an English «method» was added next to it, and anything else is «en».
- The «es» vocabulary is exactly the one of 0.3.0, so those projects keep working unchanged.

Standard library only (Python 3.9). Imported by the checks of sdd-method and by the hooks.
"""

import copy

VOCABULARIES = ("en", "es")

# Spanish key → English key, at any level of sdd.config.json.
KEYS = {
    "proyecto": "project", "metodo": "method", "aprobador": "approver", "autonomia": "autonomy",
    "vocabulario": "vocabulary", "idioma": "language",
    "entorno": "environment", "inventario": "inventory", "skills_extra": "extra_skills",
    "skills_excluidas": "excluded_skills",
    "trazabilidad": "traceability",
    "rutas": "paths", "pasos": "steps", "fichas": "step_reports", "validaciones_previas": "prior_validations",
    "recorrido_demo": "demo_walkthrough", "excluir": "exclude",
    "requisito": "requirement", "ca": "ac", "paso": "step", "paso_ejemplo": "step_example",
    "dependencia_externa": "external_dependency",
    "fin_requisitos": "requirements_end", "prioridad": "priority", "prioridad_critica": "critical_priority",
    "campos": "fields", "depende": "depends", "cumple": "satisfies", "prueba": "test_first", "paralelo": "parallel",
    "tamano": "size",
    "secciones": "sections", "exclusiones": "exclusions", "pasos_sin_ca": "steps_without_ac",
    "casos_de_ficha": "report_cases", "ambitos": "scopes",
    "marcadores": "markers", "para_cerrar": "to_close", "salvo": "except", "fin_cumple": "satisfies_end",
    "verificaciones": "verifications", "etiqueta": "label", "tipo": "type",
    "tipos": "types", "modo": "mode", "fuentes": "sources", "campo": "field", "nombres": "names", "donde": "where",
    "con": "with", "cierre": "closing",
    "paso_cierre_demo": "demo_closing_step", "negacion": "negation", "frases": "phrases", "marcas": "marks",
    "estados_evidencia": "evidence_states", "seccion": "section", "columna_estado": "state_column",
    "integrado": "integrated", "no_integrado": "not_integrated",
    "tamanos": "sizes", "regla_tamano": "size_rule", "por_ca": "per_ac", "registro": "change_log",
    "etiquetas": "tags",
}

# Maps whose keys are names chosen by the project (types, sizes), not configuration keys: they are not translated.
NAME_MAPS = {("traceability", "types"), ("traceability", "sizes"), ("traceability", "size_rule", "per_ac")}

# Spanish value → English value, by the (English) key that holds it.
VALUES = {
    "autonomy": {"estricta": "strict", "critico": "critical"},
    "mode": {"clases": "classes", "fuentes": "sources", "ficha": "report", "revision": "review",
             "validaciones": "validations"},
    "field": {"depende": "depends", "cumple": "satisfies", "prueba": "test_first", "paralelo": "parallel",
              "tamano": "size"},
}

AUTONOMIES = ("strict", "critical")

# Area IDs of the catalog (skills-by-area.json) that were Spanish in 0.2 and 0.3.
AREAS = {"sitio-lwr": "lwr-site", "canales-mensajeria": "messaging-channels", "voz": "voice", "integracion": "integration",
         "modelo-datos": "data-model", "seguridad-acceso": "access-security", "analitica": "analytics"}

# Interview answers of bootstrap.py (sdd-bootstrap) as 0.2 and 0.3 wrote them: Spanish key → English key. Their
# autonomy values use VALUES["autonomy"] and their areas, AREAS. «perfil» (the light profile) was retired in 0.2.
ANSWER_KEYS = {"proyecto": "project", "cliente": "client", "caducidad": "expiry", "aprobador": "approver",
               "autonomia": "autonomy", "fuentes_cliente": "client_sources", "solo_interno": "internal_only",
               "canales": "channels", "fecha": "date", "idioma": "language", "perfil": "profile"}

# Seed decision that bootstrap generated in 0.2 and 0.3 (knowledge/decisions/<date>-<name>).
LEGACY_SEED = "001_adoptar-sdd-salesforce.md"

# Inventory written by check-environment and read by check-traceability: a 0.3.0 inventory is Spanish.
INVENTORY_KEYS = {"estado": "state", "agentes": "agents"}
INVENTORY_STATES = {"presente": "present", "ausente": "missing", "tapada": "shadowed"}
INVENTORY_PATH = {"en": "docs/baseline/environment.json", "es": "docs/baseline/entorno.json"}
REPORT_NAME = {"en": "environment-%s.md", "es": "entorno-%s.md"}  # the dated report next to the inventory


def _normalize(obj, path, warnings):
    if isinstance(obj, list):
        return [_normalize(v, path, warnings) for v in obj]
    if not isinstance(obj, dict):
        return obj
    names = path in NAME_MAPS
    out, origin = {}, {}
    # English keys first, so that they win over their Spanish alias.
    for k in sorted(obj, key=lambda x: x in KEYS and not names):
        v = obj[k]
        en = k if (names or str(k).startswith("_")) else KEYS.get(k, k)
        if en in out:
            alias = _normalize(v, path + (en,), warnings)
            if isinstance(out[en], dict) and isinstance(alias, dict):
                # Both sections are kept, key by key: the English one wins only where both have the same key.
                _merge(out[en], alias, path + (en,), origin[en], k, warnings)
            elif isinstance(alias, dict) and not isinstance(out[en], dict):
                warnings.append("config: %s is not an object; %s is used"
                                % (".".join(path + (origin[en],)), ".".join(path + (k,))))
                out[en], origin[en] = alias, k
            else:
                warnings.append("config: %s and %s are the same key; %s wins"
                                % (".".join(path + (origin[en],)), ".".join(path + (k,)), origin[en]))
            continue
        v = _normalize(v, path + (en,), warnings)
        if not names and isinstance(v, str) and v in VALUES.get(en, {}):
            v = VALUES[en][v]
        if path == () and en == "areas":
            v = areas(v)
        out[en], origin[en] = v, k
    return out


def _merge(target, alias, path, en_key, es_key, warnings):
    """Adds to target (the English section) what only its Spanish alias has; a key in both keeps the English value."""
    for k, v in alias.items():
        if k not in target:
            target[k] = v
        elif isinstance(target[k], dict) and isinstance(v, dict):
            _merge(target[k], v, path + (k,), en_key, es_key, warnings)
        elif target[k] != v:
            warnings.append("config: %s.%s is in «%s» and in «%s» with different values; the one in «%s» wins"
                            % (".".join(path), k, en_key, es_key, en_key))


def areas(v):
    """Area IDs with the Spanish ones of 0.2 and 0.3 changed to the current ones (a text or a list, as in the config)."""
    if isinstance(v, str):
        return AREAS.get(v, v)
    if isinstance(v, list):
        return [AREAS.get(a, a) if isinstance(a, str) else a for a in v]
    return v


def normalize(raw):
    """(configuration with English keys and values, warnings). raw is not modified."""
    warnings = []
    if not isinstance(raw, dict):
        return {}, warnings
    return _normalize(copy.deepcopy(raw), (), warnings), warnings


def vocabulary(raw):
    """(«en» or «es», error or None) of a configuration as read from sdd.config.json, before normalize()."""
    raw = raw if isinstance(raw, dict) else {}
    for key in ("method", "metodo"):
        m = raw.get(key)
        if isinstance(m, dict):
            v = m.get("vocabulary", m.get("vocabulario"))
            if v is not None:
                if v in VOCABULARIES:
                    return v, None
                return "en", "method.vocabulary: «%s» is not valid (valid: %s)" % (v, ", ".join(VOCABULARIES))
    # A 0.2/0.3 project keeps «metodo»: it stays «es» even if an English «method» is added next to it.
    if isinstance(raw.get("metodo"), dict):
        return "es", None
    return "en", None


# Options of the scripts in 0.2 and 0.3, which the documents of those projects still give.
FLAGS = {"--autoprueba": "--self-test", "--autopruebas": "--self-test", "--proyecto": "--project", "--paso": "--step",
         "--sin-revision": "--no-review", "--grafo": "--graph", "--validar-catalogo": "--validate-catalog",
         "--catalogo": "--catalog", "--consultar-org": "--query-org", "--rapido": "--quick", "--no-escribir": "--no-write",
         "--destino": "--target", "--respuestas": "--answers", "--simular": "--dry-run", "--anadir": "--add-missing",
         "--sustituir-readme": "--replace-readme"}

# Names of 0.2 and 0.3 that the documents of those projects still cite, and the name that replaces each one.
LEGACY_NAMES = [("sdd-metodo", "sdd-method"), ("sdd-ayuda", "sdd-help"), ("check-entorno.py", "check-environment.py"),
                ("check-trazabilidad.py", "check-traceability.py"), ("arrancar.py", "bootstrap.py"),
                ("reglas.md", "rules.md"), ("comunicacion.md", "communication.md"), ("orquestador.md", "orchestrator.md"),
                ("brief-autor.md", "author-brief.md"), ("skills-por-area.json", "skills-by-area.json")]

# Terms of the method core and of the plugin's (English) templates that have another name in a 0.2/0.3 project, besides
# those of the document vocabularies (legacy_terms() adds them).
_LEGACY_EXTRA = [("Change queue", "Cola de cambios"), ("## Verified with", "## Verificado con"),
                 ("[PENDING: Q-NN]", "[PENDIENTE: Q-NN]"), ("docs/client/", "docs/cliente/"),
                 ("environment-<date>.md", "entorno-<fecha>.md"),
                 ("docs/baseline/environment.json", "docs/baseline/entorno.json"), ("method.autonomy", "metodo.autonomia"),
                 ("method.language", "metodo.idioma"), ("method.approver", "metodo.aprobador")]


def _pairs(en, es):
    """(en, es) pairs of the text leaves that differ between two vocabularies with the same shape."""
    if isinstance(en, dict) and isinstance(es, dict):
        return [p for k in en if k in es for p in _pairs(en[k], es[k])]
    if isinstance(en, list) and isinstance(es, list) and len(en) == len(es):
        return [p for a, b in zip(en, es) for p in _pairs(a, b)]
    if isinstance(en, str) and isinstance(es, str) and en != es:
        return [(en, es)]
    return []


def _label(pattern):
    """A verification label as a person writes it («report of W0.n (Vn)»), from its pattern."""
    return pattern.replace("(W0\\.\\d+)", "W0.n").replace("\\(V\\d+\\)", "(Vn)").replace("\\.", ".")


def legacy_terms():
    """Every token that the checks read, or that the core and templates name, with its name in a 0.2/0.3 project."""
    en, es = TRACEABILITY["en"], TRACEABILITY["es"]
    out = [("AC-", "CA-"), ("# Part 2", "# Parte 2"), ("Priority:", "Prioridad:"), ("Status:", "Estado:"),
           ("## " + en["status"]["section"], "## " + es["status"]["section"]),
           ("integrated / closed", "integrado / cerrado")]
    for key in ("fields", "sections", "markers", "evidence_states", "change_log", "paths"):
        out += _pairs(en[key], es[key])
    # The negation phrases do not line up one to one (English has the contracted forms too).
    out += [("does not cover", "no cubre"), ("not covered", "sin cubrir"), ("does not verify", "no verifica"),
            (GRAMMAR["en"]["no_reason"], GRAMMAR["es"]["no_reason"])]
    out += [(_label(a["label"]), _label(b["label"])) for a, b in zip(en["verifications"], es["verifications"])
            if a["label"] != b["label"]]
    out += _LEGACY_EXTRA
    seen, unique = set(), []
    for x in out:
        if x not in seen:
            seen.add(x)
            unique.append(x)
    return unique

# The generated CLAUDE.md of 0.2 and 0.3 tells Claude to stop if it does not see «[sdd-salesforce …] Proyecto sdd» in
# its context: in those projects the hook's project line keeps that label.
LEGACY_PROJECT_LABEL = "Proyecto sdd"


def argv(args):
    """The command line with the options of 0.2 and 0.3 changed to the current ones («--paso W1.1», «--paso=W1.1»)."""
    out = []
    for a in args:
        flag, eq, value = a.partition("=")
        out.append(FLAGS[flag] + eq + value if flag in FLAGS else a)
    return out


def inventory_state(v):
    return INVENTORY_STATES.get(v, v)


def inventory(data):
    """An inventory with English keys and states, whichever language wrote it."""
    if not isinstance(data, dict):
        return data
    out = dict((INVENTORY_KEYS.get(k, k), v) for k, v in data.items())
    skills = out.get("skills")
    if isinstance(skills, dict):
        out["skills"] = dict((n, dict((INVENTORY_KEYS.get(k, k), inventory_state(x) if INVENTORY_KEYS.get(k, k)
                                       == "state" else x) for k, x in e.items()) if isinstance(e, dict) else e)
                             for n, e in skills.items())
    return out


# --- Document vocabulary of check-traceability --------------------------------------------------------------------

_TYPES_COMMON = {
    "apex": {"mode": "classes", "sources": ["force-app/**/*Test.cls", "force-app-*/**/*Test.cls"],
             "field": "test_first", "names": "`([A-Z][A-Za-z0-9_]*Test)`", "with": "Apex"},
    "jest": {"mode": "sources", "sources": ["force-app/**/__tests__/*.test.js", "force-app-*/**/__tests__/*.test.js"]},
    "react": {"mode": "sources", "sources": ["force-app/**/uiBundles/**/*.test.ts", "force-app/**/uiBundles/**/*.test.tsx",
                                             "force-app/**/uiBundles/**/*.test.js",
                                             "force-app-*/**/uiBundles/**/*.test.ts",
                                             "force-app-*/**/uiBundles/**/*.test.tsx",
                                             "force-app-*/**/uiBundles/**/*.test.js"]},
    "agent": {"mode": "sources", "sources": ["tests/**/*.yaml", "tests/**/*.yml"]},
}


def _types(where, report, prior):
    t = copy.deepcopy(_TYPES_COMMON)
    for name in ("apex", "jest", "react", "agent"):
        t[name]["where"] = where[name]
    t[report] = {"mode": "report"}
    t["demo"] = {"mode": "report", "closing": True}
    t[prior] = {"mode": "validations"}
    t["review"] = {"mode": "review"}
    return t


TRACEABILITY = {
    "es": {
        "paths": {
            "specs": ["knowledge/specs/*.md"],
            "traceability": "docs/delivery-plan/traceability.md",
            "steps": ["docs/delivery-plan/implementation/*.md"],
            "integration": "docs/delivery-plan/integration.md",
            "status": "docs/delivery-plan/status.md",
            "step_reports": "docs/delivery-plan/fichas",
            "prior_validations": "docs/delivery-plan/w0-validaciones.md",
            "demo_walkthrough": "docs/delivery-plan/recorrido-demo.md",
            "reviews": "reviews",
            "exclude": ["node_modules"],
        },
        "ids": {
            "requirement": "R-[A-Z]+-\\d+",
            "ac": "CA-[A-Z]+-(?P<req>\\d+)\\.(?P<num>\\d+)",
            "step": "W(?P<oleada>\\d+)\\.(?P<num>\\d+)",
            "step_example": "Wn.m",
            "external_dependency": "P-\\d+",
        },
        "spec": {"requirements_end": "# Parte 2", "priority": "Prioridad: (P\\d)", "critical_priority": "P0"},
        "fields": {"depends": "Depende de", "satisfies": "Cumple", "test_first": "Prueba primero",
                   "parallel": "Paralelo con", "size": "Tamaño", "skill": "Skill"},
        "sections": {"exclusions": "Exclusiones", "steps_without_ac": "Pasos sin CA",
                     "report_cases": "Casos de verificación", "scopes": "Ámbitos"},
        "markers": {"to_close": "para cerrar", "except": "salvo",
                    "satisfies_end": ["**Fuente:**", "valida el diseño de"]},
        "verifications": [
            {"label": "test de Apex", "type": "apex"},
            {"label": "permitido/denegado con `runAs`", "type": "apex"},
            {"label": "Jest", "type": "jest"},
            {"label": "tests de la app React", "type": "react"},
            {"label": "caso de `sf agent test`", "type": "agent"},
            {"label": "preview con traza y SOQL", "type": "ficha"},
            {"label": "preview con traza", "type": "ficha"},
            {"label": "registro en el org", "type": "ficha"},
            {"label": "Login History", "type": "ficha"},
            {"label": "prueba con dos usuarios", "type": "ficha"},
            {"label": "`sf agent validate`", "type": "ficha"},
            {"label": "paso de demo", "type": "demo"},
            {"label": "ficha de (W0\\.\\d+) \\(V\\d+\\)", "type": "previa"},
            {"label": "revisión de código", "type": "review"},
            {"label": "revisión del `\\.agent`", "type": "review"},
            {"label": "revisión de la plantilla", "type": "review"},
        ],
        "types": _types({"apex": "un *Test.cls", "jest": "un test de Jest", "react": "un test de la app React",
                         "agent": "un caso YAML de tests/"}, "ficha", "previa"),
        "demo_closing_step": None,
        "negation": {"phrases": ["no cubre", "sin cubrir", "no verifica"], "marks": ["TODO"]},
        "evidence_states": ["prevista", "existe", "pasa"],
        "status": {
            "section": "Pasos",
            "state_column": 4,
            "integrated": "\\b(?:integrad[oa]|cerrad[oa])\\b",
            "not_integrated": "\\b(?:sin|no)\\s+(?:integrar|integrad[oa]|cerrar|cerrad[oa])\\b",
        },
        "sizes": {"S": 1, "M": 2, "L": 3},
        "size_rule": {"per_ac": {"M": 4, "L": 11}, "external_dependency": "L"},
        "change_log": {"section": "Registro de cambios", "tags": ["release-*", "diseno-aprobado"]},
    },
    "en": {
        "paths": {
            "specs": ["knowledge/specs/*.md"],
            "traceability": "docs/delivery-plan/traceability.md",
            "steps": ["docs/delivery-plan/implementation/*.md"],
            "integration": "docs/delivery-plan/integration.md",
            "status": "docs/delivery-plan/status.md",
            "step_reports": "docs/delivery-plan/step-reports",
            "prior_validations": "docs/delivery-plan/w0-validations.md",
            "demo_walkthrough": "docs/delivery-plan/demo-walkthrough.md",
            "reviews": "reviews",
            "exclude": ["node_modules"],
        },
        "ids": {
            "requirement": "R-[A-Z]+-\\d+",
            "ac": "AC-[A-Z]+-(?P<req>\\d+)\\.(?P<num>\\d+)",
            "step": "W(?P<wave>\\d+)\\.(?P<num>\\d+)",
            "step_example": "Wn.m",
            "external_dependency": "P-\\d+",
        },
        "spec": {"requirements_end": "# Part 2", "priority": "Priority: (P\\d)", "critical_priority": "P0"},
        "fields": {"depends": "Depends on", "satisfies": "Satisfies", "test_first": "Test first",
                   "parallel": "Parallel with", "size": "Size", "skill": "Skill"},
        "sections": {"exclusions": "Exclusions", "steps_without_ac": "Steps without AC",
                     "report_cases": "Verification cases", "scopes": "Scopes"},
        "markers": {"to_close": "to close", "except": "except",
                    "satisfies_end": ["**Source:**", "validates the design of"]},
        "verifications": [
            {"label": "Apex test", "type": "apex"},
            {"label": "allowed/denied with `runAs`", "type": "apex"},
            {"label": "Jest", "type": "jest"},
            {"label": "React app tests", "type": "react"},
            {"label": "`sf agent test` case", "type": "agent"},
            {"label": "preview with trace and SOQL", "type": "report"},
            {"label": "preview with trace", "type": "report"},
            {"label": "record in the org", "type": "report"},
            {"label": "Login History", "type": "report"},
            {"label": "two-user test", "type": "report"},
            {"label": "`sf agent validate`", "type": "report"},
            {"label": "demo step", "type": "demo"},
            {"label": "report of (W0\\.\\d+) \\(V\\d+\\)", "type": "prior"},
            {"label": "code review", "type": "review"},
            {"label": "review of the `\\.agent`", "type": "review"},
            {"label": "template review", "type": "review"},
        ],
        "types": _types({"apex": "a *Test.cls", "jest": "a Jest test", "react": "a React app test",
                         "agent": "a YAML case in tests/"}, "report", "prior"),
        "demo_closing_step": None,
        "negation": {"phrases": ["does not cover", "doesn't cover", "not covered", "does not verify",
                                 "doesn't verify"], "marks": ["TODO"]},
        "evidence_states": ["planned", "exists", "passes"],
        "status": {
            "section": "Steps",
            "state_column": 4,
            "integrated": "\\b(?:integrated|closed)\\b",
            "not_integrated": "\\b(?:not|un)\\s*(?:yet\\s+)?(?:integrated|closed)\\b",
        },
        "sizes": {"S": 1, "M": 2, "L": 3},
        "size_rule": {"per_ac": {"M": 4, "L": 11}, "external_dependency": "L"},
        "change_log": {"section": "Change log", "tags": ["release-*", "design-approved"]},
    },
}

# What check-traceability reads that is not configurable: the words of an AC list («02.1 a 02.3 y 02.5»), the
# requirement state that is not a contract change, and an exclusion without a reason.
GRAMMAR = {
    "es": {"and": "y", "to": "a", "state_field": "Estado", "no_reason": "sin motivo", "priority_field": "Prioridad"},
    "en": {"and": "and", "to": "to", "state_field": "Status", "no_reason": "no reason", "priority_field": "Priority"},
}


def traceability_defaults(vocab):
    return copy.deepcopy(TRACEABILITY[vocab])
