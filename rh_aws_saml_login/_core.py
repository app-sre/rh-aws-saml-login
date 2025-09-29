import base64
import logging
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET  # noqa: S405

import boto3
import botocore
import requests
from iterfzf import iterfzf
from pyquery import PyQuery as pq  # noqa: N813
from requests_kerberos import OPTIONAL, HTTPKerberosAuth

from ._models import AwsAccount, AwsCredentials
from ._utils import run

logger = logging.getLogger(__name__)


def is_kerberos_ticket_valid() -> bool:
    """Test for a valid kerberos ticket."""
    try:
        run(["klist", "-s"], check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def kinit(kerberos_keytab: str | None, kerberos_principal: str) -> None:
    """Acquire a kerberos ticket."""
    cmd = ["kinit"]
    with tempfile.NamedTemporaryFile() as keytab_file:
        if kerberos_keytab:
            # decode base64 keytab file and write it to a temporary file
            keytab_file.write(base64.b64decode(kerberos_keytab))
            keytab_file.flush()
            cmd += ["-kt", keytab_file.name]
        run([*cmd, kerberos_principal], check=True, capture_output=False)


def get_saml_auth(url: str) -> tuple[str, str]:
    """Get the SAML token and AWS authentification URL."""
    with requests.Session() as session:
        session.auth = HTTPKerberosAuth(mutual_authentication=OPTIONAL)
        r = session.get(url)
        r.raise_for_status()
        p = pq(r.text).xhtml_to_html()
        form = p("form")
        aws_url = form.attr("action")
        saml_token = form("input:hidden").attr("value")
    return aws_url, saml_token


def get_single_account_from_saml(saml_token: str) -> AwsAccount | None:
    """Return an AWS account from the SAML token if exactly one role is found."""
    saml_response_xml = base64.b64decode(saml_token).decode("utf-8")
    root = ET.fromstring(saml_response_xml)  # noqa: S314
    namespaces = {
        "samlp": "urn:oasis:names:tc:SAML:2.0:protocol",
        "saml": "urn:oasis:names:tc:SAML:2.0:assertion",
    }
    if (
        role_attribute := root.find(
            ".//saml:Attribute[@Name='https://aws.amazon.com/SAML/Attributes/Role']",
            namespaces,
        )
    ) is None:
        msg = "No role attribute found in SAML response"
        raise ValueError(msg)

    role_values = role_attribute.findall("./saml:AttributeValue", namespaces)

    if len(role_values) == 1:
        # Exactly one role found
        if (role_value_element := role_values[0]) is None:
            msg = "No role value found in SAML response"
            raise ValueError(msg)
        if not role_value_element.text:
            msg = "Empty role value found in SAML response"
            raise ValueError(msg)

        role_arn = role_value_element.text.split(",")[0]

        arn_parts = role_arn.split(":")
        return AwsAccount(
            # the SAML response does not provide a friendly name, so we use the account ID and role name
            name=arn_parts[4],
            uid=arn_parts[4],
            role_name=arn_parts[5].split("/")[1],
            role_arn=role_arn,
        )
    return None


def get_aws_accounts(
    aws_url: str, saml_token: str, saml_token_duration_seconds: int, region: str
) -> list[AwsAccount]:
    """Get all AWS accounts accessible to the user."""
    # The AWS SAML login page redirects directly to the account console when only one account is found.
    # Unfortunately, the SAML token does not contain the account names.
    # So we stick with the AWS SAML login html parsing if the user has multiple accounts.
    if aws_account := get_single_account_from_saml(saml_token):
        aws_account.session_timeout_seconds = saml_token_duration_seconds
        aws_account.region = region
        return [aws_account]

    r = requests.post(aws_url, data={"SAMLResponse": saml_token}, timeout=10)
    r.raise_for_status()

    p = pq(r.text).xhtml_to_html()
    accounts = p("div.saml-account")
    if not accounts:
        errormsg = f"No AWS accounts found: {r.text}"
        logger.error(errormsg)
        raise ValueError(errormsg)

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
    aws_accounts: list[AwsAccount], account_name: str, role: str | None = None
) -> AwsAccount | None:
    """Select an AWS account from the list of available accounts."""
    return next(
        (
            a
            for a in aws_accounts
            if a.name == account_name and (not role or a.role_name == role)
        ),
        None,
    )


def get_aws_account(
    aws_accounts: list[AwsAccount], account_name: str | None, role: str | None = None
) -> AwsAccount | None:
    """Select and return an AWS account from the list of available accounts."""
    if len(aws_accounts) == 1:
        return aws_accounts[0]

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

    if account_name == ".":
        # account name can be passed as a dot to open the console for the previously selected account
        account_name = os.environ.get("AWS_ACCOUNT_NAME")

    assert account_name  # make mypy happy
    return select_aws_account(aws_accounts, account_name, role)


def assume_role_with_saml(account: AwsAccount, saml_token: str) -> AwsCredentials:
    """Assume a role with SAML token."""
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
    """Assume a role with the given credentials."""
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
