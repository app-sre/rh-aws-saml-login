# Changelog

## 0.10.0

### Features

* **Display AWS credentials**: Add `--output` option to retrieve AWS credentials in different formats (json, env).

### Bug Fixes

* Fix Keytab support for Kerberos authentication.

## 0.9.0

### Features

* **Kerberos Keytab support**: Add support for granting Kerberos tickets using a keytab file. Supply the keytab file as a base64 encoded string via the `RH_KERBEROS_KEYTAB` environment variable or the `--kerberos-keytab` option.
* **Environment Variables**: Add `RH_KERBEROS_KEYTAB` and `RH_KERBEROS_PRINCIPAL` environment variables for Kerberos authentication.

### Chore

* Upgrade dependencies

## 0.8.4

### Features

* Add support for `mx-central-1` AWS region.

### Chore

* Consolidate README for Fedora library requirements

## 0.8.3

### Chore

* Upgrade dependencies

## 0.8.2

### Chore

* Pin `click`

## 0.8.1

### Features

* `AWS_ACCOUNT_UID` environment variable

## 0.8.0

### Features

* Jupyter notebook support (#149)

### Chore

* Upgrade dependencies

## 0.7.0

### Features

* **Assume role** Add `--assume-uid` and `--assume-role` options to assume a role in another account.
* **Console** Add `--console-service` option (env `RH_AWS_CONSOLE_SERVICE`) to open the AWS web console for a specific AWS service. Default is still the AWS console dashboard.
* **Environment Variables** Add `RH_DISPLAY_BANNER` (option `--display-banner/--no-display-banner` ) and `RH_AWS_REGION` (option `--region`) environment variables.
* **Shell completion** Add shell completion for the `--region` and `--console-service` options.

### Bug Fixes

* Honor `--region` option for the AWS console URL
* Fix "Account not found" error message

### Chore

* Upgrade dependencies

## 0.6.1

### Chore

* Use Konflux for the release process
* Upgrade dependencies

## 0.6.0

### Features

* `--session-timeout` option to set the session timeout in minutes. Also available as the `RH_AWS_SESSION_TIMEOUT` environment variable.

## 0.5.0

### Features

* **Non-interactive mode**: Run any arbitrary command with the AWS environment variables set.

## 0.4.2

### Features

* More PyPI metadata
* Release binary wheels for Linux and macOS

## 0.4.1

### Bug Fixes

* Do not release a whell due to a `uv` bug

## 0.4.0

### Bug Fixes

* Fix kerberos ticket test on Linux ([#18](https://github.com/app-sre/rh-aws-saml-login/issues/18))

### Features

* Add `--version` option ([#16](https://github.com/app-sre/rh-aws-saml-login/issues/16))

### Chore

* Mention [uv](https://docs.astral.sh/uv/) as the recommended installation method.
* Replace poetry with [uv](https://docs.astral.sh/uv/) for the project management.
* Upgrade dependencies

## 0.3.4

* Upgrade dependencies

## 0.3.3

* Upgrade dependencies

## 0.3.2

* `--open-command` option to open the AWS web console with a custom command.

## 0.3.1

### Chore

* Upgrade dependencies

## 0.3.0

### Features

* **AWS account name shell completion**: Add shell completion (bash/zsh/fish) for AWS account names.

### Bug Fixes

* Fix project URLs in [PyPI](https://pypi.org/project/rh-aws-saml-login/)

## 0.2.0 (2024-02-13)

### Features

* **open AWS web console:** `--console` option to open the AWS web console for an account.

## 0.1.1 (2024-02-13)

### Bug Fixes

* **kinit:** fix hidden password prompt

## 0.1.0 (2024-02-12)

* Initial release
