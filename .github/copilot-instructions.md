
# Copilot & AI Agent Instructions for This Codebase

This project is a RAG (Retrieval-Augmented Generation) chat app using Azure OpenAI and Azure AI Search, with a Python (Quart) backend and a React (Vite/TypeScript) frontend. It is designed for rapid iteration, Azure deployment, and extensibility. These instructions guide AI coding agents to be productive and follow project conventions.

## Architecture Overview

- **Backend**: `app/backend` (Quart, Python)
  - `approaches/`: Pluggable RAG strategies (e.g., `retrievethenread.py`, `chatreadretrieveread.py`)
  - `app.py`: Main entry point
- **Frontend**: `app/frontend` (React, Vite, TypeScript)
  - `src/api/`: API client
  - `src/components/`: UI components
  - `src/locales/`: i18n translations (edit all languages for new UI strings)
- **Infra**: `infra/` (Bicep templates, `azure.yaml`)
- **Data**: `data/` (documents for ingestion)
- **Tests**: `tests/` (pytest, Playwright e2e)

See `docs/architecture.md` for diagrams and data flow.

## Key Workflows

- **Local Dev**: Use VS Code Dev Containers or Codespaces for pre-configured environments. See `docs/localdev.md` for hot reloading, debug, and task usage.
  - Start dev servers: Use the VS Code "Development" task or run `app/start.sh` (runs both frontend and backend with hot reload).
- **Azure Deployment**: Use `azd up` to provision infra and deploy code. Use `azd deploy` to redeploy code only. See `README.md` and `docs/azd.md`.
- **Data Ingestion**: Add files to `data/`, then run `scripts/prepdocs.sh` to ingest.
- **Testing**: All tests in `tests/` (pytest). E2E tests in `e2e.py` (Playwright, mocks backend). Activate `.venv` before running tests.

## Project-Specific Conventions

- **Adding azd env vars**: Update all of:
  1. `infra/main.parameters.json` (add param)
  2. `infra/main.bicep` (add param, wire to `appEnvVariables`)
  3. `azure.yaml` (pipeline config)
  4. `.azdo/pipelines/azure-dev.yml` and `.github/workflows/azure-dev.yml` (env section)
- **Adding Developer Settings**:
  - Frontend: Update `src/api/models.ts`, `components/Settings.tsx`, all `locales/*/translation.json`, and pass through `pages/chat/Chat.tsx` and `pages/ask/Ask.tsx`.
  - Backend: Update `approaches/chatreadretrieveread.py`, `approaches/retrievethenread.py`, and `app.py` as needed.
- **Tests**: Add e2e for UI, integration for API, unit for functions. Use `conftest.py` for mocks.
- **Pull Requests**: Follow `PULL_REQUEST_TEMPLATE.md`.

## Integration & Patterns

- **Backend/Frontend API**: REST endpoints defined in backend, consumed via `src/api/`.
- **RAG Approaches**: Add new strategies in `app/backend/approaches/` and register in `app.py`.
- **Internationalization**: All UI strings must be added to every language in `src/locales/`.
- **Infra**: All infra changes must be reflected in both Bicep and pipeline config files.

## References

- [README.md](../README.md) — Quickstart, deployment, and dev environment
- [docs/architecture.md](../docs/architecture.md) — Architecture diagrams and explanation
- [docs/localdev.md](../docs/localdev.md) — Local dev, debugging, and tasks

> **Nota:** Mantenha os links de referência acima atualizados conforme a estrutura do projeto. Se mover arquivos como AGENTS.md, ajuste o caminho aqui.

Keep this file up to date with any changes to workflows or conventions.
