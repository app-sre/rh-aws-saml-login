from collections.abc import Callable
from pathlib import Path

import pytest
from requests_mock import Mocker as RequestsMocker

from rh_aws_saml_login.core import (
    AwsAccount,
    get_aws_accounts,
    get_saml_auth,
    select_aws_account,
)


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
        ),
        AwsAccount(
            name="account-1",
            uid="1234567890",
            role_name="read-only",
            role_arn="arn:aws:iam::1234567890:role/read-only",
        ),
        AwsAccount(
            name="account-2",
            uid="5432167890",
            role_name="admin-role",
            role_arn="arn:aws:iam::5432167890:role/admin-role",
        ),
        AwsAccount(
            name="987654321",
            uid="987654321",
            role_name="987654321-admin",
            role_arn="arn:aws:iam::987654321:role/987654321-admin",
        ),
    ]


def test_get_saml_auth(requests_mock: RequestsMocker, fx: Callable) -> None:
    """Test get_saml_auth."""
    url = "https://example.com"

    requests_mock.get(url, text=fx("saml.html"))
    aws_url, saml_token = get_saml_auth(url)
    assert aws_url == "http://localhost:8000/aws-sso.html"
    assert saml_token == "fake-saml-token"  # noqa: S105


def test_get_aws_accounts(
    requests_mock: RequestsMocker, fx: Callable, accounts: list[AwsAccount]
) -> None:
    """Test get_aws_accounts."""
    url = "https://example.com"
    saml_token = "fake-saml"  # noqa: S105
    requests_mock.post(url, text=fx("aws-sso.html"))

    assert get_aws_accounts(url, saml_token) == accounts


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
