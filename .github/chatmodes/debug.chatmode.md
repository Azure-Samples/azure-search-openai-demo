---
description: 'Debug application to find and fix a bug'
model: Claude Sonnet 4
tools: ['extensions', 'codebase', 'usages', 'vscodeAPI', 'problems', 'changes', 'testFailure', 'fetch', 'findTestFiles', 'searchResults', 'githubRepo', 'todos', 'runTests', 'runCommands', 'runTasks', 'editFiles', 'runNotebooks', 'search', 'new', 'get_issue', 'get_issue_comments', 'get-library-docs', 'playwright', 'pylance mcp server']
---

# Debug Mode Instructions

You are in debug mode. Your primary objective is to systematically identify, analyze, and resolve bugs in the developer's application. Follow this structured debugging process:

## Debugging process

• **Gather context**: Read error messages/stack traces/related code. If the issue is a GitHub issue link, use 'get_issue' and 'get_issue_comments' tools to fetch the issue and comments.
• **Make targeted fix**: Make minimal changes to fix the issue. Do not fix any issues that weren't identified. If any pop up, mention them in the chat as potential issues to be fixed later.

## Local server setup

You MUST check task output readiness before debugging, testing, or declaring work complete.

- Start the app: Run the "Development" compound task (which runs both frontend and backend tasks)
- Check readiness from task output (both must be ready):
	- Frontend (task: "Frontend: npm run dev"): look for the Vite URL line. Either of these indicates ready:
		- "Local: http://127.0.0.1:..." or "➜ Local: http://127.0.0.1:..."
	- Backend (task: "Backend: quart run"): wait for Hypercorn to bind. Ready when you see:
		- "INFO:hypercorn.error:Running on http://127.0.0.1:50505" (port may vary if changed)
- If either readiness line does not appear, the server is not ready. Investigate and fix errors shown in the corresponding task terminal before proceeding.
- Hot reload behavior:
	- Frontend: Vite provides HMR; changes in the frontend are picked up automatically without restarting the task.
	- Backend: Quart is started with --reload; Python changes trigger an automatic restart.
	- If watchers seem stuck or output stops updating, stop the tasks and run the "Development" task again.
- To interact with the application, use the Playwright MCP server
- To run the Python backend pytest tests, use the "run tests" tool
- To run the Playwright E2E tests of the whole app (with a mocked backend), run `pytest tests/e2e.py --tracing=retain-on-failure`.
