# 🛡️ System State Checklist (2025-12-25)

Use this checklist whenever you need to confirm that the Azure Search + OpenAI demo, the automation stack, and the Taskade integrations survived an environment change or Codespace rebuild.

## ⚡ Snapshot
- **Latest audit**: 2025-12-19 (`SYSTEM_AUDIT_REPORT.md`) — status ✅ *Production ready*
- **Active branch**: `devcontainer/env-hardening`
- **Dev services**: Quart backend on port **50505**, Vite frontend on port **5173**, Azure Functions skills available under `app/functions`
- **Taskade integration**: `external/taskade-docs/` and `external/taskade-mcp/` mirror upstream repos for offline use

## ✅ Primary Checklist

### 1. Git & Workspace Hygiene
- [ ] Branch is `devcontainer/env-hardening` and `git status` is clean
- [ ] `.env` exists (copied from `.env.template`) and contains all Taskade + Azure secrets
- [ ] `post-create` script finished without errors (tmux session `aso-services` is running)

### 2. Backend Readiness
- [ ] `python --version` resolves to **3.10+** inside repo `.venv`
- [ ] `quart run --reload -p 50505` succeeds and health route `/healthz` returns `200`
- [ ] `app/backend/app.py` imports resolve (run `uv pip check` or `python -m compileall app/backend`)
- [ ] Observability enabled: OpenTelemetry exporters configured via `CONFIG_*` env vars

### 3. Frontend + Assets
- [ ] `npm ci` completed under `app/frontend`
- [ ] `npm run dev -- --host 0.0.0.0 --port 5173` hot reloads without type errors
- [ ] `.env` variables prefixed with `VITE_` (e.g., `VITE_APP_BACKEND_URI`) remain in sync with backend URL

### 4. Automation System & MCP Glue
- [ ] Browser agent Playwright dependencies installed (`npx playwright install --with-deps`)
- [ ] `app/backend/automation/taskade_client.py` can fetch `/workspaces` from Taskade API using the configured token
- [ ] `external/taskade-mcp/` linked to upstream https://github.com/taskade/mcp (run `git fetch upstream && git status`)
- [ ] MCP tooling present: `packages/server/` (official Taskade MCP server) and `packages/openapi-codegen/` for tool generation

### 5. Taskade API Surfaces (Knowledge Sources)
- [ ] **Interactive reference**: https://www.taskade.com/api/documentation/#/ (Swagger UI)
- [ ] **OpenAPI JSON**: https://www.taskade.com/api/documentation/json (download and pin with `curl -o data/taskade-openapi.json` if needed)
- [ ] **GitHub docs mirror**: https://github.com/taskade/docs → synced to `external/taskade-docs/`
- [ ] **Key endpoints recorded**: `GET /workspaces`, `GET /workspaces/{workspaceId}/folders`, `POST /workspaces/{workspaceId}/projects`, `GET /folders/{folderId}/projects`

### 6. Configuration Guardrails
- [ ] `TASKADE_API_KEY`, `TASKADE_WORKSPACE_ID`, `TASKADE_FOLDER_ID` present in `.env`
- [ ] Azure resources referenced in `infra/main.bicep` match current environment (run `azd env get-values`)
- [ ] Speech + search credentials loaded via `CONFIG_*` in `app/backend/config.py`
- [ ] Key Vault (if used) contains mirrored secrets and access policy for service principal

### 7. Validation Commands
```bash
# Backend smoke test
tmux attach -t aso-services   # backend window should show "Running on http://0.0.0.0:50505"

# Taskade connectivity
source .venv/bin/activate && python examples/taskade_examples.py --check

# Documentation sync
(cd external/taskade-docs && git pull)
(cd external/taskade-mcp && git pull)
```

## 🔗 Reference Links
| Area | Link | Notes |
|------|------|-------|
| Taskade Swagger UI | https://www.taskade.com/api/documentation/#/ | Interactive testing for REST endpoints |
| Taskade OpenAPI JSON | https://www.taskade.com/api/documentation/json | Machine-readable schema for automation |
| Taskade Docs Repo | https://github.com/taskade/docs | Mirrored under `external/taskade-docs/` |
| Taskade MCP Repo | https://github.com/taskade/mcp | Mirrored under `external/taskade-mcp/` |

## 📝 Usage Notes
- Keep this file in the `/data` folder so it is automatically ingested by the RAG pipeline; update timestamps whenever you run a new audit.
- When adding new environment variables, mirror the change in `infra/main.parameters.json`, `.github/workflows/azure-dev.yml`, and `.azdo/pipelines/azure-dev.yml`.
- Cite this checklist inside incident reports to document that all baseline settings were revalidated.
