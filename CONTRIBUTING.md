# Contributing

This project welcomes contributions and suggestions.  Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit <https://cla.opensource.microsoft.com>.

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

- [Code of Conduct](#code-of-conduct)
- [Found an Issue?](#found-an-issue)
- [Want a Feature?](#want-a-feature)
- [Submission Guidelines](#submission-guidelines)
  - [Submitting an Issue](#submitting-an-issue)
  - [Submitting a Pull Request (PR)](#submitting-a-pull-request-pr)
- [Setting up the development environment](#setting-up-the-development-environment)
- [Running unit tests](#running-unit-tests)
- [Running E2E tests](#running-e2e-tests)
- [Code Style](#code-style)

## Code of Conduct

Help us keep this project open and inclusive. Please read and follow our [Code of Conduct](https://opensource.microsoft.com/codeofconduct/).

## Found an Issue?

If you find a bug in the source code or a mistake in the documentation, you can help us by
[submitting an issue](#submitting-an-issue) to the GitHub Repository. Even better, you can
[submit a Pull Request](#submitting-a-pull-request-pr) with a fix.

## Want a Feature?

You can *request* a new feature by [submitting an issue](#submitting-an-issue) to the GitHub
Repository. If you would like to *implement* a new feature, please submit an issue with
a proposal for your work first, to be sure that we can use it.

- **Small Features** can be crafted and directly [submitted as a Pull Request](#submitting-a-pull-request-pr).

## Submission Guidelines

### Submitting an Issue

Before you submit an issue, search the archive, maybe your question was already answered.

If your issue appears to be a bug, and hasn't been reported, open a new issue.
Help us to maximize the effort we can spend fixing issues and adding new
features, by not reporting duplicate issues.  Providing the following information will increase the
chances of your issue being dealt with quickly:

- **Overview of the Issue** - if an error is being thrown a non-minified stack trace helps
- **Version** - what version is affected (e.g. 0.1.2)
- **Motivation for or Use Case** - explain what are you trying to do and why the current behavior is a bug for you
- **Browsers and Operating System** - is this a problem with all browsers?
- **Reproduce the Error** - provide a live example or a unambiguous set of steps
- **Related Issues** - has a similar issue been reported before?
- **Suggest a Fix** - if you can't fix the bug yourself, perhaps you can point to what might be
  causing the problem (line of code or commit)

You can file new issues by providing the above information at the corresponding repository's issues link: <https://github.com/[organization-name>]/[repository-name]/issues/new].

### Submitting a Pull Request (PR)

Before you submit your Pull Request (PR) consider the following guidelines:

- Search the repository (<https://github.com/[organization-name>]/[repository-name]/pulls) for an open or closed PR
  that relates to your submission. You don't want to duplicate effort.
- Make your changes in a new git fork
- Follow [Code style conventions](#code-style)
- [Run the tests](#running-unit-tests) (and write new ones, if needed)
- Commit your changes using a descriptive commit message
- Push your fork to GitHub
- In GitHub, create a pull request to the `main` branch of the repository
- Ask a maintainer to review your PR and address any comments they might have

## Setting up the development environment

Install the development dependencies:

```shell
python -m pip install -r requirements-dev.txt
```

Install the pre-commit hooks:

```shell
pre-commit install
```

Compile the JavaScript:

```shell
( cd ./app/frontend ; npm install ; npm run build )
```

## Running unit tests

Run the tests:

```shell
python -m pytest
```

Check the coverage report to make sure your changes are covered.

```shell
python -m pytest --cov
```

## Running E2E tests

Install Playwright browser dependencies:

```shell
playwright install --with-deps
```

Run the tests:

```shell
python -m pytest tests/e2e.py --tracing=retain-on-failure
```

When a failure happens, the trace zip will be saved in the test-results folder.
You can view that using the Playwright CLI:

```shell
playwright show-trace test-results/<trace-zip>
```

You can also use the online trace viewer at <https://trace.playwright.dev/>

## Code Style

This codebase includes several languages: TypeScript, Python, Bicep, Powershell, and Bash.
Code should follow the standard conventions of each language.

For Python, you can enforce the conventions using `ruff` and `black`.

Install the development dependencies:

```shell
python -m pip install -r requirements-dev.txt
```

Run `ruff` to lint a file:

```shell
python -m ruff <path-to-file>
```

Run `black` to format a file:

```shell
python -m black <path-to-file>
```

If you followed the steps above to install the pre-commit hooks, then you can just wait for those hooks to run `ruff` and `black` for you.
