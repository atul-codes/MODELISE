# MODELISE

A governance proxy that sits between prompts and models. Nothing reaches a self-hosted model or a commercial AI without passing through Layer 1 and Layer 2 first.

> This documents the build you currently have installed, the one with two fixed policy buckets (`custom_model_default` / `commercial_ai_default`), not the newer per-model attachment version. If you update later, the core ideas below still hold, only the pipeline names change from two shared buckets to one per model/key.

---

## 1. System map

Five independent programs. Each one is its own folder, its own environment, its own `uvicorn` process. None of them know about each other except through plain HTTP or gRPC calls.

| Service | What it does | Port | Required |
|---|---|---|---|
| `guardrail_layer2` | FAISS rulebook engine + local model answers. Layer 2, default. | 8001 | Yes |
| `geo_policy_engine` | Country-specific rulebooks. Separate index per pack. | 8001 | Yes |
| `PolicyEnforcementService` (PEL) | Image / NSFW check, used by Layer 1. gRPC, not REST. | 50051 | Optional |
| `Backend-main` | The orchestrator. Owns the database, the provider registry, the chat routes. | 8080 | Yes |
| `Frontend-main` | The website. Talks only to Backend-main, never to the others directly. | 5173 | Optional |

Everything below can be done through `/docs` on each service, no frontend required. That's genuinely how this whole thing gets tested day to day.

---

## 2. How one request actually moves

1. A prompt hits Backend-main, either `/api/v1/chat/custom` or `/api/v1/chat/commercial`.
2. Backend-main checks the provider registry: what's switched on, what's attached to this request's pipeline.
3. **Layer 1** runs first. A regex-based prompt-injection screen, instant, no network call. If an image is attached and the PEL provider is on, that runs too.
4. Layer 1 blocks → stop. Nothing past this point ever runs.
5. **Layer 2** runs next. Whichever providers are attached to this pipeline get called concurrently, guardrail_layer2, PEL's text classifier, any geo pack. First one to say block wins; the rest get cancelled.
6. Layer 2 blocks → stop. The actual model or commercial API is never touched.
7. Both layers clear → the real call goes out, to your custom model or to OpenAI / Anthropic / Gemini.
8. Response comes back with a governance trail: what ran, what passed, what it cost.

**Worth remembering:** a blocked prompt costs nothing. Layer 1 and Layer 2 both run before any real model call, commercial or otherwise, is ever made.

---

## 3. Starting everything, in order

Backend-main depends on the first two being reachable. Start them first, or Layer 2 will fail closed (block everything) because it can't reach its own checks.

**Terminal 1 — LM Studio / Ollama**
Load your model, start the local server, leave it running.

**Terminal 2 — guardrail_layer2**
```
cd guardrail_layer2
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8001
```

**Terminal 3 — geo_policy_engine**
```
cd geo_policy_engine
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

**Terminal 4 — Backend-main**
```
cd Backend-main
.\venv\Scripts\Activate.ps1
uvicorn src.app:app --reload --port 8080
```

**Terminal 5 — Frontend-main (optional)**
```
cd Frontend-main
npm run dev
```

---

## 4. Environment files

Each service reads its own `.env`, sitting next to its own `app` or `src` folder. None of them share one file.

**guardrail_layer2 / .env**
```
OLLAMA_BASE_URL=http://localhost:1234        # LM Studio's server, or Ollama's
OLLAMA_EVAL_MODEL=your-exact-model-name       # must match /v1/models exactly
OLLAMA_GEN_MODEL=your-exact-model-name
JWT_SECRET_KEY=anything-random
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-password
```

**geo_policy_engine / .env**
```
JWT_SECRET_KEY=anything-random
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-password                  # can differ from the other services
```

**Backend-main / .env**
```
DATABASE_URL=sqlite:///./modelise.db          # SQLite is enough for local use
JWT_SECRET_KEY=anything-random
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-password
CREDENTIAL_ENCRYPTION_KEY=generated-key        # see command below
GUARDRAIL_LAYER2_BASE_URL=http://localhost:8000
GEO_POLICY_ENGINE_BASE_URL=http://localhost:8100
GEO_POLICY_ENGINE_ADMIN_USERNAME=admin         # must match geo_policy_engine's real admin login
GEO_POLICY_ENGINE_ADMIN_PASSWORD=your-password
```

Generate the encryption key once, inside Backend-main's terminal, with its environment active, then paste the output into `CREDENTIAL_ENCRYPTION_KEY`:
```
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## 5. Core concepts

### Provider
One checkable thing. A row in Backend-main's database. Has a `kind` (what it actually is), an `enabled` switch, and an `attached_pipelines` list (which request buckets it applies to).

