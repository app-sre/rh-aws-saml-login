import copy
import logging
import os
import subprocess

from rich import print
from rich.text import Text


def blend_text(
    message: str, color1: tuple[int, int, int], color2: tuple[int, int, int]
) -> Text:
    """Blend text from one color to another."""
    text = Text(message)
    r1, g1, b1 = color1
    r2, g2, b2 = color2
    dr = r2 - r1
    dg = g2 - g1
    db = b2 - b1
    size = len(text)
    for index in range(size):
        blend = index / size
        color = f"#{int(r1 + dr * blend):2X}{int(g1 + dg * blend):2X}{int(b1 + db * blend):2X}"
        text.stylize(color, index, index + 1)
    return text


def bye():
    print(
        "Thank you for using rh-aws-saml-login. :man_bowing: Have a great day ahead! :red_heart-emoji:"
    )


def enable_requests_logging():
    from http.client import HTTPConnection  # noqa: PLC0415

    HTTPConnection.debuglevel = 1
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True


def run(
    cmd: list[str] | str,
    shell: bool = False,
    check: bool = True,
    capture_output: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    shell_env = copy.deepcopy(os.environ)
    if env:
        shell_env.update(env)
    return subprocess.run(
        cmd, shell=shell, check=check, env=shell_env, capture_output=capture_output
    )
