import json
import logging
import os
import re
import shlex
import subprocess
import sys
import urllib
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime as dt
from textwrap import dedent

import boto3
import botocore
import humanize
import requests
from iterfzf import iterfzf
from pyquery import PyQuery as pq  # noqa: N813
from requests_kerberos import OPTIONAL, HTTPKerberosAuth
from rich import print  # noqa: A004
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
)
from tzlocal import get_localzone

from rh_aws_saml_login.utils import bye, run

SCRIPT_START_TIME = dt.now(UTC)

logger = logging.getLogger(__name__)


@dataclass
class AwsAccount:
    name: str
    uid: str
    role_name: str
    role_arn: str
    session_timeout_seconds: int
    region: str

    @property
    def principle_arn(self) -> str:
        return f"arn:aws:iam::{self.uid}:saml-provider/RedHatInternal"


@dataclass
class AwsCredentials:
    access_key: str
    secret_key: str
    session_token: str
    expiration: dt
    session_timeout_seconds: int
    region: str


def is_kerberos_ticket_valid() -> bool:
    """Test for a valid kerberos ticket."""
    try:
        run(["klist", "-s"], check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def kinit() -> None:
    """Acquire a kerberos ticket."""
    run(["kinit"], check=True, capture_output=False)


def get_saml_auth(url: str) -> tuple[str, str]:
    with requests.Session() as session:
        session.auth = HTTPKerberosAuth(mutual_authentication=OPTIONAL)
        r = session.get(url)
        r.raise_for_status()
        p = pq(r.text).xhtml_to_html()
        form = p("form")
        aws_url = form.attr("action")
        saml_token = form("input:hidden").attr("value")
    return aws_url, saml_token


def get_aws_accounts(
    aws_url: str, saml_token: str, saml_token_duration_seconds: int, region: str
) -> list[AwsAccount]:
    r = requests.post(aws_url, data={"SAMLResponse": saml_token}, timeout=10)
    r.raise_for_status()
    p = pq(r.text).xhtml_to_html()
    accounts = p("div.saml-account")
    if not accounts:
        logger.error("No AWS accounts found: %s", r.text)
        sys.exit(1)

    aws_accounts = []
    for account in accounts.items():
        name = account.find(".saml-account-name").text()
        if not name:
            continue
        # "Account: foobar (123456789)" or just with the ID "Account: 123456789"
        name = re.split(r"\s+", name)[1]
        role_labels = account.find(".saml-role").find("label")
        for role_label in role_labels.items():
            # arn:aws:iam::123456789:role/123456789-role-name
            role_arn = role_label.attr("for")
            aws_accounts.append(
                AwsAccount(
                    name=name,
                    uid=role_arn.split(":")[4],
                    role_name=role_label.text(),
                    role_arn=role_arn,
                    session_timeout_seconds=saml_token_duration_seconds,
                    region=region,
                )
            )
    return aws_accounts


def select_aws_account(
    aws_accounts: list[AwsAccount], account_name: str | None, role: str | None = None
) -> AwsAccount | None:
    return next(
        (
            a
            for a in aws_accounts
            if a.name == account_name and (not role or a.role_name == role)
        ),
        None,
    )


def get_aws_account(
    aws_accounts: list[AwsAccount], account_name: str | None
) -> AwsAccount | None:
    role = None

    if not account_name:
        items = [f"{acc.name:<40} {acc.role_name}" for acc in aws_accounts]
        selected_item = iterfzf(
            items,
            exact=True,
            __extra__=[f"--header={'Account':<40} Role"],
        )
        if not selected_item:
            sys.exit(0)
        account_name, role = re.split(r"\s+", selected_item, maxsplit=1)

    elif account_name == ".":
        # account name can be passed as a dot to open the console for the previously selected account
        account_name = os.environ.get("AWS_ACCOUNT_NAME")

    return select_aws_account(aws_accounts, account_name, role)


def assume_role_with_saml(account: AwsAccount, saml_token: str) -> AwsCredentials:
    sts = boto3.client(
        "sts",
        config=botocore.config.Config(signature_version=botocore.UNSIGNED),
        region_name=account.region,
    )
    response = sts.assume_role_with_saml(
        RoleArn=account.role_arn,
        PrincipalArn=account.principle_arn,
        SAMLAssertion=saml_token,
        DurationSeconds=account.session_timeout_seconds,
    )
    return AwsCredentials(
        access_key=response["Credentials"]["AccessKeyId"],
        secret_key=response["Credentials"]["SecretAccessKey"],
        session_token=response["Credentials"]["SessionToken"],
        expiration=response["Credentials"]["Expiration"],
        session_timeout_seconds=account.session_timeout_seconds,
        region=account.region,
    )


def assume_role(account: AwsAccount, credentials: AwsCredentials) -> AwsCredentials:
    sts = boto3.client(
        "sts",
        aws_access_key_id=credentials.access_key,
        aws_secret_access_key=credentials.secret_key,
        aws_session_token=credentials.session_token,
        region_name=account.region,
    )
    response = sts.assume_role(
        RoleArn=account.role_arn,
        RoleSessionName=account.role_name,
    )
    return AwsCredentials(
        access_key=response["Credentials"]["AccessKeyId"],
        secret_key=response["Credentials"]["SecretAccessKey"],
        session_token=response["Credentials"]["SessionToken"],
        expiration=response["Credentials"]["Expiration"],
        session_timeout_seconds=account.session_timeout_seconds,
        region=account.region,
    )


def open_aws_shell(
    account: AwsAccount,
    credentials: AwsCredentials,
    region: str,
    command: list[str] | str | None = None,
) -> None:
    if not command:
        print(
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


def main(  # noqa: PLR0917
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
