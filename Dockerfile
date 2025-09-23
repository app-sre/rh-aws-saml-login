FROM registry.access.redhat.com/ubi9/python-311@sha256:47e23afaf5daf6a98e76a3b5a924b85bbcb19c72b5c6ac474a418aea54cd8aae AS base
COPY --from=ghcr.io/astral-sh/uv:0.8.21@sha256:ca74b4b463d7dfc1176cbe82a02b6e143fd03a144dcb1a87c3c3e81ac16c6f6d /uv /bin/uv
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
