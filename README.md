# rh-aws-saml-login

[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![PyPI](https://img.shields.io/pypi/v/rh-aws-saml-login)][pypi-link]
[![PyPI platforms][pypi-platforms]][pypi-link]
![PyPI - License](https://img.shields.io/pypi/l/rh-aws-saml-login)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)

A CLI tool that allows you to log in and retrieve AWS temporary credentials using Red Hat SAML IDP.

![demo](/demo/quickstart.gif)

## Pre-requisites

- Python 3.11 or later
- Connected to Red Hat VPN
- A Red Hat managed computer (Kerberos must be installed and configured) and you are logged in with your Red Hat account

## How it works

The `rh-aws-saml-login` CLI is a tool that simplifies the process of logging into an AWS account via Red Hat SSO. It retrieves a SAML token from the Red Hat SSO server, then fetches and parses the AWS SSO login page to present you with a list of all available accounts and their respective roles. You can then choose your desired account and role, and `rh-aws-saml-login` uses the SAML token to generate temporary AWS role credentials. Finally, it spawns a new shell with the necessary `AWS_` environment variables already set up, so you can immediately use the `aws` CLI without any further configuration.

## Installation

### Prerequisites

`rh-aws-saml-login` needs the `krb5` library to work. On most system, e.g., MacOS, this library is already installed. On CSB Fedora, you need to install the Kerberos development package:

```shell
sudo dnf install krb5-devel
```

### Recommended Installation Method

The recommended way to install `rh-aws-saml-login` is to use the [uv](https://docs.astral.sh/uv/) tool:

```shell
uv tool install rh-aws-saml-login
```

and upgrade an existing installation with:

```shell
uv tool upgrade rh-aws-saml-login
```

### Alternative Installation Methods

You can install this library from [PyPI][pypi-link] with `pip`:

```shell
python3 -m pip install rh-aws-saml-login
```

or install it with `pipx`:

```shell
pipx install rh-aws-saml-login
```

and upgrade an existing installation with:

```shell
pipx upgrade rh-aws-saml-login
```

## Usage

### Interactive mode

Just run `rh-aws-saml-login` to start the interactive mode. It will list all available AWS accounts and roles, and you can choose the one you want to log in to:

```shell
$ rh-aws-saml-login

         __                                                         __      __            _
   _____/ /_        ____ __      _______      _________ _____ ___  / /     / /___  ____ _(_)___
  / ___/ __ \______/ __ `/ | /| / / ___/_____/ ___/ __ `/ __ `__ \/ /_____/ / __ \/ __ `/ / __ \
 / /  / / / /_____/ /_/ /| |/ |/ (__  )_____(__  ) /_/ / / / / / / /_____/ / /_/ / /_/ / / / / /
/_/  /_/ /_/      \__,_/ |__/|__/____/     /____/\__,_/_/ /_/ /_/_/     /_/\____/\__, /_/_/ /_/
                                                                                /____/

✅ Test for a valid Kerberos ticket ...
✅ Getting SAML token ...
✅ Getting AWS accounts ...
✅ Getting temporary AWS credentials ...

Spawning a new shell. Use exit or CTRL+d to leave it!

🤓 app-sre
🚀 1234567890-app-sre
⌛ 59 minutes from now (2024-10-07 11:16:54+02:00)

$ aws s3 ls
...
```

This spawns a new shell with all required AWS environment variables set. See the [Environment Variables](#environment-variables) section for more information.

### Non-interactive mode

Instead of running the interactive mode, you can also use `rh-aws-saml-login` to run any arbitrary command with the AWS environment variables set:

```shell
rh-aws-saml-login <ACCOUNT_NAME> -- <COMMAND> [ARGUMENTS]
```

For example:

```shell
$ rh-aws-saml-login app-sre-stage -- aws s3 ls

         __                                                         __      __            _
   _____/ /_        ____ __      _______      _________ _____ ___  / /     / /___  ____ _(_)___
  / ___/ __ \______/ __ `/ | /| / / ___/_____/ ___/ __ `/ __ `__ \/ /_____/ / __ \/ __ `/ / __ \
 / /  / / / /_____/ /_/ /| |/ |/ (__  )_____(__  ) /_/ / / / / / / /_____/ / /_/ / /_/ / / / / /
/_/  /_/ /_/      \__,_/ |__/|__/____/     /____/\__,_/_/ /_/ /_/_/     /_/\____/\__, /_/_/ /_/
                                                                                /____/

✅ Test for a valid Kerberos ticket ...
✅ Getting SAML token ...
✅ Getting AWS accounts ...
✅ Getting temporary AWS credentials ...
2022-05-17 13:48:49 bucket-name-stage
2022-12-13 13:21:02 bucket-name-tfstate-stage
Thank you for using rh-aws-saml-login. 🙇‍♂️ Have a great day ahead! ❤️
```

## Environment Variables

`rh-aws-saml-login` sets the following environment variables:

- `AWS_ACCOUNT_NAME`: The name/alias of the AWS account
- `AWS_ROLE_NAME`:  The name of the role
- `AWS_ROLE_ARN`: The ARN of the role
- `AWS_ACCESS_KEY_ID`: The access key used by the AWS CLI
- `AWS_SECRET_ACCESS_KEY`: The secret access key used by the AWS CLI
- `AWS_SESSION_TOKEN`: The session token used by the AWS CLI
- `AWS_REGION`: The default region used by the AWS CLI

## Features

`rh-aws-saml-login` currently provides the following features (get help with `-h` or `--help`):

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

- Update CHANGELOG.md with the new version number and date
- Bump the version number in [pyproject.toml](/pyproject.toml)

[pypi-link]:                https://pypi.org/project/rh-aws-saml-login/
[pypi-platforms]:           https://img.shields.io/pypi/pyversions/rh-aws-saml-login
