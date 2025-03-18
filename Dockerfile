FROM registry.access.redhat.com/ubi9/python-311@sha256:ae3c5e4857482fed9a04a9373eb5e852e52db4d32851a69ef1fc3ad2d48b256a AS base
COPY --from=ghcr.io/astral-sh/uv:0.6.7@sha256:d25a9b42ecc3aac0d63782654dcb2ab4b304f86357794b05a5c39b17f4777339 /uv /bin/uv
COPY LICENSE /licenses/

ENV \
    # use venv from ubi image
    UV_PROJECT_ENVIRONMENT=$APP_ROOT \
    # disable uv cache. it doesn't make sense in a container
    UV_NO_CACHE=true

COPY pyproject.toml uv.lock README.md ./
# Test lock file is up to date
RUN uv lock --locked

COPY tests ./tests
COPY rh_aws_saml_login ./rh_aws_saml_login
RUN uv sync --frozen

COPY Makefile ./


#
# Test image
#
FROM base AS test
RUN make test


#
# PyPI publish image
#
FROM test AS pypi
# Secrets are owned by root and are not readable by others :(
USER root
RUN --mount=type=secret,id=app-sre-pypi-credentials/token make -s pypi
