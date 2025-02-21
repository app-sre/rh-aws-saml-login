"""Test all public API methods are available."""
# ruff: noqa: D103, PLC0415

from dataclasses import is_dataclass


def test_public_get_aws_credentials() -> None:
    from rh_aws_saml_login import get_aws_credentials

    assert callable(get_aws_credentials)


def test_public_exceptions() -> None:
    from rh_aws_saml_login import NoAwsAccountError, NoKerberosTicketError

    assert issubclass(NoAwsAccountError, Exception)
    assert issubclass(NoKerberosTicketError, Exception)


def test_public_models() -> None:
    from rh_aws_saml_login import AwsCredentials

    assert is_dataclass(AwsCredentials)
