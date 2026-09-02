#!/usr/bin/env python3
"""
Rewire catalog templates to the platform database contract (communal DBs).

Why: on communal-equipped shared zones kubero-server provisions Postgres /
MariaDB as LOGICAL databases (user + database = `<namespace>_<instance>`,
random password, host = the `<instance>` pooler Service) and Valkey as an
ephemeral instance. The platform injects the connection contract into every
app that references the add-on:

  Cluster (CNPG)   PGHOST PGPORT PGUSER PGDATABASE PGPASSWORD(secretKeyRef)
  MariaDB          MYSQL_HOST MYSQL_PORT MYSQL_USER MYSQL_DATABASE MYSQL_PASSWORD(secretKeyRef)
  Valkey           REDISHOST REDISPORT REDIS_URL

Templates that hardcode `user:pass@{{KUBERO_APP_NAME}}-postgresql-rw` dial a
Service and credentials that no longer exist. Kubernetes expands `$(NAME)`
references in env values from variables defined earlier in the container env
(kubero-server dependency-orders the final list), so every template env var
that carried a DB host / user / database / password / URL literal is rewritten
to compose from the injected contract, e.g.

  DATABASE_URL: postgresql://$(PGUSER):$(PGPASSWORD)@$(PGHOST):$(PGPORT)/$(PGDATABASE)
  DB_HOST: $(MYSQL_HOST)            DB_PASSWORD: $(MYSQL_PASSWORD)
  REDIS_URL: redis://$(REDISHOST):$(REDISPORT)/0

The add-on CR blocks are left untouched: they are the server-mode fallback
(zones without a communal server, dedicated clusters) and the source the
platform derives the contract from there.

Edits are line-level inside `spec.envVars` so formatting/comments survive.
Multi-line (block scalar) values are reported, never edited.

Usage:
  scripts/migrate-to-communal-db-env.py            # rewrite in place, print report
  scripts/migrate-to-communal-db-env.py --check    # lint only (CI): exit 1 on residual literals
  scripts/migrate-to-communal-db-env.py --dry-run  # report what would change
  scripts/migrate-to-communal-db-env.py nextcloud plausible   # subset
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SERVICES = ROOT / "services"
TOKEN = "{{KUBERO_APP_NAME}}"

CONTRACT = {
    "pg": ["PGHOST", "PGPORT", "PGUSER", "PGDATABASE", "PGPASSWORD"],
    "mysql": ["MYSQL_HOST", "MYSQL_PORT", "MYSQL_USER", "MYSQL_DATABASE", "MYSQL_PASSWORD"],
    "redis": ["REDISHOST", "REDISPORT", "REDIS_URL"],
}
VARS = {
    "pg": dict(host="$(PGHOST)", port="$(PGPORT)", user="$(PGUSER)", db="$(PGDATABASE)", password="$(PGPASSWORD)"),
    "mysql": dict(host="$(MYSQL_HOST)", port="$(MYSQL_PORT)", user="$(MYSQL_USER)", db="$(MYSQL_DATABASE)", password="$(MYSQL_PASSWORD)"),
    "redis": dict(host="$(REDISHOST)", port="$(REDISPORT)"),
}
DEFAULT_PORT = {"pg": "5432", "mysql": "3306", "redis": "6379"}

# Env var NAME classifiers. A standalone literal is only rewritten when the
# name says what the value is AND the value equals what the add-on CR bakes.
ENGINE_HINT = {
    "pg": re.compile(r"(^|_)(PG\w*|POSTGRES(QL)?\w*|PSQL)(_|$)|^PG"),
    "mysql": re.compile(r"(^|_)(MYSQL|MARIADB|MARIA)(_|$)"),
    "redis": re.compile(r"(^|_)(REDIS\w*|VALKEY|CACHE)(_|$)"),
}
GENERIC_DB_HINT = re.compile(r"(^|_)(DB|DATABASE|SQL|DBNAME|DBUSER|DBPASS|DBHOST|DBPORT)(_|$)|(^|_)DB\w+$")
SEMANTIC = [
    ("password", re.compile(r"(PASS(WORD)?|PWD|SECRET)(_|$)")),
    ("user", re.compile(r"(USER(NAME)?|LOGIN|UID)(_|$)")),
    ("db", re.compile(r"(DATABASE|DBNAME|DB_NAME|NAME|_DB|DB|SCHEMA)$")),
    ("host", re.compile(r"(HOST(NAME)?|SERVER|ADDR(ESS)?)(_|$)")),
    ("port", re.compile(r"PORT(_|$)")),
]


@dataclass
class Engine:
    kind: str  # pg | mysql | redis
    instance: str
    db: str | None = None
    user: str | None = None
    password: str | None = None
    admin_user: str | None = None
    admin_password: str | None = None

    def literals(self, sem: str) -> set[str]:
        if sem == "password":
            return {v for v in (self.password, self.admin_password) if v}
        if sem == "user":
            return {v for v in (self.user, self.admin_user) if v}
        if sem == "db":
            return {self.db} if self.db else set()
        return set()


@dataclass
class Report:
    slug: str
    file: str
    changed: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    residual: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)


def secret_passwords(defs: dict) -> dict[str, str | None]:
    out: dict[str, str | None] = {}
    for d in defs.values():
        if isinstance(d, dict) and d.get("kind") == "Secret":
            name = (d.get("metadata") or {}).get("name")
            if name:
                out[name] = (d.get("stringData") or {}).get("password")
    return out


def engines_of(spec: dict) -> list[Engine]:
    out: list[Engine] = []
    for a in spec.get("addons") or []:
        if not isinstance(a, dict):
            continue
        kind = a.get("kind")
        defs = a.get("resourceDefinitions") or {}
        main = next((d for d in defs.values() if isinstance(d, dict) and d.get("kind") == kind), None)
        if not main:
            continue
        inst = str((main.get("metadata") or {}).get("name") or "")
        if not inst:
            continue
        s = main.get("spec") or {}
        pw = secret_passwords(defs)
        if kind == "Cluster":
            initdb = ((s.get("bootstrap") or {}).get("initdb") or {})
            out.append(
                Engine(
                    "pg",
                    inst,
                    db=initdb.get("database"),
                    user=initdb.get("owner"),
                    password=pw.get((initdb.get("secret") or {}).get("name")),
                    admin_user="postgres",
                    admin_password=pw.get((s.get("superuserSecret") or {}).get("name")),
                )
            )
        elif kind == "MariaDB":
            out.append(
                Engine(
                    "mysql",
                    inst,
                    db=s.get("database"),
                    user=s.get("username"),
                    password=pw.get((s.get("passwordSecretKeyRef") or {}).get("name")),
                    admin_user="root",
                    admin_password=pw.get((s.get("rootPasswordSecretKeyRef") or {}).get("name")),
                )
            )
        elif kind == "Valkey":
            out.append(Engine("redis", inst))
    return out


def host_alternation(e: Engine, slug: str) -> str:
    names = {e.instance, e.instance.replace(TOKEN, slug)}
    if TOKEN not in e.instance:
        # token-less CR names get app-prefixed at deploy (uniquifyTemplate), so
        # env literals legitimately spell them `{{KUBERO_APP_NAME}}-<name>`.
        names |= {f"{TOKEN}-{e.instance}", f"{slug}-{e.instance}"}
    alts: list[str] = []
    for n in names:
        q = re.escape(n)
        if e.kind == "pg":
            alts += [q + r"-rw", q + r"-ro", q + r"-r", q + r"-any"]
        elif e.kind == "mysql":
            alts += [q + r"-primary", q]
        else:
            alts += [r"rfr-" + q + r"-(?:readwrite|readonly|\d+)", r"rfs-" + q, q]
    # longest first so `foo-rw` wins over `foo`
    alts.sort(key=len, reverse=True)
    return "(?:" + "|".join(alts) + ")"


NOT_HOSTCHAR = r"(?![A-Za-z0-9.-])"
URL_RE_TPL = (
    r"(?P<scheme>[A-Za-z][A-Za-z0-9+.-]*://)"
    r"(?:(?P<user>[^:@/\s'\"]+)(?::(?P<pass>[^@/\s'\"]*))?@)?"
    r"(?P<host>{HOST})(?::(?P<port>\d+))?"
    r"(?P<path>/[^?\s'\"#]*)?(?P<q>\?[^\s'\"#]*)?"
)
DSN_RE_TPL = (
    r"(?P<user>[^:@\s'\"(]+):(?P<pass>[^@\s'\"]*)@tcp\((?P<host>{HOST})(?::(?P<port>\d+))?\)"
    r"/(?P<db>[^?\s'\"]*)(?P<q>\?[^\s'\"]*)?"
)


def rewrite_value(value: str, e: Engine, slug: str) -> str:
    host = host_alternation(e, slug)
    v = VARS[e.kind]

    def url_sub(m: re.Match) -> str:
        scheme = m.group("scheme")
        creds = ""
        if m.group("user") is not None and e.kind != "redis":
            creds = f"{v['user']}:{v['password']}@"
        path = m.group("path") or ""
        q = m.group("q") or ""
        if e.kind == "redis":
            # keep the logical DB index (/0, /1 …); default to none
            tail = path if re.fullmatch(r"/\d*", path or "") else ""
            if tail == "/":
                tail = ""
            return f"{scheme}{creds}{v['host']}:{v['port']}{tail}{q}"
        return f"{scheme}{creds}{v['host']}:{v['port']}/{v['db']}{q}"

    def dsn_sub(m: re.Match) -> str:
        q = m.group("q") or ""
        return f"{v['user']}:{v['password']}@tcp({v['host']}:{v['port']})/{v['db']}{q}"

    v2 = re.sub(URL_RE_TPL.format(HOST=host), url_sub, value)
    if e.kind == "mysql":
        v2 = re.sub(DSN_RE_TPL.format(HOST=host), dsn_sub, v2)
    # host:port and bare host anywhere in the string
    v2 = re.sub(host + r":" + DEFAULT_PORT[e.kind] + NOT_HOSTCHAR, f"{v['host']}:{v['port']}", v2)
    v2 = re.sub(host + NOT_HOSTCHAR, v['host'], v2)
    return v2


def engine_for_name(name: str, engines: list[Engine]) -> Engine | None:
    for kind in ("pg", "mysql", "redis"):
        if ENGINE_HINT[kind].search(name):
            cands = [e for e in engines if e.kind == kind]
            return cands[0] if len(cands) == 1 else None
    if GENERIC_DB_HINT.search(name):
        sql = [e for e in engines if e.kind in ("pg", "mysql")]
        return sql[0] if len(sql) == 1 else None
    return None


def semantic_of(name: str) -> str | None:
    for sem, rx in SEMANTIC:
        if rx.search(name):
            return sem
    return None


def rewrite_standalone(name: str, value: str, engines: list[Engine], slug: str) -> str | None:
    e = engine_for_name(name, engines)
    sem = semantic_of(name)
    if not e or not sem:
        return None
    v = VARS[e.kind]
    if sem == "port":
        return v["port"] if value == DEFAULT_PORT[e.kind] else None
    if sem == "host":
        return None  # handled by host regex
    if e.kind == "redis":
        return None  # no user/db/password in the Valkey contract
    if value in e.literals(sem):
        return v[sem]
    return None


def yaml_scalar(text: str):
    """Parse the RHS of `value: <text>` as a YAML scalar; None if not a plain string."""
    try:
        parsed = yaml.safe_load(text) if text.strip() else ""
    except Exception:
        return None
    return parsed


def quote(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


ENV_START = re.compile(r"^  envVars:\s*$")
ENV_ITEM = re.compile(r"^  - name: (.+?)\s*$")
ENV_VALUE = re.compile(r"^(    value: ?)(.*)$")
NEXT_KEY = re.compile(r"^  [A-Za-z]")


def process_file(path: Path, slug: str, apply: bool) -> Report | None:
    text = path.read_text(encoding="utf-8")
    try:
        doc = yaml.safe_load(text)
    except Exception as exc:
        r = Report(slug, path.name)
        r.skipped.append(f"YAML parse failed: {exc}")
        return r
    spec = (doc or {}).get("spec") or {}
    engines = engines_of(spec)
    if not engines:
        return None
    rep = Report(slug, path.name)
    contract_names = {n for e in engines for n in CONTRACT[e.kind]}

    lines = text.split("\n")
    out: list[str] = []
    i = 0
    in_env = False
    env_names: set[str] = set()
    drop_until_next_item = False
    while i < len(lines):
        line = lines[i]
        if not in_env:
            out.append(line)
            if ENV_START.match(line):
                in_env = True
            i += 1
            continue
        # inside envVars
        if NEXT_KEY.match(line) or (line and not line.startswith(" ")):
            in_env = False
            drop_until_next_item = False
            out.append(line)
            i += 1
            continue
        m_item = ENV_ITEM.match(line)
        if m_item:
            name = yaml_scalar(m_item.group(1))
            name = str(name) if name is not None else m_item.group(1)
            if name in contract_names:
                # platform injects this exact var; a template literal would
                # override it. Drop the whole entry.
                rep.removed.append(name)
                drop_until_next_item = True
                i += 1
                continue
            drop_until_next_item = False
            env_names.add(name)
            cur_name = name
            out.append(line)
            i += 1
            continue
        if drop_until_next_item:
            i += 1
            continue
        m_val = ENV_VALUE.match(line)
        if not m_val:
            out.append(line)
            i += 1
            continue
        prefix, rest = m_val.group(1), m_val.group(2)
        stripped = rest.strip()
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        is_block = stripped in ("|", ">", "|-", ">-", "|+", ">+", "") or (
            nxt.startswith("      ") and not nxt.lstrip().startswith(("- ", "valueFrom"))
        )
        if is_block:
            rep.skipped.append(f"{cur_name}: multi-line value not rewritten")
            out.append(line)
            i += 1
            continue
        parsed = yaml_scalar(stripped)
        if isinstance(parsed, bool) or parsed is None:
            out.append(line)
            i += 1
            continue
        value = str(parsed)
        new = value
        for e in engines:
            new = rewrite_value(new, e, slug)
        if new == value:
            alt = rewrite_standalone(cur_name, value, engines, slug)
            if alt is not None:
                new = alt
        if new != value:
            rep.changed.append(f"{cur_name}: {value!r} -> {new!r}")
            out.append(prefix.rstrip() + " " + quote(new))
        else:
            out.append(line)
        i += 1

    new_text = "\n".join(out)

    # ---- verification on the rewritten env ---------------------------------
    try:
        new_doc = yaml.safe_load(new_text)
    except Exception as exc:
        rep.skipped.append(f"REWRITE PRODUCED INVALID YAML: {exc}")
        return rep
    env = (new_doc.get("spec") or {}).get("envVars") or []
    names = {str(x.get("name")) for x in env if isinstance(x, dict)} | contract_names
    for x in env:
        if not isinstance(x, dict) or not isinstance(x.get("value"), str):
            continue
        for ref in re.findall(r"\$\(([A-Za-z_][A-Za-z0-9_.-]*)\)", x["value"].replace("$$", "")):
            if ref not in names:
                rep.unresolved.append(f"{x.get('name')} references $({ref})")
        for e in engines:
            if re.search(host_alternation(e, slug) + NOT_HOSTCHAR, x["value"]):
                rep.residual.append(f"{x.get('name')}: still names {e.instance} host: {x['value']!r}")
            sem = semantic_of(str(x.get("name")))
            if sem in ("password",) and e.kind != "redis" and x["value"] in e.literals(sem) and engine_for_name(str(x.get("name")), engines) is e:
                rep.residual.append(f"{x.get('name')}: still carries the baked {e.kind} password")

    if apply and new_text != text:
        path.write_text(new_text, encoding="utf-8")
    return rep


def main(argv: list[str]) -> int:
    check = "--check" in argv
    dry = "--dry-run" in argv
    only = [a for a in argv if not a.startswith("--")]
    apply = not (check or dry)
    reports: list[Report] = []
    for d in sorted(SERVICES.iterdir()):
        if not d.is_dir() or (only and d.name not in only):
            continue
        for fn in ("app.yaml", "app.ha.yaml"):
            p = d / fn
            if p.is_file():
                r = process_file(p, d.name, apply)
                if r:
                    reports.append(r)

    n_files = len(reports)
    n_changed = sum(1 for r in reports if r.changed or r.removed)
    n_edits = sum(len(r.changed) + len(r.removed) for r in reports)
    bad = [r for r in reports if r.residual or r.unresolved or any("INVALID" in s for s in r.skipped)]
    skipped = [r for r in reports if r.skipped]

    if check:
        # lint mode: in-place files must already be clean
        problems = [r for r in reports if r.changed or r.removed or r.residual or r.unresolved]
        for r in problems:
            for c in r.changed:
                print(f"  {r.slug}/{r.file}: would rewrite {c}")
            for c in r.removed:
                print(f"  {r.slug}/{r.file}: overrides platform var {c}")
            for c in r.residual + r.unresolved:
                print(f"  {r.slug}/{r.file}: {c}")
        if problems:
            print(f"\nFAIL — {len(problems)} template file(s) not on the platform DB env contract")
            return 1
        print(f"OK — {n_files} DB-backed template files on the platform DB env contract")
        return 0

    verb = "would change" if dry else "changed"
    print(f"{n_files} DB-backed template files scanned; {verb} {n_changed} files, {n_edits} env entries\n")
    if "--verbose" in argv or only:
        for r in reports:
            if r.changed or r.removed:
                print(f"== {r.slug}/{r.file}")
                for c in r.changed:
                    print(f"   ~ {c}")
                for c in r.removed:
                    print(f"   - removed {c} (platform-injected)")
    if bad:
        print("\nNEEDS MANUAL REVIEW:")
        for r in bad:
            for c in r.residual + r.unresolved + [s for s in r.skipped if "INVALID" in s]:
                print(f"  {r.slug}/{r.file}: {c}")
    if skipped:
        print("\nSKIPPED (multi-line values / parse):")
        for r in skipped:
            for c in r.skipped:
                if "INVALID" not in c:
                    print(f"  {r.slug}/{r.file}: {c}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
