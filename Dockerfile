FROM registry.access.redhat.com/ubi9/python-311@sha256:745690e5b7480f512c8dda81b14c1677a6df0a442ee49d15fab190f261ddd01d AS base
COPY --from=ghcr.io/astral-sh/uv:0.5.10@sha256:e4c08963c249b0e07d88e9313374d00491e69eed0c99ca5ee443e5c234a16a38 /uv /bin/uv
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
