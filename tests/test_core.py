"""Tests for the core module."""

# ruff: file-ignore[import-private-name]
import base64
from collections.abc import Callable
from datetime import UTC
from datetime import datetime as dt
from pathlib import Path
from typing import Any
from unittest import mock

import boto3
import pytest
from botocore.exceptions import ClientError
from botocore.stub import Stubber
from requests_mock import Mocker as RequestsMocker

from rh_aws_saml_login._core import (
    assume_role,
    assume_role_with_saml,
    get_aws_accounts,
    get_saml_auth,
    select_aws_account,
)
from rh_aws_saml_login._models import AwsAccount, AwsCredentials


@pytest.fixture
def fx() -> Callable:
    """Return a function to read fixture files."""

    def _fx(filename: str) -> str:
        return Path(f"tests/fixtures/{filename}").read_text(encoding="locale")

    return _fx


@pytest.fixture
def accounts() -> list[AwsAccount]:
    """Return a list of AwsAccount objects."""
    return [
        AwsAccount(
            name="account-1",
            uid="1234567890",
            role_name="admin-role",
            role_arn="arn:aws:iam::1234567890:role/admin-role",
            session_timeout_seconds=60,
            region="us-east-1",
        ),
        AwsAccount(
            name="account-1",
            uid="1234567890",
            role_name="read-only",
            role_arn="arn:aws:iam::1234567890:role/read-only",
            session_timeout_seconds=60,
            region="us-east-1",
        ),
        AwsAccount(
            name="account-2",
            uid="5432167890",
            role_name="admin-role",
            role_arn="arn:aws:iam::5432167890:role/admin-role",
            session_timeout_seconds=60,
            region="us-east-1",
        ),
        AwsAccount(
            name="987654321",
            uid="987654321",
            role_name="987654321-admin",
            role_arn="arn:aws:iam::987654321:role/987654321-admin",
            session_timeout_seconds=60,
            region="us-east-1",
        ),
    ]


SAML_TOKEN_MULTIPLE_ACCOUNTS = base64.b64encode(b"""
<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol" xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion">
    <saml:Assertion>
        <saml:AttributeStatement>
            <saml:Attribute Name="https://aws.amazon.com/SAML/Attributes/Role">
                <saml:AttributeValue>arn:aws:iam::111111111111:role/SAML-PowerUser-Role,arn:aws:iam::111111111111:saml-provider/MyIDProvider</saml:AttributeValue>
                <saml:AttributeValue>arn:aws:iam::222222222222:role/SAML-PowerUser-Role,arn:aws:iam::222222222222:saml-provider/MyIDProvider</saml:AttributeValue>
            </saml:Attribute>
        </saml:AttributeStatement>
    </saml:Assertion>
</samlp:Response>
""").decode("utf-8")
SAML_TOKEN_SINGLE_ACCOUNT = base64.b64encode(b"""
<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol" xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion">
    <saml:Assertion>
        <saml:AttributeStatement>
            <saml:Attribute Name="https://aws.amazon.com/SAML/Attributes/Role">
                <saml:AttributeValue>arn:aws:iam::111111111111:role/SAML-PowerUser-Role,arn:aws:iam::111111111111:saml-provider/MyIDProvider</saml:AttributeValue>
            </saml:Attribute>
        </saml:AttributeStatement>
    </saml:Assertion>
</samlp:Response>
""").decode("utf-8")


def test_get_saml_auth(requests_mock: RequestsMocker, fx: Callable) -> None:
    """Test get_saml_auth."""
    url = "https://example.com"

    requests_mock.get(url, text=fx("saml.html"))
    aws_url, saml_token = get_saml_auth(url)
    assert aws_url == "http://localhost:8000/aws-sso.html"
    assert saml_token == "fake-saml-token"  # ruff: ignore[hardcoded-password-string]


def test_get_aws_accounts(
    requests_mock: RequestsMocker, fx: Callable, accounts: list[AwsAccount]
) -> None:
    """Test get_aws_accounts."""
    url = "https://example.com"
    requests_mock.post(url, text=fx("aws-sso.html"))

    assert (
        get_aws_accounts(
            url,
            SAML_TOKEN_MULTIPLE_ACCOUNTS,
            saml_token_duration_seconds=60,
            region="us-east-1",
        )
        == accounts
    )


def test_get_aws_accounts_single(requests_mock: RequestsMocker, fx: Callable) -> None:
    """Test get_aws_accounts."""
    url = "https://example.com"
    requests_mock.post(url, text=fx("aws-sso.html"))

    assert get_aws_accounts(
        url,
        SAML_TOKEN_SINGLE_ACCOUNT,
        saml_token_duration_seconds=60,
        region="us-east-1",
    ) == [
        AwsAccount(
            name="111111111111",
            uid="111111111111",
            role_name="SAML-PowerUser-Role",
            role_arn="arn:aws:iam::111111111111:role/SAML-PowerUser-Role",
            session_timeout_seconds=60,
            region="us-east-1",
        )
    ]


