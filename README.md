# rh-aws-saml-login

[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![PyPI](https://img.shields.io/pypi/v/rh-aws-saml-login)][pypi-link]
[![PyPI platforms][pypi-platforms]][pypi-link]
![PyPI - License](https://img.shields.io/pypi/l/rh-aws-saml-login)

A CLI tool that allows you to log in and retrieve AWS temporary credentials using Red Hat SAML IDP.

![demo](/demo/quickstart.gif)

## Pre-requisites

- Python 3.11 or later
- Connected to Red Hat VPN
- A Red Hat managed computer (Kerberos must be installed and configured) and you are logged in with your Red Hat account

## How it works

The `rh-aws-saml-login` CLI is a tool that simplifies the process of logging into an AWS account via Red Hat SSO. It retrieves a SAML token from the Red Hat SSO server, then fetches and parses the AWS SSO login page to present you with a list of all available accounts and their respective roles. You can then choose your desired account and role, and `rh-aws-saml-login` uses the SAML token to generate temporary AWS role credentials. Finally, it spawns a new shell with the necessary `AWS_` environment variables already set up, so you can immediately use the `aws` CLI without any further configuration.

## Installation

On CSB Fedora, you need to install the Kerberos development package:

```shell
sudo dnf install krb5-devel
```

You can install this library from [PyPI][pypi-link] with `pip`:

```shell
python3 -m pip install rh-aws-saml-login
```

or install it with `pipx`:

```shell
pipx install rh-aws-saml-login
```

You can also use `pipx` to run the library without installing it:

```shell
pipx run rh-aws-saml-login
```

## Usage

```shell
rh-aws-saml-login
```

This spawns a new shell with the following environment variables are set:

- `AWS_ACCOUNT_NAME`: The name/alias of the AWS account
- `AWS_ROLE_NAME`:  The name of the role
- `AWS_ROLE_ARN`: The ARN of the role
- `AWS_ACCESS_KEY_ID`: The access key used by the AWS CLI
- `AWS_SECRET_ACCESS_KEY`: The secret access key used by the AWS CLI
- `AWS_SESSION_TOKEN`: The session token used by the AWS CLI
- `AWS_REGION`: The default region used by the AWS CLI

## Features

rh-aws-saml-login currently provides the following features (get help with `-h` or `--help`):

- No configuration needed
- Uses Kerberos authentication
- Open the AWS web console for an account with the `--console` option
- Shell auto-completion (bash, zsh, and fish) including AWS account names
- Integrates nicely with the [starship](https://starship.rs)

  ```toml
   [env_var.AWS_ACCOUNT_NAME]
   format = "$symbol$style [$env_value]($style) "
   style = "cyan"
   symbol = "🚀"
  ```

## Development

[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)

- Update CHANGELOG.md with the new version number and date
- Bump the version number in [pyproject.toml](/pyproject.toml)

[pypi-link]:                https://pypi.org/project/rh-aws-saml-login/
[pypi-platforms]:           https://img.shields.io/pypi/pyversions/rh-aws-saml-login
