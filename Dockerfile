FROM registry.access.redhat.com/ubi9/python-311@sha256:c0be006b436abb581e76cd1953f452875d1464f7a5b1daed9dac94036f3b681f AS base
COPY --from=ghcr.io/astral-sh/uv:0.11.12@sha256:3a59a3cdd5f7c217faa36e32dbc7fddbb0412889c2a0a5229f6d790e5a019dd7 /uv /bin/uv
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
