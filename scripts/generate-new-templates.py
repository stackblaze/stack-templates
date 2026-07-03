#!/usr/bin/env python3
"""Generate kubero templates for 26 high-value new apps identified from Railway catalog."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICES = ROOT / "services"
SPECS = Path(__file__).resolve().parent / "_specs"
BASE_RAW = "https://raw.githubusercontent.com/stackblaze/stack-templates/main/services"
TODAY = "2026-06-13T00:00:00Z"

# ─── Addon YAML helpers ──────────────────────────────────────────────────────

def pg_addon(slug: str, db_size: str = "5Gi") -> str:
    return f"""\
  - displayName: PostgreSQL (CloudNativePG)
    env: []
    icon: /img/addons/pgsql.svg
    id: kubero-operator
    kind: Cluster
    resourceDefinitions:
      Cluster:
        apiVersion: postgresql.cnpg.io/v1
        kind: Cluster
        metadata:
          name: {slug}-postgresql
        spec:
          instances: 1
          imageName: ghcr.io/cloudnative-pg/postgresql:16
          primaryUpdateStrategy: unsupervised
          storage:
            storageClass: smart
            size: {db_size}
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
            limits:
              cpu: '1'
              memory: 1Gi
          bootstrap:
            initdb:
              database: {slug}
              owner: {slug}
              secret:
                name: {slug}-postgresql-app
              postInitApplicationSQL:
                - GRANT ALL ON SCHEMA public TO {slug}
                - GRANT CREATE ON SCHEMA public TO {slug}
                - ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO {slug}
          enableSuperuserAccess: true
          superuserSecret:
            name: {slug}-postgresql-superuser
      superuserSecret:
        apiVersion: v1
        kind: Secret
        metadata:
          name: {slug}-postgresql-superuser
        type: kubernetes.io/basic-auth
        stringData:
          username: postgres
          password: {slug}
      appUserSecret:
        apiVersion: v1
        kind: Secret
        metadata:
          name: {slug}-postgresql-app
        type: kubernetes.io/basic-auth
        stringData:
          username: {slug}
          password: {slug}"""


def valkey_addon(slug: str) -> str:
    return f"""\
  - displayName: Valkey
    env: []
    icon: /img/addons/redis.svg
    id: kubero-operator
    kind: Valkey
    resourceDefinitions:
      Valkey:
        apiVersion: rds.valkey.buf.red/v1alpha1
        kind: Valkey
        metadata:
          name: {slug}-cache
        spec:
          version: '8.0'
          arch: replica
          replicas:
            shards: 1
            replicasOfShard: 1
          access:
            serviceType: ClusterIP
          storage:
            capacity: 1Gi
            storageClassName: fast
          resources:
            requests:
              cpu: 50m
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 256Mi"""


def mariadb_addon(slug: str, db_size: str = "5Gi") -> str:
    return f"""\
  - displayName: MariaDB
    env: []
    icon: /img/addons/mysql.svg
    id: kubero-operator
    kind: MariaDB
    resourceDefinitions:
      MariaDB:
        apiVersion: k8s.mariadb.com/v1alpha1
        kind: MariaDB
        metadata:
          name: {slug}-db
        spec:
          metrics:
            enabled: true
          rootPasswordSecretKeyRef:
            name: {slug}-db-root
            key: password
          database: {slug}
          username: {slug}
          passwordSecretKeyRef:
            name: {slug}-db-app
            key: password
          storage:
            size: {db_size}
            storageClassName: fast
          replicas: 1
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
            limits:
              cpu: '1'
              memory: 1Gi
      rootSecret:
        apiVersion: v1
        kind: Secret
        metadata:
          name: {slug}-db-root
        type: Opaque
        stringData:
          password: {slug}
      appSecret:
        apiVersion: v1
        kind: Secret
        metadata:
          name: {slug}-db-app
        type: Opaque
        stringData:
          password: {slug}"""


# ─── YAML generator ──────────────────────────────────────────────────────────

def yaml_str(v: str) -> str:
    """Wrap a string value for YAML annotation if it contains special chars."""
    if any(c in v for c in ('"', "'", ':', '#', '{', '}', '[', ']', '|', '>', '!')):
        escaped = v.replace("'", "''")
        return f"'{escaped}'"
    return v


def env_block(envs: list[dict]) -> str:
    if not envs:
        return "  envVars: []\n"
    lines = ["  envVars:\n"]
    for e in envs:
        lines.append(f"  - name: {e['name']}\n")
        val = str(e['value'])
        if any(c in val for c in ('"', ':', '#', '{', '}', '[', ']', '|', '>', '!')):
            val = "'" + val.replace("'", "''") + "'"
        lines.append(f"    value: {val}\n")
    return "".join(lines)


def volumes_block(vols: list[dict]) -> str:
    if not vols:
        return "  extraVolumes: []\n"
    lines = ["  extraVolumes:\n"]
    for v in vols:
        lines.append("  - accessModes:\n    - ReadWriteOnce\n")
        lines.append("    emptyDir: false\n")
        lines.append(f"    mountPath: {v['mountPath']}\n")
        lines.append(f"    name: {v['name']}\n")
        lines.append(f"    size: {v['size']}\n")
    return "".join(lines)


def cmd_block(cmd: list[str]) -> str:
    if not cmd:
        return ""
    lines = ["    command:\n"]
    for c in cmd:
        lines.append(f"    - {c}\n")
    return "".join(lines)


def resources_block(res: dict | None) -> str:
    if not res:
        return ""
    r = res.get("requests", {})
    l = res.get("limits", {})
    return (
        "  resources:\n"
        f"    requests:\n"
        f"      cpu: {r.get('cpu', '250m')}\n"
        f"      memory: {r.get('memory', '512Mi')}\n"
        f"    limits:\n"
        f"      cpu: '{l.get('cpu', '1')}'\n"
        f"      memory: {l.get('memory', '1Gi')}\n"
    )


def health_block(h: dict | None) -> str:
    if not h:
        return ""
    return (
        "  healthcheck:\n"
        "    enabled: true\n"
        f"    path: {h.get('path', '/')}\n"
        f"    startupSeconds: {h.get('startupSeconds', 300)}\n"
        "    timeoutSeconds: 5\n"
        "    periodSeconds: 10\n"
    )


def generate_app_yaml(app: dict) -> str:
    slug = app["slug"]
    title = yaml_str(app["title"])
    desc = yaml_str(app["description"])
    installation = yaml_str(app["installation"])
    source = app["source"]
    website = app["website"]
    cats = json.dumps(app["categories"])
    links = json.dumps(app.get("links", [source]))
    icon = f"{BASE_RAW}/{slug}/icon.png"
    img = app["image"]

    addons_parts = []
    for at in app.get("addons_type", []):
        if at == "pg":
            addons_parts.append(pg_addon(slug, app.get("pg_size", "5Gi")))
        elif at == "valkey":
            addons_parts.append(valkey_addon(slug))
        elif at == "mariadb":
            addons_parts.append(mariadb_addon(slug, app.get("db_size", "5Gi")))

    if addons_parts:
        addons_yaml = "  addons:\n" + "\n".join(addons_parts) + "\n"
    else:
        addons_yaml = "  addons: []\n"

    lines = [
        "apiVersion: application.kubero.dev/v1alpha1\n",
        "kind: KuberoApp\n",
        "metadata:\n",
        f"  name: {slug}\n",
        "  annotations:\n",
        "    kubero.dev/template.architecture: '[]'\n",
        f"    kubero.dev/template.description: {desc}\n",
        f"    kubero.dev/template.icon: {icon}\n",
        f"    kubero.dev/template.installation: {installation}\n",
        f"    kubero.dev/template.links: '{links}'\n",
        "    kubero.dev/template.screenshots: '[]'\n",
        f"    kubero.dev/template.source: {source}\n",
        f"    kubero.dev/template.categories: '{cats}'\n",
        f"    kubero.dev/template.title: {title}\n",
        f"    kubero.dev/template.website: {website}\n",
        "  labels:\n",
        "    manager: kubero\n",
        "spec:\n",
        f"  name: {slug}\n",
        "  deploymentstrategy: docker\n",
        addons_yaml,
        env_block(app.get("envVars", [])),
        volumes_block(app.get("extraVolumes", [])),
        "  cronjobs: []\n",
        "  web:\n",
        "    replicaCount: 1\n",
        "  worker:\n",
        "    replicaCount: 0\n",
        resources_block(app.get("resources")),
        health_block(app.get("healthcheck")),
        "  image:\n",
        f"    containerPort: '{img['containerPort']}'\n",
        "    pullPolicy: Always\n",
        f"    repository: {img['repository']}\n",
        f"    tag: {img['tag']}\n",
        cmd_block(img.get("command", [])),
    ]
    return "".join(lines)


def generate_spec_json(app: dict) -> dict:
    slug = app["slug"]
    return {
        "slug": slug,
        "title": app["title"],
        "description": app["description"],
        "source": app["source"],
        "website": app["website"],
        "icon": f"{BASE_RAW}/{slug}/icon.png",
        "categories": app["categories"],
        "installation": app["installation"],
        "screenshots": [],
        "links": app.get("links", [app["source"]]),
        "license": app.get("license", "Other"),
        "spdx_id": app.get("spdx_id", "NOASSERTION"),
        "stars": app.get("stars", 0),
        "language": app.get("language", ""),
        "image": app["image"],
        "envVars": app.get("envVars", []),
        "addons": app.get("addons", []),
        "extraVolumes": app.get("extraVolumes", []),
    }


def index_entry(app: dict) -> dict:
    slug = app["slug"]
    img = app["image"]
    return {
        "name": slug,
        "description": app["description"],
        "source": app["source"],
        "icon": f"{BASE_RAW}/{slug}/icon.png",
        "website": app["website"],
        "installation": "",
        "architecture": [],
        "categories": app["categories"],
        "screenshots": [],
        "links": app.get("links", []),
        "addons": [],
        "stars": app.get("stars", 0),
        "forks": 0,
        "watchers": app.get("stars", 0),
        "issues": 0,
        "last_updated": TODAY,
        "last_pushed": TODAY,
        "created_at": "2020-01-01T00:00:00Z",
        "size": 1000,
        "language": app.get("language", ""),
        "gitops": False,
        "template": f"{BASE_RAW}/{slug}/app.yaml",
        "status": "active",
        "license": app.get("license", "Other"),
        "spdx_id": app.get("spdx_id", "NOASSERTION"),
        "dirname": slug,
        "deploymentTypes": [
            {"id": "standard", "label": "Standard", "default": True,
             "template": f"{BASE_RAW}/{slug}/app.yaml"},
        ],
    }


# ─── App definitions ─────────────────────────────────────────────────────────

APPS: list[dict] = [

    # ── AI / LLM ────────────────────────────────────────────────────────────

    {
        "slug": "ollama",
        "title": "Ollama",
        "description": "Run large language models locally — Llama 3, Mistral, Gemma, Phi, and 100+ models via a simple OpenAI-compatible REST API.",
        "source": "https://github.com/ollama/ollama",
        "website": "https://ollama.com",
        "categories": ["ai", "utilities", "development"],
        "license": "MIT",
        "spdx_id": "MIT",
        "stars": 120000,
        "language": "Go",
        "links": ["https://github.com/ollama/ollama", "https://ollama.com/library"],
        "image": {"repository": "ollama/ollama", "tag": "latest", "containerPort": "11434", "command": []},
        "addons_type": [],
        "addons": [],
        "envVars": [
            {"name": "OLLAMA_HOST", "value": "0.0.0.0"},
            {"name": "OLLAMA_ORIGINS", "value": "*"},
            {"name": "OLLAMA_KEEP_ALIVE", "value": "5m"},
        ],
        "extraVolumes": [{"mountPath": "/root/.ollama", "name": "ollama-models", "size": "20Gi"}],
        "resources": {"requests": {"cpu": "500m", "memory": "2Gi"}, "limits": {"cpu": "4", "memory": "8Gi"}},
        "healthcheck": {"path": "/", "startupSeconds": 60},
        "installation": "Ollama runs a local LLM inference server. After deploy, pull a model: POST /api/pull with {\"model\":\"llama3.2\"}. Then chat at POST /api/chat or use the OpenAI-compatible endpoint at /v1. GPU is unavailable on CPU nodes — use quantised models (llama3.2:3b, phi3:mini) for acceptable speed. Increase the volume before pulling large models (7B ~4GB, 70B ~40GB). Pair with Open WebUI for a browser chat interface.",
    },

    {
        "slug": "open-webui",
        "title": "Open WebUI",
        "description": "ChatGPT-style web interface for Ollama and any OpenAI-compatible API — supports RAG, web search, image generation, and multi-model chat.",
        "source": "https://github.com/open-webui/open-webui",
        "website": "https://openwebui.com",
        "categories": ["ai", "utilities"],
        "license": "MIT",
        "spdx_id": "MIT",
        "stars": 136000,
        "language": "Python",
        "links": ["https://docs.openwebui.com/"],
        "image": {"repository": "ghcr.io/open-webui/open-webui", "tag": "main", "containerPort": "8080", "command": []},
        "addons_type": ["pg"],
        "addons": [{"type": "postgres", "name": "open-webui", "db": "open-webui", "user": "open-webui", "password": "open-webui"}],
        "envVars": [
            {"name": "DATABASE_URL", "value": "postgresql://open-webui:open-webui@open-webui-postgresql-rw:5432/open-webui"},
            {"name": "WEBUI_SECRET_KEY", "value": "change-me-to-a-random-32char-secret"},
            {"name": "WEBUI_URL", "value": "{{KUBERO_APP_URL}}"},
            {"name": "OLLAMA_BASE_URL", "value": ""},
            {"name": "OPENAI_API_KEY", "value": ""},
            {"name": "OPENAI_API_BASE_URL", "value": "https://api.openai.com/v1"},
            {"name": "ENABLE_SIGNUP", "value": "true"},
        ],
        "extraVolumes": [{"mountPath": "/app/backend/data", "name": "open-webui-data", "size": "5Gi"}],
        "resources": {"requests": {"cpu": "250m", "memory": "512Mi"}, "limits": {"cpu": "2", "memory": "2Gi"}},
        "healthcheck": {"path": "/health", "startupSeconds": 120},
        "installation": "Set OLLAMA_BASE_URL to your Ollama instance (e.g. http://ollama:11434) OR set OPENAI_API_KEY for cloud LLMs. WEBUI_SECRET_KEY must be changed before use. On first visit create the admin account. The Postgres add-on persists users, chats, and settings. RAG document storage uses the open-webui-data volume.",
    },

    {
        "slug": "litellm",
        "title": "LiteLLM",
        "description": "LLM proxy and gateway — unified OpenAI-compatible API for 100+ providers including OpenAI, Anthropic, Gemini, Ollama, and Bedrock with cost tracking and rate limiting.",
        "source": "https://github.com/BerriAI/litellm",
        "website": "https://litellm.ai",
        "categories": ["ai", "development", "utilities"],
        "license": "MIT",
        "spdx_id": "MIT",
        "stars": 24000,
        "language": "Python",
        "links": ["https://docs.litellm.ai/"],
        "image": {"repository": "ghcr.io/berriai/litellm", "tag": "main-latest", "containerPort": "4000", "command": []},
        "addons_type": ["pg"],
        "addons": [{"type": "postgres", "name": "litellm", "db": "litellm", "user": "litellm", "password": "litellm"}],
        "envVars": [
            {"name": "DATABASE_URL", "value": "postgresql://litellm:litellm@litellm-postgresql-rw:5432/litellm"},
            {"name": "LITELLM_MASTER_KEY", "value": "sk-change-me"},
            {"name": "STORE_MODEL_IN_DB", "value": "True"},
            {"name": "LITELLM_LOG", "value": "INFO"},
            {"name": "UI_USERNAME", "value": "admin"},
            {"name": "UI_PASSWORD", "value": "change-me"},
        ],
        "extraVolumes": [],
        "resources": {"requests": {"cpu": "250m", "memory": "512Mi"}, "limits": {"cpu": "2", "memory": "2Gi"}},
        "healthcheck": {"path": "/health/liveliness", "startupSeconds": 120},
        "installation": "LiteLLM provides a single OpenAI-compatible endpoint that proxies to any LLM provider. Set LITELLM_MASTER_KEY (must start with sk-). Add models via the /ui dashboard (login with UI_USERNAME/UI_PASSWORD) or via the /models API. The Postgres add-on persists model configs, spend logs, and keys. Connect any OpenAI SDK client to {{KUBERO_APP_URL}}/v1 with Authorization: Bearer sk-change-me.",
    },

    {
        "slug": "langfuse",
        "title": "Langfuse",
        "description": "Open-source LLM observability platform — traces, evals, prompt management, datasets, and cost analytics for AI applications.",
        "source": "https://github.com/langfuse/langfuse",
        "website": "https://langfuse.com",
        "categories": ["ai", "monitoring", "development"],
        "license": "MIT",
        "spdx_id": "MIT",
        "stars": 13000,
        "language": "TypeScript",
        "links": ["https://langfuse.com/docs"],
        "image": {"repository": "langfuse/langfuse", "tag": "3", "containerPort": "3000", "command": []},
        "addons_type": ["pg"],
        "addons": [{"type": "postgres", "name": "langfuse", "db": "langfuse", "user": "langfuse", "password": "langfuse"}],
        "envVars": [
            {"name": "DATABASE_URL", "value": "postgresql://langfuse:langfuse@langfuse-postgresql-rw:5432/langfuse"},
            {"name": "NEXTAUTH_URL", "value": "{{KUBERO_APP_URL}}"},
            {"name": "NEXTAUTH_SECRET", "value": "change-me-to-random-32char-string"},
            {"name": "SALT", "value": "change-me-to-random-string"},
            {"name": "ENCRYPTION_KEY", "value": "0000000000000000000000000000000000000000000000000000000000000000"},
            {"name": "LANGFUSE_INIT_ORG_ID", "value": "my-org"},
            {"name": "LANGFUSE_INIT_ORG_NAME", "value": "My Org"},
            {"name": "LANGFUSE_INIT_PROJECT_ID", "value": "my-project"},
            {"name": "LANGFUSE_INIT_PROJECT_NAME", "value": "My Project"},
            {"name": "LANGFUSE_INIT_USER_EMAIL", "value": "admin@example.com"},
            {"name": "LANGFUSE_INIT_USER_NAME", "value": "Admin"},
            {"name": "LANGFUSE_INIT_USER_PASSWORD", "value": "change-me"},
        ],
        "extraVolumes": [],
        "resources": {"requests": {"cpu": "250m", "memory": "512Mi"}, "limits": {"cpu": "2", "memory": "2Gi"}},
        "healthcheck": {"path": "/api/public/health", "startupSeconds": 180},
        "installation": "Change NEXTAUTH_SECRET, SALT, and ENCRYPTION_KEY to random values before use (ENCRYPTION_KEY must be a 64-char hex string). LANGFUSE_INIT_* variables seed the first org/project/user — change them or delete after first login. Instrument your app with the Langfuse SDK (pip install langfuse) and set LANGFUSE_HOST={{KUBERO_APP_URL}} in your app. The free self-hosted version includes all features.",
    },

    {
        "slug": "localai",
        "title": "LocalAI",
        "description": "Self-hosted, OpenAI-compatible REST API for running LLMs, image generation, audio transcription, and embeddings locally — no GPU required.",
        "source": "https://github.com/mudler/LocalAI",
        "website": "https://localai.io",
        "categories": ["ai", "utilities"],
        "license": "MIT",
        "spdx_id": "MIT",
        "stars": 30000,
        "language": "Go",
        "links": ["https://localai.io/basics/getting_started/"],
        "image": {"repository": "localai/localai", "tag": "latest-cpu", "containerPort": "8080", "command": []},
        "addons_type": [],
        "addons": [],
        "envVars": [
            {"name": "MODELS_PATH", "value": "/models"},
            {"name": "CONTEXT_SIZE", "value": "512"},
            {"name": "THREADS", "value": "4"},
            {"name": "DEBUG", "value": "false"},
        ],
        "extraVolumes": [{"mountPath": "/models", "name": "localai-models", "size": "20Gi"}],
        "resources": {"requests": {"cpu": "500m", "memory": "2Gi"}, "limits": {"cpu": "4", "memory": "8Gi"}},
        "healthcheck": {"path": "/readyz", "startupSeconds": 180},
        "installation": "LocalAI provides an OpenAI-compatible API for local models. Use the latest-cpu tag (no GPU). Download a model by placing a GGUF file in the /models volume, or use the gallery API to install models: POST /models/apply with {\"id\":\"gpt4all-j\"}. Set THREADS to the number of CPU cores available. Use the /v1 endpoints with any OpenAI client library — just point the base URL at {{KUBERO_APP_URL}}/v1.",
    },

    {
        "slug": "anythingllm",
        "title": "AnythingLLM",
        "description": "All-in-one private AI workspace — RAG, multi-user chat, web browsing, custom agents, and 100+ LLM integrations with a clean browser UI.",
        "source": "https://github.com/Mintplex-Labs/anything-llm",
        "website": "https://anythingllm.com",
        "categories": ["ai", "utilities", "documentation"],
        "license": "MIT",
        "spdx_id": "MIT",
        "stars": 42000,
        "language": "JavaScript",
        "links": ["https://docs.anythingllm.com/"],
        "image": {"repository": "mintplexlabs/anythingllm", "tag": "latest", "containerPort": "3001", "command": []},
        "addons_type": [],
        "addons": [],
        "envVars": [
            {"name": "STORAGE_DIR", "value": "/app/server/storage"},
            {"name": "JWT_SECRET", "value": "change-me-to-random-secret"},
            {"name": "SIG_KEY", "value": "change-me-to-32char-string"},
            {"name": "SIG_SALT", "value": "change-me-to-32char-string"},
            {"name": "SERVER_PORT", "value": "3001"},
            {"name": "DISABLE_TELEMETRY", "value": "true"},
        ],
        "extraVolumes": [{"mountPath": "/app/server/storage", "name": "anythingllm-storage", "size": "10Gi"}],
        "resources": {"requests": {"cpu": "250m", "memory": "512Mi"}, "limits": {"cpu": "2", "memory": "2Gi"}},
        "healthcheck": {"path": "/api/ping", "startupSeconds": 120},
        "installation": "Change JWT_SECRET, SIG_KEY, and SIG_SALT to random strings before use. On first load, set up the admin account. Connect your LLM in Settings (supports Ollama, OpenAI, Anthropic, and more). Upload documents to workspaces for RAG. AnythingLLM uses SQLite by default (stored in the volume) — no database add-on required.",
    },

    # ── Auth / SSO ───────────────────────────────────────────────────────────

    {
        "slug": "authentik",
        "title": "Authentik",
        "description": "Open-source identity provider — SSO, OAuth2, SAML, LDAP, MFA, and social login. Self-hosted alternative to Okta and Auth0.",
        "source": "https://github.com/goauthentik/authentik",
        "website": "https://goauthentik.io",
        "categories": ["security", "development", "utilities"],
        "license": "MIT",
        "spdx_id": "MIT",
        "stars": 16000,
        "language": "Python",
        "links": ["https://docs.goauthentik.io/"],
        "image": {"repository": "ghcr.io/goauthentik/server", "tag": "latest", "containerPort": "9000", "command": ["server"]},
        "addons_type": ["pg", "valkey"],
        "addons": [
            {"type": "postgres", "name": "authentik", "db": "authentik", "user": "authentik", "password": "authentik"},
            {"type": "redis", "name": "authentik"},
        ],
        "envVars": [
            {"name": "AUTHENTIK_POSTGRESQL__HOST", "value": "authentik-postgresql-rw"},
            {"name": "AUTHENTIK_POSTGRESQL__USER", "value": "authentik"},
            {"name": "AUTHENTIK_POSTGRESQL__PASSWORD", "value": "authentik"},
            {"name": "AUTHENTIK_POSTGRESQL__NAME", "value": "authentik"},
            {"name": "AUTHENTIK_REDIS__HOST", "value": "rfr-authentik-cache-readwrite"},
            {"name": "AUTHENTIK_SECRET_KEY", "value": "change-me-to-50char-random-string"},
            {"name": "AUTHENTIK_ERROR_REPORTING__ENABLED", "value": "false"},
        ],
        "extraVolumes": [
            {"mountPath": "/media", "name": "authentik-media", "size": "2Gi"},
            {"mountPath": "/templates", "name": "authentik-templates", "size": "1Gi"},
        ],
        "resources": {"requests": {"cpu": "250m", "memory": "512Mi"}, "limits": {"cpu": "2", "memory": "2Gi"}},
        "healthcheck": {"path": "/-/health/ready/", "startupSeconds": 300},
        "installation": "Change AUTHENTIK_SECRET_KEY to a 50+ character random string. The first admin account is bootstrapped via the /if/flow/initial-setup/ URL on first run. Configure OIDC/SAML applications in the Admin UI at /if/admin/. The worker (background tasks) is bundled in this image when run as 'server' — for production workloads deploy a second instance with command 'worker'.",
    },

    {
        "slug": "keycloak",
        "title": "Keycloak",
        "description": "Enterprise-grade open-source identity and access management — SSO, OAuth2, SAML, LDAP federation, MFA, and user management.",
        "source": "https://github.com/keycloak/keycloak",
        "website": "https://www.keycloak.org",
        "categories": ["security", "development", "work"],
        "license": "Apache-2.0",
        "spdx_id": "Apache-2.0",
        "stars": 24000,
        "language": "Java",
        "links": ["https://www.keycloak.org/documentation"],
        "image": {"repository": "quay.io/keycloak/keycloak", "tag": "latest", "containerPort": "8080", "command": ["start-dev"]},
        "addons_type": ["pg"],
        "addons": [{"type": "postgres", "name": "keycloak", "db": "keycloak", "user": "keycloak", "password": "keycloak"}],
        "envVars": [
            {"name": "KC_DB", "value": "postgres"},
            {"name": "KC_DB_URL", "value": "jdbc:postgresql://keycloak-postgresql-rw:5432/keycloak"},
            {"name": "KC_DB_USERNAME", "value": "keycloak"},
            {"name": "KC_DB_PASSWORD", "value": "keycloak"},
            {"name": "KC_HOSTNAME", "value": "{{KUBERO_APP_URL}}"},
            {"name": "KC_PROXY", "value": "edge"},
            {"name": "KC_HTTP_ENABLED", "value": "true"},
            {"name": "KC_BOOTSTRAP_ADMIN_USERNAME", "value": "admin"},
            {"name": "KC_BOOTSTRAP_ADMIN_PASSWORD", "value": "change-me"},
        ],
        "extraVolumes": [],
        "resources": {"requests": {"cpu": "500m", "memory": "1Gi"}, "limits": {"cpu": "2", "memory": "2Gi"}},
        "healthcheck": {"path": "/health/ready", "startupSeconds": 300},
        "installation": "Change KC_BOOTSTRAP_ADMIN_PASSWORD before first deploy. start-dev mode is used here for simplicity — for production replace with 'start' and configure proper TLS/hostname. Access the Admin Console at /admin. KC_PROXY=edge enables proxy header trust (required when running behind the kubero ingress). Create realms, clients, and users in the Admin Console.",
    },

    {
        "slug": "zitadel",
        "title": "Zitadel",
        "description": "Cloud-native identity platform — OIDC, OAuth2, SAML, passkeys, MFA, and multi-tenancy out of the box. Self-hosted alternative to Auth0.",
        "source": "https://github.com/zitadel/zitadel",
        "website": "https://zitadel.com",
        "categories": ["security", "development", "work"],
        "license": "Apache-2.0",
        "spdx_id": "Apache-2.0",
        "stars": 9000,
        "language": "Go",
        "links": ["https://zitadel.com/docs"],
        "image": {"repository": "ghcr.io/zitadel/zitadel", "tag": "stable", "containerPort": "8080", "command": ["start-from-init", "--masterkeyFromEnv"]},
        "addons_type": ["pg"],
        "addons": [{"type": "postgres", "name": "zitadel", "db": "zitadel", "user": "zitadel", "password": "zitadel"}],
        "envVars": [
            {"name": "ZITADEL_DATABASE_POSTGRES_HOST", "value": "zitadel-postgresql-rw"},
            {"name": "ZITADEL_DATABASE_POSTGRES_PORT", "value": "5432"},
            {"name": "ZITADEL_DATABASE_POSTGRES_DATABASE", "value": "zitadel"},
            {"name": "ZITADEL_DATABASE_POSTGRES_USER_USERNAME", "value": "zitadel"},
            {"name": "ZITADEL_DATABASE_POSTGRES_USER_PASSWORD", "value": "zitadel"},
            {"name": "ZITADEL_DATABASE_POSTGRES_USER_SSL_MODE", "value": "disable"},
            {"name": "ZITADEL_DATABASE_POSTGRES_ADMIN_USERNAME", "value": "postgres"},
            {"name": "ZITADEL_DATABASE_POSTGRES_ADMIN_PASSWORD", "value": "zitadel"},
            {"name": "ZITADEL_DATABASE_POSTGRES_ADMIN_SSL_MODE", "value": "disable"},
            {"name": "ZITADEL_EXTERNALDOMAIN", "value": "{{KUBERO_APP_HOST}}"},
            {"name": "ZITADEL_EXTERNALPORT", "value": "443"},
            {"name": "ZITADEL_EXTERNALSECURE", "value": "true"},
            {"name": "ZITADEL_MASTERKEY", "value": "MasterkeyNeedsToHave32Characters"},
        ],
        "extraVolumes": [],
        "resources": {"requests": {"cpu": "250m", "memory": "512Mi"}, "limits": {"cpu": "2", "memory": "1Gi"}},
        "healthcheck": {"path": "/debug/ready", "startupSeconds": 300},
        "installation": "Change ZITADEL_MASTERKEY to exactly 32 characters. Set ZITADEL_EXTERNALDOMAIN to the app hostname (without https://). ZITADEL_DATABASE_POSTGRES_ADMIN_PASSWORD must match the CNPG superuser secret (default: zitadel). On first boot Zitadel auto-migrates the database and prints the initial admin credentials to the container log — retrieve them with kubectl logs.",
    },

    # ── No-code / Low-code ───────────────────────────────────────────────────

    {
        "slug": "baserow",
        "title": "Baserow",
        "description": "Open-source no-code database and Airtable alternative — build relational databases, forms, and automations with a spreadsheet-like UI.",
        "source": "https://gitlab.com/bramw/baserow",
        "website": "https://baserow.io",
        "categories": ["data", "productivity", "work"],
        "license": "MIT",
        "spdx_id": "MIT",
        "stars": 12000,
        "language": "Python",
        "links": ["https://baserow.io/docs/index"],
        "image": {"repository": "baserow/baserow", "tag": "latest", "containerPort": "80", "command": []},
        "addons_type": ["pg", "valkey"],
        "addons": [
            {"type": "postgres", "name": "baserow", "db": "baserow", "user": "baserow", "password": "baserow"},
            {"type": "redis", "name": "baserow"},
        ],
        "envVars": [
            {"name": "DATABASE_HOST", "value": "baserow-postgresql-rw"},
            {"name": "DATABASE_PORT", "value": "5432"},
            {"name": "DATABASE_NAME", "value": "baserow"},
            {"name": "DATABASE_USER", "value": "baserow"},
            {"name": "DATABASE_PASSWORD", "value": "baserow"},
            {"name": "REDIS_HOST", "value": "rfr-baserow-cache-readwrite"},
            {"name": "REDIS_PORT", "value": "6379"},
            {"name": "BASEROW_PUBLIC_URL", "value": "{{KUBERO_APP_URL}}"},
            {"name": "SECRET_KEY", "value": "change-me-to-random-string"},
        ],
        "extraVolumes": [{"mountPath": "/baserow/media", "name": "baserow-media", "size": "10Gi"}],
        "resources": {"requests": {"cpu": "500m", "memory": "1Gi"}, "limits": {"cpu": "2", "memory": "2Gi"}},
        "healthcheck": {"path": "/api/_health/", "startupSeconds": 300},
        "installation": "Change SECRET_KEY to a random string. The all-in-one image bundles the API, web frontend, and background workers. On first visit, register an admin account. The media volume stores uploaded files and attachments. For larger deployments, switch to the distributed architecture (separate backend/frontend/worker images).",
    },

    {
        "slug": "teable",
        "title": "Teable",
        "description": "Open-source Airtable alternative built on native Postgres — spreadsheet UI over real SQL tables with automations, views, and API.",
        "source": "https://github.com/teableio/teable",
        "website": "https://teable.io",
        "categories": ["data", "productivity", "work"],
        "license": "AGPL-3.0",
        "spdx_id": "AGPL-3.0",
        "stars": 19000,
        "language": "TypeScript",
        "links": ["https://help.teable.io/"],
        "image": {"repository": "ghcr.io/teableio/teable", "tag": "latest", "containerPort": "3000", "command": []},
        "addons_type": ["pg", "valkey"],
        "addons": [
            {"type": "postgres", "name": "teable", "db": "teable", "user": "teable", "password": "teable"},
            {"type": "redis", "name": "teable"},
        ],
        "envVars": [
            {"name": "PRISMA_DATABASE_URL", "value": "postgresql://teable:teable@teable-postgresql-rw:5432/teable"},
            {"name": "BACKEND_CACHE_REDIS_URI", "value": "redis://rfr-teable-cache-readwrite:6379/0"},
            {"name": "SECRET_KEY", "value": "change-me-to-random-string"},
            {"name": "PUBLIC_ORIGIN", "value": "{{KUBERO_APP_URL}}"},
            {"name": "BACKEND_STORAGE_TYPE", "value": "local"},
            {"name": "BACKEND_LOCAL_STORAGE_PATH", "value": "/app/.teable"},
            {"name": "BACKEND_UPLOAD_FILE_SIZE_LIMIT", "value": "209715200"},
        ],
        "extraVolumes": [{"mountPath": "/app/.teable", "name": "teable-storage", "size": "10Gi"}],
        "resources": {"requests": {"cpu": "250m", "memory": "512Mi"}, "limits": {"cpu": "2", "memory": "2Gi"}},
        "healthcheck": {"path": "/health", "startupSeconds": 180},
        "installation": "Change SECRET_KEY to a random string. PUBLIC_ORIGIN must match the app URL exactly (used for OAuth callbacks and magic links). Teable stores data directly in Postgres — each table becomes a real SQL table you can query. The storage volume holds file attachments. Register on first visit to create the admin workspace.",
    },

    {
        "slug": "nocobase",
        "title": "NocoBase",
        "description": "Open-source no-code/low-code platform for building CRMs, ERPs, and internal tools with a plugin-based extensible architecture.",
        "source": "https://github.com/nocobase/nocobase",
        "website": "https://www.nocobase.com",
        "categories": ["data", "development", "productivity"],
        "license": "AGPL-3.0",
        "spdx_id": "AGPL-3.0",
        "stars": 16000,
        "language": "TypeScript",
        "links": ["https://docs.nocobase.com/"],
        "image": {"repository": "nocobase/nocobase", "tag": "latest", "containerPort": "13000", "command": []},
        "addons_type": ["pg"],
        "addons": [{"type": "postgres", "name": "nocobase", "db": "nocobase", "user": "nocobase", "password": "nocobase"}],
        "envVars": [
            {"name": "DB_DIALECT", "value": "postgres"},
            {"name": "DB_HOST", "value": "nocobase-postgresql-rw"},
            {"name": "DB_PORT", "value": "5432"},
            {"name": "DB_DATABASE", "value": "nocobase"},
            {"name": "DB_USER", "value": "nocobase"},
            {"name": "DB_PASSWORD", "value": "nocobase"},
            {"name": "APP_KEY", "value": "change-me-to-random-string"},
            {"name": "APP_PORT", "value": "13000"},
        ],
        "extraVolumes": [{"mountPath": "/app/nocobase/storage", "name": "nocobase-storage", "size": "5Gi"}],
        "resources": {"requests": {"cpu": "250m", "memory": "512Mi"}, "limits": {"cpu": "2", "memory": "2Gi"}},
        "healthcheck": {"path": "/api/app:getInfo", "startupSeconds": 300},
        "installation": "Change APP_KEY to a random string. On first load, NocoBase auto-migrates the database and shows the setup wizard. Default admin: admin@nocobase.com / admin123 (change immediately). Use the plugin manager to install additional plugins. Supports building custom data models, forms, workflows, and dashboards without code.",
    },

    {
        "slug": "pocketbase",
        "title": "PocketBase",
        "description": "Open-source Firebase alternative — realtime subscriptions, auth, file storage, and admin UI, all in a single Go binary backed by SQLite.",
        "source": "https://github.com/pocketbase/pocketbase",
        "website": "https://pocketbase.io",
        "categories": ["development", "utilities", "data"],
        "license": "MIT",
        "spdx_id": "MIT",
        "stars": 43000,
        "language": "Go",
        "links": ["https://pocketbase.io/docs/"],
        "image": {"repository": "ghcr.io/muchobien/pocketbase", "tag": "latest", "containerPort": "8090", "command": []},
        "addons_type": [],
        "addons": [],
        "envVars": [],
        "extraVolumes": [{"mountPath": "/pb/pb_data", "name": "pocketbase-data", "size": "5Gi"}],
        "resources": {"requests": {"cpu": "100m", "memory": "128Mi"}, "limits": {"cpu": "1", "memory": "512Mi"}},
        "healthcheck": {"path": "/api/health", "startupSeconds": 60},
        "installation": "PocketBase runs as a single binary with SQLite — no external database needed. Access the Admin UI at /_/ and create the admin account on first visit. Define collections (tables), set up auth providers, and configure file storage rules in the Admin UI. Use the JS/TypeScript SDK or REST API to build your frontend. All data is stored in the pocketbase-data volume.",
    },

    # ── CMS ─────────────────────────────────────────────────────────────────

    {
        "slug": "strapi",
        "title": "Strapi",
        "description": "Most popular open-source headless CMS — REST and GraphQL APIs, role-based access, media library, and a customisable admin panel.",
        "source": "https://github.com/strapi/strapi",
        "website": "https://strapi.io",
        "categories": ["cms", "development", "data"],
        "license": "MIT",
        "spdx_id": "MIT",
        "stars": 65000,
        "language": "JavaScript",
        "links": ["https://docs.strapi.io/"],
        "image": {"repository": "elestio/strapi", "tag": "latest", "containerPort": "1337", "command": []},
        "addons_type": ["pg"],
        "addons": [{"type": "postgres", "name": "strapi", "db": "strapi", "user": "strapi", "password": "strapi"}],
        "envVars": [
            {"name": "DATABASE_CLIENT", "value": "postgres"},
            {"name": "DATABASE_HOST", "value": "strapi-postgresql-rw"},
            {"name": "DATABASE_PORT", "value": "5432"},
            {"name": "DATABASE_NAME", "value": "strapi"},
            {"name": "DATABASE_USERNAME", "value": "strapi"},
            {"name": "DATABASE_PASSWORD", "value": "strapi"},
            {"name": "DATABASE_SSL", "value": "false"},
            {"name": "JWT_SECRET", "value": "change-me-jwt-secret"},
            {"name": "ADMIN_JWT_SECRET", "value": "change-me-admin-jwt-secret"},
            {"name": "APP_KEYS", "value": "key1,key2,key3,key4"},
            {"name": "API_TOKEN_SALT", "value": "change-me-token-salt"},
            {"name": "TRANSFER_TOKEN_SALT", "value": "change-me-transfer-salt"},
            {"name": "NODE_ENV", "value": "production"},
        ],
        "extraVolumes": [{"mountPath": "/srv/app/public/uploads", "name": "strapi-uploads", "size": "10Gi"}],
        "resources": {"requests": {"cpu": "250m", "memory": "512Mi"}, "limits": {"cpu": "2", "memory": "2Gi"}},
        "healthcheck": {"path": "/_health", "startupSeconds": 300},
        "installation": "Change JWT_SECRET, ADMIN_JWT_SECRET, APP_KEYS, API_TOKEN_SALT, and TRANSFER_TOKEN_SALT to unique random values. Access the Admin Panel at /admin and create the first admin user. Define Content-Types in the Content-Type Builder, then query them via REST at /api/<collection> or GraphQL at /graphql. Media uploads go to the strapi-uploads volume.",
    },

    # ── Databases ────────────────────────────────────────────────────────────

    {
        "slug": "clickhouse",
        "title": "ClickHouse",
        "description": "Column-oriented OLAP database for real-time analytics — processes billions of rows per second with sub-second query latency.",
        "source": "https://github.com/ClickHouse/ClickHouse",
        "website": "https://clickhouse.com",
        "categories": ["database", "analytics", "data"],
        "license": "Apache-2.0",
        "spdx_id": "Apache-2.0",
        "stars": 41000,
        "language": "C++",
        "links": ["https://clickhouse.com/docs/"],
        "image": {"repository": "clickhouse/clickhouse-server", "tag": "latest", "containerPort": "8123", "command": []},
        "addons_type": [],
        "addons": [],
        "envVars": [
            {"name": "CLICKHOUSE_DB", "value": "default"},
            {"name": "CLICKHOUSE_USER", "value": "admin"},
            {"name": "CLICKHOUSE_PASSWORD", "value": "change-me"},
            {"name": "CLICKHOUSE_DEFAULT_ACCESS_MANAGEMENT", "value": "1"},
        ],
        "extraVolumes": [{"mountPath": "/var/lib/clickhouse", "name": "clickhouse-data", "size": "20Gi"}],
        "resources": {"requests": {"cpu": "500m", "memory": "1Gi"}, "limits": {"cpu": "4", "memory": "8Gi"}},
        "healthcheck": {"path": "/ping", "startupSeconds": 120},
        "installation": "Change CLICKHOUSE_PASSWORD. Access the HTTP interface at port 8123 and the Play UI at /play. Connect with any ClickHouse client using host={{KUBERO_APP_HOST}}, port=443, user=admin, password=<your-password>. The native TCP port 9000 is not exposed externally — use the HTTP interface or the JDBC/ODBC drivers via HTTP. Note: ClickHouse is also available as an operator-managed add-on for higher availability.",
    },

    {
        "slug": "questdb",
        "title": "QuestDB",
        "description": "High-performance time-series database with SQL — optimised for IoT, financial, and observability data with a built-in web console.",
        "source": "https://github.com/questdb/questdb",
        "website": "https://questdb.io",
        "categories": ["database", "analytics", "data"],
        "license": "Apache-2.0",
        "spdx_id": "Apache-2.0",
        "stars": 15000,
        "language": "Java",
        "links": ["https://questdb.io/docs/"],
        "image": {"repository": "questdb/questdb", "tag": "latest", "containerPort": "9000", "command": []},
        "addons_type": [],
        "addons": [],
        "envVars": [
            {"name": "QDB_HTTP_MIN_ENABLED", "value": "true"},
            {"name": "QDB_TELEMETRY_ENABLED", "value": "false"},
        ],
        "extraVolumes": [{"mountPath": "/var/lib/questdb", "name": "questdb-data", "size": "20Gi"}],
        "resources": {"requests": {"cpu": "250m", "memory": "512Mi"}, "limits": {"cpu": "4", "memory": "4Gi"}},
        "healthcheck": {"path": "/", "startupSeconds": 120},
        "installation": "QuestDB exposes a web console at port 9000 (also accessible via {{KUBERO_APP_URL}}). Query with SQL in the web console or via the REST API at /exec?query=. The PostgreSQL wire protocol runs on port 8812 (not exposed externally). Ingest data via InfluxDB line protocol (TCP 9009) or REST. Partitioned by day/month/year for optimal time-series performance.",
    },

    {
        "slug": "timescaledb",
        "title": "TimescaleDB",
        "description": "Time-series database built on Postgres — hypertables, compression, continuous aggregates, and full SQL compatibility for metrics and events.",
        "source": "https://github.com/timescale/timescaledb",
        "website": "https://www.timescale.com",
        "categories": ["database", "analytics", "data"],
        "license": "Apache-2.0",
        "spdx_id": "Apache-2.0",
        "stars": 18000,
        "language": "C",
        "links": ["https://docs.timescale.com/"],
        "image": {"repository": "timescale/timescaledb", "tag": "latest-pg16", "containerPort": "5432", "command": []},
        "addons_type": [],
        "addons": [],
        "envVars": [
            {"name": "POSTGRES_USER", "value": "postgres"},
            {"name": "POSTGRES_PASSWORD", "value": "change-me"},
            {"name": "POSTGRES_DB", "value": "timescaledb"},
            {"name": "TIMESCALEDB_TELEMETRY", "value": "off"},
        ],
        "extraVolumes": [{"mountPath": "/var/lib/postgresql/data", "name": "timescaledb-data", "size": "20Gi"}],
        "resources": {"requests": {"cpu": "250m", "memory": "512Mi"}, "limits": {"cpu": "4", "memory": "4Gi"}},
        "healthcheck": {"path": "/", "startupSeconds": 120},
        "installation": "Change POSTGRES_PASSWORD. Connect via PostgreSQL clients on port 5432 (note: this port is internal; use port-forwarding or the kubero connection info to access it). Create hypertables with SELECT create_hypertable('my_table', 'time'). TimescaleDB adds time-series superpowers to standard Postgres — all standard psql tools and ORMs work unchanged.",
    },

    {
        "slug": "adminer",
        "title": "Adminer",
        "description": "Lightweight single-file database manager for MySQL, PostgreSQL, SQLite, MongoDB, and more — simpler alternative to phpMyAdmin.",
        "source": "https://github.com/vrana/adminer",
        "website": "https://www.adminer.org",
        "categories": ["database", "development", "utilities"],
        "license": "Apache-2.0",
        "spdx_id": "Apache-2.0",
        "stars": 7000,
        "language": "PHP",
        "links": ["https://www.adminer.org/"],
        "image": {"repository": "adminer", "tag": "latest", "containerPort": "8080", "command": []},
        "addons_type": [],
        "addons": [],
        "envVars": [
            {"name": "ADMINER_DEFAULT_SERVER", "value": ""},
            {"name": "ADMINER_DESIGN", "value": "pepa-linha"},
        ],
        "extraVolumes": [],
        "resources": {"requests": {"cpu": "50m", "memory": "64Mi"}, "limits": {"cpu": "500m", "memory": "256Mi"}},
        "healthcheck": {"path": "/", "startupSeconds": 30},
        "installation": "Adminer has no credentials of its own — it proxies your database credentials. Enter the hostname, username, and password of any database server accessible from within the cluster (e.g. a CNPG Postgres at myapp-postgresql-rw, port 5432). Supports PostgreSQL, MySQL/MariaDB, SQLite, and more. For security, restrict ingress access to internal users only.",
    },

    {
        "slug": "pgadmin",
        "title": "pgAdmin 4",
        "description": "The most popular open-source administration and management platform for PostgreSQL databases, with a full-featured web UI.",
        "source": "https://github.com/pgadmin-org/pgadmin4",
        "website": "https://www.pgadmin.org",
        "categories": ["database", "development", "utilities"],
        "license": "PostgreSQL",
        "spdx_id": "PostgreSQL",
        "stars": 4000,
        "language": "Python",
        "links": ["https://www.pgadmin.org/docs/"],
        "image": {"repository": "dpage/pgadmin4", "tag": "latest", "containerPort": "80", "command": []},
        "addons_type": [],
        "addons": [],
        "envVars": [
            {"name": "PGADMIN_DEFAULT_EMAIL", "value": "admin@example.com"},
            {"name": "PGADMIN_DEFAULT_PASSWORD", "value": "change-me"},
            {"name": "PGADMIN_LISTEN_PORT", "value": "80"},
            {"name": "PGADMIN_CONFIG_ENHANCED_COOKIE_PROTECTION", "value": "True"},
            {"name": "PGADMIN_CONFIG_LOGIN_BANNER", "value": "'Authorised users only'"},
        ],
        "extraVolumes": [{"mountPath": "/var/lib/pgadmin", "name": "pgadmin-data", "size": "1Gi"}],
        "resources": {"requests": {"cpu": "100m", "memory": "256Mi"}, "limits": {"cpu": "1", "memory": "1Gi"}},
        "healthcheck": {"path": "/misc/ping", "startupSeconds": 60},
        "installation": "Change PGADMIN_DEFAULT_EMAIL and PGADMIN_DEFAULT_PASSWORD. Log in with those credentials. Add your PostgreSQL servers via Object > Register > Server, entering the cluster host (e.g. myapp-postgresql-rw) and credentials. Connection details are saved in the pgadmin-data volume. For security, restrict ingress access to authorised users only.",
    },

    # ── Networking ───────────────────────────────────────────────────────────

    {
        "slug": "headscale",
        "title": "Headscale",
        "description": "Self-hosted Tailscale control server — manage your own WireGuard mesh VPN with the full Tailscale client ecosystem but zero vendor lock-in.",
        "source": "https://github.com/juanfont/headscale",
        "website": "https://headscale.net",
        "categories": ["networking", "security", "utilities"],
        "license": "BSD-3-Clause",
        "spdx_id": "BSD-3-Clause",
        "stars": 24000,
        "language": "Go",
        "links": ["https://headscale.net/running-headscale-container/"],
        "image": {"repository": "headscale/headscale", "tag": "latest", "containerPort": "8080", "command": ["serve"]},
        "addons_type": [],
        "addons": [],
        "envVars": [
            {"name": "HEADSCALE_LISTEN_ADDR", "value": "0.0.0.0:8080"},
            {"name": "HEADSCALE_SERVER_URL", "value": "{{KUBERO_APP_URL}}"},
            {"name": "HEADSCALE_DB_TYPE", "value": "sqlite3"},
            {"name": "HEADSCALE_DB_PATH", "value": "/etc/headscale/db.sqlite"},
            {"name": "HEADSCALE_PRIVATE_KEY_PATH", "value": "/etc/headscale/private.key"},
            {"name": "HEADSCALE_NOISE_PRIVATE_KEY_PATH", "value": "/etc/headscale/noise_private.key"},
            {"name": "HEADSCALE_IP_PREFIXES", "value": "100.64.0.0/10"},
        ],
        "extraVolumes": [{"mountPath": "/etc/headscale", "name": "headscale-data", "size": "1Gi"}],
        "resources": {"requests": {"cpu": "100m", "memory": "128Mi"}, "limits": {"cpu": "1", "memory": "512Mi"}},
        "healthcheck": {"path": "/health", "startupSeconds": 60},
        "installation": "Headscale uses SQLite by default — no database add-on required. HEADSCALE_SERVER_URL must be the public HTTPS URL of this app. After deploy, create a user with headscale users create <name> (exec into the container or use the gRPC API). Generate a pre-auth key with headscale preauthkeys create --user <name> --reusable, then use it with the Tailscale client: tailscale up --login-server={{KUBERO_APP_URL}}.",
    },

    # ── Email ────────────────────────────────────────────────────────────────

    {
        "slug": "listmonk",
        "title": "Listmonk",
        "description": "Self-hosted high-performance newsletter and mailing list manager with analytics, templating, and multi-list support. Mailchimp alternative.",
        "source": "https://github.com/knadh/listmonk",
        "website": "https://listmonk.app",
        "categories": ["email", "marketing", "communication"],
        "license": "AGPL-3.0",
        "spdx_id": "AGPL-3.0",
        "stars": 16000,
        "language": "Go",
        "links": ["https://listmonk.app/docs/"],
        "image": {"repository": "listmonk/listmonk", "tag": "latest", "containerPort": "9000", "command": []},
        "addons_type": ["pg"],
        "addons": [{"type": "postgres", "name": "listmonk", "db": "listmonk", "user": "listmonk", "password": "listmonk"}],
        "envVars": [
            {"name": "LISTMONK_db__host", "value": "listmonk-postgresql-rw"},
            {"name": "LISTMONK_db__port", "value": "5432"},
            {"name": "LISTMONK_db__user", "value": "listmonk"},
            {"name": "LISTMONK_db__password", "value": "listmonk"},
            {"name": "LISTMONK_db__database", "value": "listmonk"},
            {"name": "LISTMONK_app__admin_username", "value": "admin"},
            {"name": "LISTMONK_app__admin_password", "value": "change-me"},
            {"name": "LISTMONK_app__address", "value": "0.0.0.0:9000"},
        ],
        "extraVolumes": [{"mountPath": "/listmonk/uploads", "name": "listmonk-uploads", "size": "5Gi"}],
        "resources": {"requests": {"cpu": "100m", "memory": "128Mi"}, "limits": {"cpu": "1", "memory": "512Mi"}},
        "healthcheck": {"path": "/health", "startupSeconds": 120},
        "installation": "Change LISTMONK_app__admin_password. On first boot, listmonk runs database migrations automatically. Log in at /admin with admin/<password>. Configure an SMTP server in Settings > SMTP to send campaigns. Import subscribers via CSV or the API. Listmonk is extremely efficient — a single instance can send millions of emails per hour with a good SMTP provider.",
    },

    {
        "slug": "stalwart-mail",
        "title": "Stalwart Mail",
        "description": "All-in-one mail server with SMTP, IMAP, JMAP, and ManageSieve — modern Rust implementation with built-in anti-spam, DKIM, and web admin.",
        "source": "https://github.com/stalwartlabs/mail-server",
        "website": "https://stalw.art",
        "categories": ["email", "communication", "utilities"],
        "license": "AGPL-3.0",
        "spdx_id": "AGPL-3.0",
        "stars": 8000,
        "language": "Rust",
        "links": ["https://stalw.art/docs/get-started/"],
        "image": {"repository": "stalwartlabs/mail-server", "tag": "latest", "containerPort": "8080", "command": []},
        "addons_type": [],
        "addons": [],
        "envVars": [
            {"name": "TZ", "value": "UTC"},
        ],
        "extraVolumes": [{"mountPath": "/opt/stalwart-mail", "name": "stalwart-data", "size": "20Gi"}],
        "resources": {"requests": {"cpu": "250m", "memory": "256Mi"}, "limits": {"cpu": "2", "memory": "1Gi"}},
        "healthcheck": {"path": "/healthz", "startupSeconds": 60},
        "installation": "Stalwart stores all data (config, mail, SQLite) in the /opt/stalwart-mail volume. The web admin UI is at port 8080 (the kubero app URL). IMPORTANT: SMTP (25), SMTPS (465/587), IMAP (143/993), and ManageSieve (4190) ports are NOT exposed via the default HTTP ingress — you need a TCP/LoadBalancer service for mail ports. Access the admin panel first, set the admin password, then configure domains and DNS records. Use with an external SMTP relay or expose mail ports via a LoadBalancer.",
    },

    # ── Finance ──────────────────────────────────────────────────────────────

    {
        "slug": "actual-budget",
        "title": "Actual Budget",
        "description": "Local-first personal finance app with envelope budgeting, bank sync, and end-to-end encryption. Self-hosted YNAB alternative.",
        "source": "https://github.com/actualbudget/actual",
        "website": "https://actualbudget.org",
        "categories": ["finance", "productivity", "utilities"],
        "license": "MIT",
        "spdx_id": "MIT",
        "stars": 17000,
        "language": "JavaScript",
        "links": ["https://actualbudget.org/docs/"],
        "image": {"repository": "actualbudget/actual-server", "tag": "latest", "containerPort": "5006", "command": []},
        "addons_type": [],
        "addons": [],
        "envVars": [
            {"name": "ACTUAL_SERVER_HOSTNAME", "value": "0.0.0.0"},
        ],
        "extraVolumes": [{"mountPath": "/data", "name": "actual-data", "size": "2Gi"}],
        "resources": {"requests": {"cpu": "100m", "memory": "128Mi"}, "limits": {"cpu": "1", "memory": "512Mi"}},
        "healthcheck": {"path": "/", "startupSeconds": 30},
        "installation": "Actual Budget stores budgets as SQLite files in the /data volume. On first visit, create a password for the server. Each budget file can be synced across devices. Bank sync requires a GoCardless or SimpleFIN subscription (optional — manual entry also works). All data is end-to-end encrypted client-side. No external database needed.",
    },

    {
        "slug": "firefly-iii",
        "title": "Firefly III",
        "description": "Self-hosted personal finance manager — transactions, budgets, bills, piggy banks, reports, and recurring transactions. Full-featured money management.",
        "source": "https://github.com/firefly-iii/firefly-iii",
        "website": "https://www.firefly-iii.org",
        "categories": ["finance", "productivity", "utilities"],
        "license": "AGPL-3.0",
        "spdx_id": "AGPL-3.0",
        "stars": 16000,
        "language": "PHP",
        "links": ["https://docs.firefly-iii.org/", "https://hub.docker.com/r/fireflyiii/core"],
        "image": {"repository": "fireflyiii/core", "tag": "latest", "containerPort": "8080", "command": []},
        "addons_type": ["mariadb", "valkey"],
        "addons": [
            {"type": "mariadb", "name": "firefly-iii", "db": "firefly-iii", "user": "firefly-iii", "password": "firefly-iii"},
            {"type": "redis", "name": "firefly-iii"},
        ],
        "envVars": [
            {"name": "APP_KEY", "value": "SomeRandomStringOf32CharsExactly"},
            {"name": "APP_URL", "value": "{{KUBERO_APP_URL}}"},
            {"name": "APP_ENV", "value": "production"},
            {"name": "DB_CONNECTION", "value": "mysql"},
            {"name": "DB_HOST", "value": "firefly-iii-db"},
            {"name": "DB_PORT", "value": "3306"},
            {"name": "DB_DATABASE", "value": "firefly-iii"},
            {"name": "DB_USERNAME", "value": "firefly-iii"},
            {"name": "DB_PASSWORD", "value": "firefly-iii"},
            {"name": "REDIS_HOST", "value": "rfr-firefly-iii-cache-readwrite"},
            {"name": "REDIS_PORT", "value": "6379"},
            {"name": "CACHE_DRIVER", "value": "redis"},
            {"name": "SESSION_DRIVER", "value": "redis"},
            {"name": "TRUSTED_PROXIES", "value": "**"},
        ],
        "extraVolumes": [{"mountPath": "/var/www/html/storage/upload", "name": "firefly-iii-uploads", "size": "5Gi"}],
        "resources": {"requests": {"cpu": "250m", "memory": "512Mi"}, "limits": {"cpu": "1", "memory": "1Gi"}},
        "healthcheck": {"path": "/health", "startupSeconds": 300},
        "installation": "APP_KEY must be exactly 32 characters — generate with: openssl rand -base64 24 | tr -d '/+=' | head -c 32. On first visit, register the first user (becomes admin). Configure your currencies, accounts, and categories. For automatic bank import, deploy the separate Firefly III Data Importer container. File uploads go to the firefly-iii-uploads volume.",
    },

    # ── Dev tools ────────────────────────────────────────────────────────────

    {
        "slug": "verdaccio",
        "title": "Verdaccio",
        "description": "Lightweight private npm/yarn/pnpm registry — proxy public packages and publish private ones with simple auth and no external database.",
        "source": "https://github.com/verdaccio/verdaccio",
        "website": "https://verdaccio.org",
        "categories": ["development", "utilities", "devops"],
        "license": "MIT",
        "spdx_id": "MIT",
        "stars": 17000,
        "language": "TypeScript",
        "links": ["https://verdaccio.org/docs/installation/"],
        "image": {"repository": "verdaccio/verdaccio", "tag": "latest", "containerPort": "4873", "command": []},
        "addons_type": [],
        "addons": [],
        "envVars": [
            {"name": "VERDACCIO_PORT", "value": "4873"},
            {"name": "VERDACCIO_PROTOCOL", "value": "https"},
        ],
        "extraVolumes": [
            {"mountPath": "/verdaccio/storage", "name": "verdaccio-storage", "size": "10Gi"},
            {"mountPath": "/verdaccio/conf", "name": "verdaccio-conf", "size": "1Gi"},
        ],
        "resources": {"requests": {"cpu": "100m", "memory": "128Mi"}, "limits": {"cpu": "1", "memory": "512Mi"}},
        "healthcheck": {"path": "/-/ping", "startupSeconds": 60},
        "installation": "Configure your npm client: npm set registry {{KUBERO_APP_URL}}. Add users with npm adduser --registry {{KUBERO_APP_URL}}. Publish packages with npm publish --registry {{KUBERO_APP_URL}}. By default Verdaccio proxies missing packages from npmjs.org. Configure auth, package access rules, and proxy uplinks by mounting a custom config.yaml to /verdaccio/conf/config.yaml via the conf volume.",
    },

    # ── Storage ──────────────────────────────────────────────────────────────

    {
        "slug": "seafile",
        "title": "Seafile",
        "description": "High-performance self-hosted file sync and share — encrypted libraries, version history, team collaboration, and Office online editing.",
        "source": "https://github.com/haiwen/seafile",
        "website": "https://www.seafile.com",
        "categories": ["storage", "productivity", "work"],
        "license": "Apache-2.0",
        "spdx_id": "Apache-2.0",
        "stars": 13000,
        "language": "Python",
        "links": ["https://manual.seafile.com/"],
        "image": {"repository": "seafileltd/seafile-mc", "tag": "latest", "containerPort": "80", "command": []},
        "addons_type": ["mariadb"],
        "addons": [{"type": "mariadb", "name": "seafile", "db": "seafile", "user": "seafile", "password": "seafile"}],
        "envVars": [
            {"name": "DB_HOST", "value": "seafile-db"},
            {"name": "DB_ROOT_PASSWD", "value": "seafile"},
            {"name": "TIME_ZONE", "value": "Etc/UTC"},
            {"name": "SEAFILE_ADMIN_EMAIL", "value": "admin@example.com"},
            {"name": "SEAFILE_ADMIN_PASSWORD", "value": "change-me"},
            {"name": "SEAFILE_SERVER_HOSTNAME", "value": "{{KUBERO_APP_HOST}}"},
            {"name": "SEAFILE_SERVER_LETSENCRYPT", "value": "false"},
        ],
        "extraVolumes": [{"mountPath": "/shared", "name": "seafile-data", "size": "50Gi"}],
        "resources": {"requests": {"cpu": "250m", "memory": "512Mi"}, "limits": {"cpu": "2", "memory": "2Gi"}},
        "healthcheck": {"path": "/", "startupSeconds": 300},
        "installation": "Change SEAFILE_ADMIN_EMAIL and SEAFILE_ADMIN_PASSWORD. SEAFILE_SERVER_HOSTNAME must be just the hostname (no https://, e.g. seafile.example.com). DB_ROOT_PASSWD must match the MariaDB root password from the add-on (default: seafile). On first start, Seafile auto-creates its databases (seafile, seahub, ccnet). The seafile-data volume holds all uploaded files. SEAFILE_SERVER_LETSENCRYPT=false because TLS is handled by the kubero ingress.",
    },

]


# ─── Generator ───────────────────────────────────────────────────────────────

def main() -> int:
    created_dirs = []
    created_yamls = []
    created_specs = []

    for app in APPS:
        slug = app["slug"]
        svc_dir = SERVICES / slug
        svc_dir.mkdir(parents=True, exist_ok=True)
        created_dirs.append(slug)

        # Write app.yaml
        yaml_path = svc_dir / "app.yaml"
        yaml_content = generate_app_yaml(app)
        yaml_path.write_text(yaml_content, encoding="utf-8")
        created_yamls.append(str(yaml_path.relative_to(ROOT)))

        # Write spec JSON
        spec_path = SPECS / f"{slug}.json"
        spec = generate_spec_json(app)
        spec_path.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        created_specs.append(slug)

        print(f"  [{slug}] app.yaml + _specs/{slug}.json")

    # Update index.json
    index_path = ROOT / "index.json"
    with open(index_path, encoding="utf-8") as f:
        index = json.load(f)

    existing_slugs = {s.get("name") or s.get("dirname") for s in index["services"]}
    added = 0
    for app in APPS:
        slug = app["slug"]
        if slug not in existing_slugs:
            index["services"].append(index_entry(app))
            added += 1

    if "stats" in index and "count" in index["stats"]:
        index["stats"]["count"] = len(index["services"])

    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"\nDone:")
    print(f"  {len(created_dirs)} service directories created/updated")
    print(f"  {len(created_specs)} spec JSONs written")
    print(f"  {added} new entries added to index.json ({len(index['services'])} total)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
