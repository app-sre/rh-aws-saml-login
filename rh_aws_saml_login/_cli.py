import json
import logging
import os
import shlex
import sys
import urllib
from collections.abc import Generator
from datetime import UTC
from datetime import datetime as dt
from importlib.metadata import version
from pathlib import Path
from textwrap import dedent
from typing import Annotated

import humanize
import requests
import typer
from rich import print as rich_print
from rich.progress import Progress, SpinnerColumn, TextColumn
from tzlocal import get_localzone

from ._consts import RH_SAML_URL, AwsConsoleService, AwsRegion
from ._core import (
    assume_role,
    assume_role_with_saml,
    get_aws_account,
    get_aws_accounts,
    get_saml_auth,
    is_kerberos_ticket_valid,
    kinit,
)
from ._models import AwsAccount, AwsCredentials
from ._utils import blend_text, bye, enable_requests_logging, run

app = typer.Typer(rich_markup_mode="rich")
BANNER = r"""
         __                                                         __      __            _
   _____/ /_        ____ __      _______      _________ _____ ___  / /     / /___  ____ _(_)___
  / ___/ __ \______/ __ `/ | /| / / ___/_____/ ___/ __ `/ __ `__ \/ /_____/ / __ \/ __ `/ / __ \
 / /  / / / /_____/ /_/ /| |/ |/ (__  )_____(__  ) /_/ / / / / / / /_____/ / /_/ / /_/ / / / / /
/_/  /_/ /_/      \__,_/ |__/|__/____/     /____/\__,_/_/ /_/ /_/_/     /_/\____/\__, /_/_/ /_/
                                                                                /____/
"""
APP_NAME = "rh-aws-saml-login"
APP_DIR = Path(typer.get_app_dir(APP_NAME))
APP_DIR.mkdir(exist_ok=True)
ACCOUNT_CACHE = APP_DIR / "account_cache.json"

SCRIPT_START_TIME = dt.now(UTC)

logger = logging.getLogger(__name__)


def open_aws_shell(
    account: AwsAccount,
    credentials: AwsCredentials,
    region: str,
    command: list[str] | str | None = None,
) -> None:
    if not command:
        rich_print(
            dedent(f"""
            Spawning a new shell. Use exit or CTRL+d to leave it!

            :nerd_face: {account.name}
            :rocket: {account.role_name}
            :hourglass: {humanize.naturaltime(credentials.expiration, when=SCRIPT_START_TIME)} ({credentials.expiration.astimezone(tz=get_localzone())})
        """)
        )
        command = os.environ.get("SHELL", "/bin/bash")
    run(
        command,
        check=False,
        capture_output=False,
        env={
            "AWS_ACCOUNT_NAME": account.name,
            "AWS_ACCOUNT_UID": account.uid,
            "AWS_ROLE_NAME": account.role_name,
            "AWS_ROLE_ARN": account.role_arn,
            "AWS_ACCESS_KEY_ID": credentials.access_key,
            "AWS_SECRET_ACCESS_KEY": credentials.secret_key,
            "AWS_SESSION_TOKEN": credentials.session_token,
            "AWS_REGION": region,
        },
    )


def open_aws_console(
    open_command: str, credentials: AwsCredentials, console_service: str | None = None
) -> None:
    """Open the AWS console in a browser.

    See https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_enable-console-custom-url.html
    """
    aws_federated_signin_endpoint = "https://signin.aws.amazon.com/federation"
    # Get a sign-in token from the AWS sign-in federation endpoint.
    response = requests.get(
        aws_federated_signin_endpoint,
        params={
            "Action": "getSigninToken",
            "SessionDuration": str(credentials.session_timeout_seconds),
            "Session": json.dumps({
                "sessionId": credentials.access_key,
                "sessionKey": credentials.secret_key,
                "sessionToken": credentials.session_token,
            }),
        },
        timeout=10,
    )
    if response.status_code == requests.codes.BAD_REQUEST:
        logger.error(
            "Failed to get a sign-in token. Try lowering the session timeout value via --session-timeout."
        )
        sys.exit(1)

    signin_token = json.loads(response.text)
    # Make a federated URL that can be used to sign into the AWS Management Console.
    query_string = urllib.parse.urlencode({
        "Action": "login",
        "Issuer": "redhat.com",
        "Destination": f"https://{credentials.region}.console.aws.amazon.com/{console_service or ''}",
        "SigninToken": signin_token["SigninToken"],
    })
    federated_url = f"{aws_federated_signin_endpoint}?{query_string}"
    run([*shlex.split(open_command), federated_url], check=False, capture_output=False)


def write_accounts_cache(accounts: list[str]) -> None:
    """Write accounts cache to disk."""
    json.dump(accounts, ACCOUNT_CACHE.open("w"))


def read_accounts_cache() -> list[str]:
    """Read accounts cache from disk."""
    if ACCOUNT_CACHE.exists():
        return json.load(ACCOUNT_CACHE.open())
    return []


def complete_account(ctx: typer.Context, incomplete: str) -> Generator[str, None, None]:  # noqa: ARG001
    for name in read_accounts_cache():
        if name.startswith(incomplete):
            yield name


