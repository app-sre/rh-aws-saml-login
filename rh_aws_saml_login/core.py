import json
import logging
import os
import re
import subprocess
import sys
import urllib
from dataclasses import dataclass
from datetime import datetime as dt
from textwrap import dedent

import boto3
import botocore
import humanize
import requests
from iterfzf import iterfzf
from pyquery import PyQuery as pq
from requests_kerberos import OPTIONAL, HTTPKerberosAuth
from rich import print
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
)
from tzlocal import get_localzone

from rh_aws_saml_login.utils import bye, run


@dataclass
class AwsAccount:
    name: str
    uid: str
    role_name: str
    role_arn: str

    @property
    def principle_arn(self) -> str:
        return f"arn:aws:iam::{self.uid}:saml-provider/RedHatInternal"


@dataclass
class AwsCredentials:
    access_key: str
    secret_key: str
    session_token: str
    expiration: dt


def is_kerberos_ticket_valid() -> bool:
    """Test for a valid kerberos ticket."""
    try:
        run(["klist", "--test"], check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def kinit():
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


def get_aws_accounts(aws_url: str, saml_token: str) -> list[AwsAccount]:
    r = requests.post(aws_url, data={"SAMLResponse": saml_token})
    r.raise_for_status()
    p = pq(r.text).xhtml_to_html()
    accounts = p("div.saml-account")
    if not accounts:
        logging.error("No AWS accounts found: %s", r.text)
        sys.exit(1)

    aws_accounts = []
    for account in accounts.items():
        name = account.find(".saml-account-name").text()
        if not name:
            continue
        # "Account: foobar (123456789)" or "Account: 123456789"
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
                )
            )
    return aws_accounts


def select_aws_account(
    aws_accounts: list[AwsAccount], account_name: str | None, role: str | None = None
) -> AwsAccount | None:
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
    account = next(
        (
            a
            for a in aws_accounts
            if a.name == account_name and (not role or a.role_name == role)
        ),
        None,
    )
    return account


def assume_role_with_saml(account: AwsAccount, saml_token: str) -> AwsCredentials:
    sts = boto3.client(
        "sts", config=botocore.config.Config(signature_version=botocore.UNSIGNED)
    )
    response = sts.assume_role_with_saml(
        RoleArn=account.role_arn,
        PrincipalArn=account.principle_arn,
        SAMLAssertion=saml_token,
    )
    return AwsCredentials(
        access_key=response["Credentials"]["AccessKeyId"],
        secret_key=response["Credentials"]["SecretAccessKey"],
        session_token=response["Credentials"]["SessionToken"],
        expiration=response["Credentials"]["Expiration"],
    )


def open_aws_shell(account: AwsAccount, credentials: AwsCredentials, region: str):
    print(
        dedent(f"""
            Spawning a new shell. Use exit or CTRL+d to leave it!

            :nerd_face: {account.name}
            :rocket: {account.role_name}
            :hourglass: {humanize.naturaltime(credentials.expiration)} ({credentials.expiration.astimezone(tz=get_localzone())})
        """)
    )
    run(
        os.environ["SHELL"],
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


def open_aws_console(account: AwsAccount, credentials: AwsCredentials) -> None:
    """Open the AWS console in a browser.

    See https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_enable-console-custom-url.html
    """
    aws_federated_signin_endpoint = "https://signin.aws.amazon.com/federation"
    # Get a sign-in token from the AWS sign-in federation endpoint.
    response = requests.get(
        aws_federated_signin_endpoint,
        params={
            "Action": "getSigninToken",
            # 12 hours
            "SessionDuration": "43200",
            "Session": json.dumps({
                "sessionId": credentials.access_key,
                "sessionKey": credentials.secret_key,
                "sessionToken": credentials.session_token,
            }),
        },
    )
    signin_token = json.loads(response.text)

    # Make a federated URL that can be used to sign into the AWS Management Console.
    query_string = urllib.parse.urlencode({
        "Action": "login",
        "Issuer": "redhat.com",
        "Destination": "https://console.aws.amazon.com/",
        "SigninToken": signin_token["SigninToken"],
    })
    federated_url = f"{aws_federated_signin_endpoint}?{query_string}"
    run(["open", federated_url], check=False, capture_output=False)


def main(  # noqa: PLR0913, PLR0917
    account_name: str | None, region: str, console: bool, saml_url: str
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
            logging.info("No valid Kerberos ticket found. Acquiring one ...")
            kinit()
            progress.start()
        progress.update(task, completed=1)

        task = progress.add_task(description="Getting SAML token ...", total=1)
        aws_url, saml_token = get_saml_auth(saml_url)
        progress.update(task, completed=1)

        task = progress.add_task(description="Getting AWS accounts ...", total=1)
        aws_accounts = get_aws_accounts(aws_url, saml_token)

        progress.stop()
        if account_name == ".":
            # account name can be passed as a dot to open the console for the previously selected account
            account_name = os.environ.get("AWS_ACCOUNT_NAME")
        account = select_aws_account(aws_accounts, account_name)
        progress.start()
        if not account:
            logging.error("Account not found: %s", account_name)
            sys.exit(1)

        progress.update(task, completed=1)

        task = progress.add_task(
            description="Getting temporary AWS credentials ...", total=1
        )
        credentials = assume_role_with_saml(account, saml_token)
        progress.update(task, completed=1)

    if console:
        open_aws_console(account, credentials)
    else:
        open_aws_shell(account, credentials, region)
    bye()
    return [acc.name for acc in aws_accounts]
