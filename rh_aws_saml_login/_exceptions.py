class NoKerberosTicketError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("No valid kerberos ticket found.")


class NoAwsAccountError(RuntimeError):
    def __init__(self, account_name: str) -> None:
        super().__init__(f"Account not found: {account_name}")