| kind | What it is | On by default |
|---|---|---|
| `layer1_heuristic` | Word-pattern jailbreak screen | Yes |
| `layer1_image_nsfw_grpc` | Image check via PEL | Yes |
| `layer2_faiss_rest` | guardrail_layer2's rulebook engine | Yes |
| `layer2_grpc_classifier` | PEL's text classifier, alternate Layer 2 | No |
| `geo_policy_pack` | A country/regime rulebook you uploaded | No, you switch it on |
| `custom_policy` | A custom policy rulebook you uploaded | No, you switch it on |

### Pipeline
In this version, there are exactly two: `custom_model_default` (every registered custom model shares this) and `commercial_ai_default` (every stored commercial key shares this). A provider attached to one applies to **everything** using that bucket, there's no per-model granularity yet.

**The one mistake worth avoiding:** `PUT /providers/{id}/attachments` **replaces** the whole `attached_pipelines` list, it doesn't add to it. Always `GET /api/v1/providers` first, copy the existing array, then add your change to it, or you'll silently detach everything else that provider was doing.

---

## 6. Common tasks

**Log in**
```
POST /api/v1/auth/login
{ "username": "admin", "password": "..." }
```
Copy `access_token` from the response, click **Authorize** at the top of `/docs`, paste it in the single box. Do this again after every server restart and every browser refresh, it doesn't persist.

**Connect a self-hosted model**
```
POST /api/v1/custom-models
{
  "name": "My Local Model",
  "base_url": "http://localhost:1234/v1/chat/completions",
  "request_style": "openai_chat"
}
```

**Add a commercial AI key**
```
POST /api/v1/credentials
{ "provider": "openai", "label": "prod key", "api_key": "sk-..." }
```

**Upload a geo policy pack**
```
POST /api/v1/geo-policies/{pack_id}/upload-csv?display_name=India%20DPDP
```
Multipart file upload. The CSV needs `prompt` and `allow/block` columns.

**Turn a policy on for all custom models**
```
PUT /api/v1/providers/{provider_id}/attachments
{ "attached_pipelines": ["custom_model_default", "commercial_ai_default"] }
```

**Send a prompt through the full chain**
```
POST /api/v1/chat/custom
{
  "user_id": "test1",
  "endpoint_id": "...",
  "prompt": "What's a good pasta recipe?",
  "max_output_tokens": 512
}
```

---

## 7. Points to note

- LM Studio doesn't speak Ollama's native API. guardrail_layer2's judge call and its generation call both go through the OpenAI-compatible `/v1/chat/completions` endpoint. If you're on Ollama instead of LM Studio, this still works the same way.
- `--reload` only watches `.py` files. Editing `.env` does nothing until you fully stop (`Ctrl+C`) and restart the server.
- Every service bootstraps one admin account from its own `.env` at startup. There's no shared login across services, Backend-main's admin password and geo_policy_engine's admin password can be, and usually are, different values.
- PDF policy uploads need `langchain-community` installed. CSV uploads don't. If PDF upload throws an internal server error but CSV works fine, check that package first.
- `pyodbc` is only needed if `DATABASE_URL` points at a real SQL Server. Plain SQLite (`sqlite:///./modelise.db`) doesn't need it at all.
- An empty rulebook doesn't block anything, by design. If a prompt that should be blocked comes back approved, check `chunks_evaluated` in the response, if it's `0`, nothing was actually indexed on this run yet.
- `Create Provider` in `/docs` accepts any `kind` string, but only five values actually do anything (see the table in section 5). Anything else creates a real, harmless, inert row.
- The generic `/models/upload` endpoint at the top of the API list is unrelated to everything above, it's a separate file-upload feature, not part of the governance chain.

---

## 8. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| "Not authenticated" on an upload/admin call | Login expired or was never done this session | Re-run login, re-click Authorize |
| Prompt that should block comes back approved | `chunks_evaluated: 0`, empty index | Re-upload the CSV/PDF on this running instance |
| 503 on `/evaluate` or `/inspect` | Model server unreachable at the configured URL/name | Check `OLLAMA_BASE_URL` matches your actual model server, check the model name matches `/v1/models` exactly |
| Internal Server Error, no detail in the browser | Real error is in the terminal, not the browser | Check the red text in the `uvicorn` terminal window |
| Red underlines on `from app... import` in the editor, but it runs fine | Editor doesn't know the project root | Right-click the top folder → Mark Directory as → Sources Root |
| "Connection refused" in the browser | Server isn't actually running | Check the terminal, restart with `uvicorn ...` |
