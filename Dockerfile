FROM registry.access.redhat.com/ubi9/python-311@sha256:23c0de6631bdc9befb2d1155988d7929fbfe24eec8ba82c5c04aaee656bb2b89 AS base
COPY --from=ghcr.io/astral-sh/uv:0.5.16@sha256:feebeb26b63566bb53d53031dee5497e49a0aa66feffd33aabe2e98307c72f6d /uv /bin/uv
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
