FROM registry.access.redhat.com/ubi9/python-311@sha256:ed423c14020369e28f1a9ecb6ea74eb1e23b521c9fd82e3690bb53300086c571 AS base
COPY --from=ghcr.io/astral-sh/uv:0.8.18@sha256:62022a082ce1358336b920e9b7746ac7c95b1b11473aa93ab5e4f01232d6712d /uv /bin/uv
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
