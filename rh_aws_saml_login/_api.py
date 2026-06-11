import logging

from ._consts import RH_SAML_URL, AwsRegion
from ._core import (
    assume_role_with_saml,
    get_aws_accounts,
    get_saml_auth,
    is_kerberos_ticket_valid,
    select_aws_account,
)
from ._exceptions import NoAwsAccountError, NoKerberosTicketError
from ._models import AwsCredentials

logger = logging.getLogger(__name__)


def get_aws_credentials(
    account_name: str,
    saml_url: str = RH_SAML_URL,
    session_timeout_seconds: int = 900,
    region: str = AwsRegion.US_EAST_1,
) -> AwsCredentials:
    """Get AWS credentials for the given account name non-interactively."""
    if not is_kerberos_ticket_valid():
        raise NoKerberosTicketError
    aws_url, saml_token = get_saml_auth(saml_url)
    aws_accounts = get_aws_accounts(
        aws_url, saml_token, session_timeout_seconds, region
    )
    if not (account := select_aws_account(aws_accounts, account_name)):
        raise NoAwsAccountError(account_name)
    return assume_role_with_saml(account, saml_token)
