# Instructions for Coding Agents

This file contains instructions for developers working on the Azure Search and OpenAI demo application. It covers the overall code layout, how to add new data, how to add new azd environment variables, how to add new developer settings, and how to add tests for new features.

Always keep this file up to date with any changes to the codebase or development process.
If necessary, edit this file to ensure it accurately reflects the current state of the project.

## Overall code layout

* app: Contains the main application code, including frontend and backend.
  * app/backend: Contains the Python backend code, written with Quart framework.
    * app/backend/approaches: Contains the different approaches
      * app/backend/approaches/approach.py: Base class for all approaches
      * app/backend/approaches/retrievethenread.py: Ask approach, just searches and answers
      * app/backend/approaches/chatreadretrieveread.py: Chat approach, includes query rewriting step first
      * app/backend/approaches/prompts/ask_answer_question.prompty: Prompt used by the Ask approach to answer the question based off sources
      * app/backend/approaches/prompts/chat_query_rewrite.prompty: Prompt used to rewrite the query based off search history into a better search query
      * app/backend/approaches/prompts/chat_query_rewrite_tools.json: Tools used by the query rewriting prompt
      * app/backend/approaches/prompts/chat_answer_question.prompty: Prompt used by the Chat approach to actually answer the question based off sources
    * app/backend/prepdocslib/cloudingestionstrategy.py: Builds the Azure AI Search indexer and skillset for the cloud ingestion pipeline
    * app/backend/prepdocslib/pdfparser.py: Uses Azure Document Intelligence to emit page text plus figure placeholders
    * app/backend/prepdocslib/figureprocessor.py: Shared helper that generates figure descriptions for both local ingestion and the cloud figure-processor skill
    * app/backend/app.py: The main entry point for the backend application.
  * app/frontend: Contains the React frontend code, built with TypeScript, built with vite.
    * app/frontend/src/api: Contains the API client code for communicating with the backend.
    * app/frontend/src/components: Contains the React components for the frontend.
    * app/frontend/src/locales: Contains the translation files for internationalization.
      * app/frontend/src/locales/da/translation.json: Danish translations
      * app/frontend/src/locales/en/translation.json: English translations
      * app/frontend/src/locales/es/translation.json: Spanish translations
      * app/frontend/src/locales/fr/translation.json: French translations
      * app/frontend/src/locales/it/translation.json: Italian translations
      * app/frontend/src/locales/ja/translation.json: Japanese translations
      * app/frontend/src/locales/nl/translation.json: Dutch translations
      * app/frontend/src/locales/ptBR/translation.json: Portuguese translations
      * app/frontend/src/locales/tr/translation.json: Turkish translations
    * app/frontend/src/pages: Contains the main pages of the application
* infra: Contains the Bicep templates for provisioning Azure resources.
* tests: Contains the test code, including e2e tests, app integration tests, and unit tests.

## Adding new data

New files should be added to the `data` folder, and then either run scripts/prepdocs.sh or scripts/prepdocs.ps1 to ingest the data.

## Adding a new azd environment variable

An azd environment variable is stored by the azd CLI for each environment. It is passed to the "azd up" command and can configure both provisioning options and application settings.
When adding new azd environment variables, update:

1. infra/main.parameters.json : Add the new parameter with a Bicep-friendly variable name and map to the new environment variable
1. infra/main.bicep: Add the new Bicep parameter at the top, and add it to the `appEnvVariables` object
1. .azdo/pipelines/azure-dev.yml: Add the new environment variable under `env` section
1. .github/workflows/azure-dev.yml: Add the new environment variable under `env` section

For cloud ingestion, `prepdocs.py --use-cloud-ingestion` expects the function endpoints and managed identity resource IDs in the azd environment. The search service must have a system- or user-assigned managed identity with access to the Azure Functions app:

* `DOCUMENT_EXTRACTOR_SKILL_ENDPOINT`
* `DOCUMENT_EXTRACTOR_SKILL_RESOURCE_ID`
* `FIGURE_PROCESSOR_SKILL_ENDPOINT`
* `FIGURE_PROCESSOR_SKILL_RESOURCE_ID`
* `TEXT_PROCESSOR_SKILL_ENDPOINT`
* `TEXT_PROCESSOR_SKILL_RESOURCE_ID`

## Adding a new setting to "Developer Settings" in RAG app

When adding a new developer setting, update:

* frontend:
  * app/frontend/src/api/models.ts : Add to ChatAppRequestOverrides
  * app/frontend/src/components/Settings.tsx : Add a UI element for the setting
  * app/frontend/src/locales/*/translations.json: Add a translation for the setting label/tooltip for all languages
  * app/frontend/src/pages/chat/Chat.tsx: Add the setting to the component, pass it to Settings
  * app/frontend/src/pages/ask/Ask.tsx: Add the setting to the component, pass it to Settings

* backend:
  * app/backend/approaches/chatreadretrieveread.py :  Retrieve from overrides parameter
  * app/backend/approaches/retrievethenread.py : Retrieve from overrides parameter
  * app/backend/app.py: Some settings may need to be sent down in the /config route.

## When adding tests for a new feature

All tests are in the `tests` folder and use the pytest framework.
There are three styles of tests:

* e2e tests: These use playwright to run the app in a browser and test the UI end-to-end. They are in e2e.py and they mock the backend using the snapshots from the app tests.
* app integration tests: Mostly in test_app.py, these test the app's API endpoints and use mocks for services like Azure OpenAI and Azure Search.
* unit tests: The rest of the tests are unit tests that test individual functions and methods. They are in test_*.py files.

When adding a new feature, add tests for it in the appropriate file.
If the feature is a UI element, add an e2e test for it.
If it is an API endpoint, add an app integration test for it.
If it is a function or method, add a unit test for it.
Use mocks from tests/conftest.py to mock external services. Prefer mocking at the HTTP/requests level when possible.

When you're running tests, make sure you activate the .venv virtual environment first:

```shell
source .venv/bin/activate
```

## Sending pull requests

When sending pull requests, make sure to follow the PULL_REQUEST_TEMPLATE.md format.

## Upgrading dependencies

To upgrade a particular package in the backend, use the following command, replacing `<package-name>` with the name of the package you want to upgrade:

```shell
cd app/backend && uv pip compile requirements.in -o requirements.txt --python-version 3.9 --upgrade-package package-name
```

## Checking Python type hints

To check Python type hints, use the following command:

```shell
cd app/backend && mypy . --config-file=../pyproject.toml
```

```shell
cd scripts && mypy . --config-file=../pyproject.toml
```

Note that we do not currently enforce type hints in the tests folder, as it would require adding a lot of `# type: ignore` comments to the existing tests.
We only enforce type hints in the main application code and scripts.
