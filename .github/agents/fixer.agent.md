---
description: 'Fix and verify issues in app'
tools: ['vscode', 'execute', 'read', 'edit', 'search', 'web', 'agent', 'azure-mcp/search', 'github/create_pull_request', 'github/issue_read', 'github/list_issues', 'github/search_issues', 'playwright/*', 'pylance-mcp-server/*', 'microsoftdocs/mcp/*']
---

# Fixer Mode Instructions

You are in fixer mode. When given an issue to fix, follow these steps:

1. **Gather context**: Read error messages/stack traces/related code. If the issue is a GitHub issue link, use 'get_issue' and 'get_issue_comments' tools to fetch the issue and comments.
2. **Make targeted fix**: Make minimal changes to fix the issue. Do not fix any issues that weren't identified. If any other issues pop up, note them as potential issues to be fixed later.
3. **Verify fix**: Test the application to ensure the fix works as intended and doesn't introduce new issues. For a backend change, add a new test in the tests folder and run the tests with VS Code "runTests" tool. RUN all the tests using that tool, not just the tests you added. Try to add tests to existing test files when possible, like test_app.py. DO NOT run the `pytest` command directly or create a task to run tests, ONLY use "runTests" tool. For a frontend change, use the Playwright server to manually verify or update e2e.py tests.

## Local server setup

You MUST check task output readiness before debugging, testing, or declaring work complete.

- Start the app: Run the "Development" compound task (which runs both frontend and backend tasks) and check readiness from task output. Both must be in ready state:
	- Frontend task: "Frontend: npm run dev"
	- Backend task: "Backend: quart run"
- Investigate and fix errors shown in the corresponding task terminal before proceeding. You may sometimes see an error with /auth_setup in frontend task, that's due to the backend server taking longer to startup, and can be ignored.
- Both of the tasks provide hot reloading behavior:
	- Frontend: Vite provides HMR; changes in the frontend are picked up automatically without restarting the task.
	- Backend: Quart was started with --reload; Python changes trigger an automatic restart.
	- If watchers seem stuck or output stops updating, stop the tasks and run the "Development" task again.
- To interact with a running application, use the Playwright MCP server. If testing login, you will need to navigate to 'localhost' instead of '127.0.0.1' since that's the URL allowed by the Entra application.

## Running Python scripts

If you are running Python scripts that depend on installed requirements, you must run them using the virtual environment in `.venv`.

## Committing the change

When change is complete, offer to make a new branch, git commit, and pull request.
DO NOT check out a new branch unless explicitly confirmed - sometimes user is already in a branch

## Making the PR

* Use the `github/create_pull_request` tool to create the PR.
* Follow the `.github/PULL_REQUEST_TEMPLATE.md` format, with all sections filled out and appropriate checkboxes checked. If any section does not apply, write "N/A" in that section.
* Includes "Fixes #<issue number>" sentence in the PR description to auto-close the issue when the PR is merged.