def test_select_aws_account(accounts: list[AwsAccount]) -> None:
    """Test select_aws_account."""
    account = select_aws_account(accounts, "account-1", "read-only")
    assert account == accounts[1]

    account = select_aws_account(accounts, "account-1")
    assert account == accounts[0]

    account = select_aws_account(accounts, "account-1", "non-existent-role")
    assert not account
    account = select_aws_account(accounts, "non-existent-account")
    assert not account
    account = select_aws_account(accounts, "non-existent-account", "non-existent-role")
    assert not account


@pytest.fixture
def sts_stubber(monkeypatch: pytest.MonkeyPatch) -> Stubber:
    """Patch the boto3 client used by _core with a stubbed STS client."""
    client = boto3.client("sts", region_name="us-east-1")
    stubber = Stubber(client)
    stubber.activate()
    mock_boto3 = mock.Mock()
    mock_boto3.client.return_value = client
    monkeypatch.setattr("rh_aws_saml_login._core.boto3", mock_boto3)
    return stubber


@pytest.fixture
def sts_credentials() -> dict[str, Any]:
    """Return a fake STS credentials response block."""
    return {
        "AccessKeyId": "ASIAEXAMPLEACCESSKEY",
        "SecretAccessKey": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        "SessionToken": "EXAMPLESESSIONTOKEN",
        "Expiration": dt(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
    }


@pytest.fixture
def sts_account() -> AwsAccount:
    """Return an AWS account with a session timeout valid for STS parameter validation."""
    return AwsAccount(
        name="account-1",
        uid="1234567890",
        role_name="admin-role",
        role_arn="arn:aws:iam::1234567890:role/admin-role",
        session_timeout_seconds=900,
        region="us-east-1",
    )


@pytest.fixture
def first_hop_credentials(sts_account: AwsAccount) -> AwsCredentials:
    """Return credentials as returned by a first-hop AssumeRoleWithSAML call."""
    account = sts_account
    return AwsCredentials(
        access_key="ASIAEXAMPLEACCESSKEY",
        secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",  # ruff: ignore[hardcoded-password-func-arg]
        session_token="EXAMPLESESSIONTOKEN",  # ruff: ignore[hardcoded-password-func-arg]
        expiration=dt(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
        session_timeout_seconds=account.session_timeout_seconds,
        region=account.region,
        assumed_role_user_arn=f"arn:aws:sts::{account.uid}:assumed-role/{account.role_name}/khnguyen",
        assumed_role_user_id=f"AROAEXAMPLE:{account.role_name}",
    )


def test_assume_role_with_saml_preserves_user_identity(
    sts_stubber: Stubber, sts_credentials: dict[str, Any], sts_account: AwsAccount
) -> None:
    """Test that the user identity of the first-hop SAML response is retained."""
    account = sts_account
    assumed_role_user_arn = (
        f"arn:aws:sts::{account.uid}:assumed-role/{account.role_name}/khnguyen"
    )
    sts_stubber.add_response(
        "assume_role_with_saml",
        {
            "Credentials": sts_credentials,
            "AssumedRoleUser": {
                "Arn": assumed_role_user_arn,
                "AssumedRoleId": f"AROAEXAMPLE:{account.role_name}",
            },
            "SourceIdentity": "khnguyen@redhat.com",
        },
        expected_params={
            "RoleArn": account.role_arn,
            "PrincipalArn": account.principle_arn,
            "SAMLAssertion": "saml-token",
            "DurationSeconds": account.session_timeout_seconds,
        },
    )
    credentials = assume_role_with_saml(account, "saml-token")
    assert credentials.assumed_role_user_arn == assumed_role_user_arn
    assert credentials.assumed_role_user_id == f"AROAEXAMPLE:{account.role_name}"
    assert credentials.source_identity == "khnguyen@redhat.com"
    assert credentials.user_identity == "khnguyen@redhat.com"


def test_assume_role_uses_user_identity_as_session_name(
    sts_stubber: Stubber,
    sts_credentials: dict[str, Any],
    sts_account: AwsAccount,
    first_hop_credentials: AwsCredentials,
) -> None:
    """Test that assume_role uses the first-hop user identity as RoleSessionName."""
    account = sts_account
    assumed_role_user_arn = f"arn:aws:sts::{account.uid}:assumed-role/OrganizationAccountAccessRole/khnguyen"
    sts_stubber.add_response(
        "assume_role",
        {
            "Credentials": sts_credentials,
            "AssumedRoleUser": {
                "Arn": assumed_role_user_arn,
                "AssumedRoleId": "AROAEXAMPLE:khnguyen",
            },
        },
        expected_params={
            "RoleArn": account.role_arn,
            "RoleSessionName": "khnguyen",
        },
    )
    credentials = assume_role(account, first_hop_credentials)
    assert credentials.access_key == "ASIAEXAMPLEACCESSKEY"
    assert credentials.assumed_role_user_arn == assumed_role_user_arn
    assert credentials.source_identity is None


def test_assume_role_propagates_source_identity(
    sts_stubber: Stubber,
    sts_credentials: dict[str, Any],
    sts_account: AwsAccount,
    first_hop_credentials: AwsCredentials,
) -> None:
    """Test that assume_role propagates the first-hop SourceIdentity."""
    account = sts_account
    first_hop_credentials.source_identity = "khnguyen@redhat.com"
    sts_stubber.add_response(
        "assume_role",
        {
            "Credentials": sts_credentials,
            "AssumedRoleUser": {
                "Arn": "arn:aws:sts::1234567890:assumed-role/OrganizationAccountAccessRole/khnguyen@redhat.com",
                "AssumedRoleId": "AROAEXAMPLE:khnguyen@redhat.com",
            },
            "SourceIdentity": "khnguyen@redhat.com",
        },
        expected_params={
            "RoleArn": account.role_arn,
            "RoleSessionName": "khnguyen@redhat.com",
            "SourceIdentity": "khnguyen@redhat.com",
        },
    )
    credentials = assume_role(account, first_hop_credentials)
    assert credentials.source_identity == "khnguyen@redhat.com"


def test_assume_role_falls_back_to_role_name(
    sts_stubber: Stubber,
    sts_credentials: dict[str, Any],
    sts_account: AwsAccount,
    first_hop_credentials: AwsCredentials,
) -> None:
    """Test that assume_role falls back to the role name without a user identity."""
    account = sts_account
    first_hop_credentials.assumed_role_user_arn = None
    first_hop_credentials.assumed_role_user_id = None
    sts_stubber.add_response(
        "assume_role",
        {
            "Credentials": sts_credentials,
            "AssumedRoleUser": {
                "Arn": f"arn:aws:sts::{account.uid}:assumed-role/{account.role_name}/admin-role",
                "AssumedRoleId": f"AROAEXAMPLE:{account.role_name}",
            },
        },
        expected_params={
            "RoleArn": account.role_arn,
            "RoleSessionName": account.role_name,
        },
    )
    credentials = assume_role(account, first_hop_credentials)
    assert credentials.access_key == "ASIAEXAMPLEACCESSKEY"


def test_assume_role_retries_without_source_identity_on_access_denied(
    sts_stubber: Stubber,
    sts_credentials: dict[str, Any],
    sts_account: AwsAccount,
    first_hop_credentials: AwsCredentials,
) -> None:
    """Test that assume_role retries without SourceIdentity if the role's trust policy rejects it."""
    account = sts_account
    first_hop_credentials.source_identity = "khnguyen@redhat.com"
    sts_stubber.add_client_error(
        "assume_role",
        service_error_code="AccessDenied",
        service_message="not authorized to perform: sts:SetSourceIdentity",
        expected_params={
            "RoleArn": account.role_arn,
            "RoleSessionName": "khnguyen@redhat.com",
            "SourceIdentity": "khnguyen@redhat.com",
        },
    )
    sts_stubber.add_response(
        "assume_role",
        {
            "Credentials": sts_credentials,
            "AssumedRoleUser": {
                "Arn": "arn:aws:sts::1234567890:assumed-role/OrganizationAccountAccessRole/khnguyen@redhat.com",
                "AssumedRoleId": "AROAEXAMPLE:khnguyen@redhat.com",
            },
        },
        expected_params={
            "RoleArn": account.role_arn,
            "RoleSessionName": "khnguyen@redhat.com",
        },
    )
    credentials = assume_role(account, first_hop_credentials)
    assert credentials.access_key == "ASIAEXAMPLEACCESSKEY"
    assert credentials.source_identity is None


def test_assume_role_raises_on_unrelated_access_denied(
    sts_stubber: Stubber,
    sts_account: AwsAccount,
    first_hop_credentials: AwsCredentials,
) -> None:
    """Test that assume_role re-raises AccessDenied errors unrelated to SourceIdentity."""
    account = sts_account
    sts_stubber.add_client_error(
        "assume_role",
        service_error_code="AccessDenied",
        service_message="not authorized to perform: sts:AssumeRole",
        expected_params={
            "RoleArn": account.role_arn,
            "RoleSessionName": "khnguyen",
        },
    )
    with pytest.raises(ClientError):
        assume_role(account, first_hop_credentials)
