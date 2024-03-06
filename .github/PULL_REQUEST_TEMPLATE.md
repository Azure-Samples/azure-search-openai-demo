## Purpose

<!-- Describe the intention of the changes being proposed. What problem does it solve or functionality does it add? -->


## Does this introduce a breaking change?

When developers merge from main and run the server, azd up, or azd deploy, will this produce an error?
If you're not sure, try it out on an old environment.

```
[ ] Yes
[ ] No
```

## Does this require changes to learn.microsoft.com docs?

This repository is referenced by [this tutorial](https://learn.microsoft.com/azure/developer/python/get-started-app-chat-template)
which includes deployment, settings and usage instructions. If text or screenshot need to change in the tutorial,
check the box below and notify the tutorial author. A Microsoft employee can do this for you if you're an external contributor.

```
[ ] Yes
[ ] No
```

## Type of change

```
[ ] Bugfix
[ ] Feature
[ ] Code style update (formatting, local variables)
[ ] Refactoring (no functional changes, no api changes)
[ ] Documentation content changes
[ ] Other... Please describe:
```

## Code quality checklist

See [CONTRIBUTING.md](../CONTRIBUTING.md#submit-pr) for more details.

- [ ] The current tests all pass (`python -m pytest`).
- [ ] I added tests that prove my fix is effective or that my feature works
- [ ] I ran `python -m pytest --cov` to verify 100% coverage of added lines
- [ ] I ran `python -m mypy` to check for type errors
- [ ] I either used the pre-commit hooks or ran `ruff` and `black` manually on my code.