def version_callback(*, value: bool) -> None:
    if value:
        rich_print(f"Version: {version(APP_NAME)}")
        raise typer.Exit


@app.command(epilog="Made with [red]:heart:[/] by [blue]https://github.com/app-sre[/]")
def cli(  # noqa: PLR0917
    account_name: Annotated[
        str | None,
        typer.Argument(
            help="AWS account name. '.' as shortcut to use $AWS_ACCOUNT_NAME.",
            autocompletion=complete_account,
        ),
    ] = None,
    command: Annotated[list[str] | None, typer.Argument(help="Command to run")] = None,
    region: Annotated[
        AwsRegion,
        typer.Option(
            help="AWS region",
            envvar="RH_AWS_REGION",
        ),
    ] = AwsRegion.US_EAST_1,
    saml_url: Annotated[
        str,
        typer.Option(
            help="SAML URL",
        ),
    ] = RH_SAML_URL,
    session_timeout: Annotated[
        int,
        typer.Option(
            help="Session timeout in minutes. Default: 60 minutes. Max value depends on the AWS IAM role.",
            envvar="RH_AWS_SESSION_TIMEOUT",
        ),
    ] = 60,
    open_command: Annotated[
        str,
        typer.Option(
            help="Command to open the browser (e.g. 'xdg-open' on Linux)",
            envvar="RH_AWS_SAML_LOGIN_OPEN_COMMAND",
        ),
    ] = "open",
    console_service: Annotated[
        AwsConsoleService | None,
        typer.Option(
            help="Directly open this AWS console service",
            envvar="RH_AWS_CONSOLE_SERVICE",
        ),
    ] = None,
    assume_uid: Annotated[
        str | None,
        typer.Option(
            help="Define the target AWS account UID to assume",
        ),
    ] = None,
    assume_role: Annotated[
        str,
        typer.Option(
            help="Define the role name to assume",
        ),
    ] = "role/OrganizationAccountAccessRole",
    *,
    debug: Annotated[bool, typer.Option(help="Enable debug mode")] = False,
    console: Annotated[
        bool,
        typer.Option(help="Open the AWS console in browser instead of a local shell"),
    ] = False,
    display_banner: Annotated[
        bool,
        typer.Option(
            help="Display a shiny banner",
            envvar="RH_DISPLAY_BANNER",
        ),
    ] = True,
    version: Annotated[  # noqa: ARG001
        bool | None, typer.Option("--version", callback=version_callback)
    ] = None,
) -> None:
    """Login to AWS using SAML."""
    logging.basicConfig(
        level=logging.INFO if not debug else logging.DEBUG, format="%(message)s"
    )
    if display_banner:
        rich_print(blend_text(BANNER, (32, 32, 255), (255, 32, 255)))
    if debug:
        enable_requests_logging()
    accounts = _main(
        account_name=account_name,
        region=region,
        console=console,
        saml_url=saml_url,
        session_timeout_seconds=session_timeout * 60,
        command=command,
        open_command=open_command,
        console_service=console_service,
        assume_uid=assume_uid,
        assume_role_name=assume_role,
    )
    write_accounts_cache(accounts)


def _main(  # noqa: PLR0917
    account_name: str | None,
    region: str,
    saml_url: str,
    session_timeout_seconds: int,
    command: list[str] | None,
    open_command: str,
    console_service: str | None,
    assume_uid: str | None,
    assume_role_name: str,
    *,
    console: bool,
) -> list[str]:
    with Progress(
        SpinnerColumn(finished_text="✅"),
        TextColumn("[progress.description]{task.description}"),
    ) as progress:
        task = progress.add_task(
            description="Test for a valid Kerberos ticket ...", total=1
        )
        if not is_kerberos_ticket_valid():
            progress.stop()
            logger.info("No valid Kerberos ticket found. Acquiring one ...")
            kinit()
            progress.start()
        progress.update(task, completed=1)

        task = progress.add_task(description="Getting SAML token ...", total=1)
        aws_url, saml_token = get_saml_auth(saml_url)
        progress.update(task, completed=1)

        task = progress.add_task(description="Getting AWS accounts ...", total=1)
        aws_accounts = get_aws_accounts(
            aws_url, saml_token, session_timeout_seconds, region
        )

        progress.stop()
        if not (account := get_aws_account(aws_accounts, account_name)):
            logger.error("Account not found: %s", account_name)
            sys.exit(1)
        progress.start()
        progress.update(task, completed=1)

        task = progress.add_task(
            description="Getting temporary AWS credentials ...", total=1
        )
        credentials = assume_role_with_saml(account, saml_token)
        progress.update(task, completed=1)

        if assume_uid:
            account = AwsAccount(
                name=assume_uid,
                uid=assume_uid,
                role_name=account.name,
                role_arn=f"arn:aws:iam::{assume_uid}:{assume_role_name}",
                session_timeout_seconds=session_timeout_seconds,
                region=region,
            )
            task = progress.add_task(description="Assume role ...", total=1)
            credentials = assume_role(account, credentials)
            progress.update(task, completed=1)

    if console:
        open_aws_console(open_command, credentials, console_service)
    else:
        open_aws_shell(account, credentials, region, command)
    bye()
    return [acc.name for acc in aws_accounts]
