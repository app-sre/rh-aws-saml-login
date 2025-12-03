FROM registry.access.redhat.com/ubi9/python-311@sha256:e80bccbb5033c7026912300d97ee967e240e31f01625511c345fb2fa8cd2f971 AS base
COPY --from=ghcr.io/astral-sh/uv:0.9.15@sha256:f739908ce28d7303646e25e4613906d23c08a69397f4a52b989aac23148ee971 /uv /bin/uv
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
