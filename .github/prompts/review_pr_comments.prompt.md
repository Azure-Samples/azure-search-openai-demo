---
agent: agent
---
We have received comments on the current active pull request. Together, we will go through each comment one by one and discuss whether to accept the change, iterate on it, or reject the change.

## Steps to follow:

1. Fetch the active pull request: If available, use the `activePullRequest` tool from the `GitHub Pull Requests` toolset to get the details of the active pull request including the comments. If not, use the GitHub MCP server or GitHub CLI to get the details of the active pull request. Fetch both top level comments and inline comments.
2. Present a list of the comments with a one-sentence summary of each.
3. One at a time, present each comment in full detail and ask me whether to accept, iterate, or reject the change. Provide your recommendation for each comment based on best practices, code quality, and project guidelines. Await user's decision before proceeding to the next comment. DO NOT make any changes to the code or files until I have responded with my decision for each comment.
4. If the decision is to accept or iterate, make the necessary code changes to address the comment. If the decision is to reject, provide a brief explanation of why the change was not made.
5. Wait for user to affirm completion of any code changes made before moving to the next comment.
6. Reply to each comment on the pull request with the outcome of our discussion (accepted, iterated, or rejected) along with any relevant explanations.
