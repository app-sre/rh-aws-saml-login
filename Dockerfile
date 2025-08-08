FROM registry.access.redhat.com/ubi9/python-311@sha256:d89ff287e8248919657e8b6ca978f768054c48f087614bc765f51eafbe922fbc AS base
COPY --from=ghcr.io/astral-sh/uv:0.8.7@sha256:72c835cd4327377132b37c4c6944a3be209007e2e2314a031b220c4a5d09739e /uv /bin/uv
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
