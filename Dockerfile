FROM registry.access.redhat.com/ubi9/python-311@sha256:47107ded2aac95702535be963e2718e58d45bcecb3d4e582bd58bd35f6fc6bc3 AS base
COPY --from=ghcr.io/astral-sh/uv:0.5.26@sha256:a0c0e6aed043f5138957ea89744536eed81f1db633dc9bb3be2b882116060be2 /uv /bin/uv
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
