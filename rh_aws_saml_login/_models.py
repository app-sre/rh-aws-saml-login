from dataclasses import dataclass
from datetime import datetime as dt


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
