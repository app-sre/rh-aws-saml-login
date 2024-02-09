import typer
from rich import print

from rh_aws_saml_login import core
from rh_aws_saml_login.utils import blend_text

app = typer.Typer(rich_markup_mode="rich")
BANNER = r"""
         __                                                         __      __            _
   _____/ /_        ____ __      _______      _________ _____ ___  / /     / /___  ____ _(_)___
  / ___/ __ \______/ __ `/ | /| / / ___/_____/ ___/ __ `/ __ `__ \/ /_____/ / __ \/ __ `/ / __ \
 / /  / / / /_____/ /_/ /| |/ |/ (__  )_____(__  ) /_/ / / / / / / /_____/ / /_/ / /_/ / / / / /
/_/  /_/ /_/      \__,_/ |__/|__/____/     /____/\__,_/_/ /_/ /_/_/     /_/\____/\__, /_/_/ /_/
                                                                                /____/
"""


@app.command(epilog="Made with :heart: by [blue]https://github.com/app-sre[/]")
def cli(  # noqa: PLR0913, PLR0917
    account_name: str = typer.Argument(None, help="AWS account name"),
    region: str = typer.Option("us-east-1", help="AWS region"),
    debug: bool = typer.Option(False, help="Enable debug mode"),
    open_in_browser: bool = typer.Option(
        False, help="Open the AWS console in browser instead of a local shell"
    ),
    display_banner: bool = typer.Option(True, help="Display a shiny banner"),
    saml_url: str = typer.Option(
        "https://auth.redhat.com/auth/realms/EmployeeIDP/protocol/saml/clients/itaws",
        help="SAML URL",
    ),
):
    if display_banner:
        print(blend_text(BANNER, (32, 32, 255), (255, 32, 255)))
    core.main(
        account_name=account_name,
        region=region,
        debug=debug,
        open_in_browser=open_in_browser,
        saml_url=saml_url,
    )


if __name__ == "__main__":
    app()
