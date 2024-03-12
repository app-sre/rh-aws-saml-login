import json
import logging
from pathlib import Path

import typer
from rich import print

from rh_aws_saml_login import core
from rh_aws_saml_login.utils import blend_text, enable_requests_logging

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


def write_accounts_cache(accounts: list[str]) -> None:
    """Write accounts cache to disk."""
    json.dump(accounts, ACCOUNT_CACHE.open("w"))


def read_accounts_cache() -> list[str]:
    """Read accounts cache from disk."""
    if ACCOUNT_CACHE.exists():
        return json.load(ACCOUNT_CACHE.open())
    return []


def complete_account(ctx: typer.Context, incomplete: str):
    names = ctx.params.get("account_name") or []
    for name in read_accounts_cache():
        if name.startswith(incomplete) and name not in names:
            yield name


@app.command(epilog="Made with [red]:heart:[/] by [blue]https://github.com/app-sre[/]")
def cli(  # noqa: PLR0913, PLR0917
    account_name: str = typer.Argument(
        None,
        help="AWS account name. '.' as shortcut to use $AWS_ACCOUNT_NAME.",
        autocompletion=complete_account,
    ),
    region: str = typer.Option("us-east-1", help="AWS region"),
    debug: bool = typer.Option(False, help="Enable debug mode"),
    console: bool = typer.Option(
        False, help="Open the AWS console in browser instead of a local shell"
    ),
    display_banner: bool = typer.Option(True, help="Display a shiny banner"),
    saml_url: str = typer.Option(
        "https://auth.redhat.com/auth/realms/EmployeeIDP/protocol/saml/clients/itaws",
        help="SAML URL",
    ),
):
    """Login to AWS using SAML."""
    logging.basicConfig(
        level=logging.INFO if not debug else logging.DEBUG, format="%(message)s"
    )
    if display_banner:
        print(blend_text(BANNER, (32, 32, 255), (255, 32, 255)))
    if debug:
        enable_requests_logging()
    accounts = core.main(
        account_name=account_name, region=region, console=console, saml_url=saml_url
    )
    write_accounts_cache(accounts)


if __name__ == "__main__":
    app()
