FROM registry.access.redhat.com/ubi9/python-311@sha256:3145a0bb4fd5c841bfc21a77d099f0b24550e78a7eb871528b6c0ab811b43ac8 AS base
COPY --from=ghcr.io/astral-sh/uv:0.5.13@sha256:926f32f1722d6a9187f5a48fe0da68c34cab9512885e1857219a3fe0a546ab0d /uv /bin/uv
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
