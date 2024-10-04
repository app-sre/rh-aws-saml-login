FROM registry.access.redhat.com/ubi9/python-311:1-77.1726664316
COPY --from=ghcr.io/astral-sh/uv:0.4.18 /uv /bin/uv

ARG TWINE_USERNAME
ARG TWINE_PASSWORD
ARG MAKE_TARGET

ENV UV_CACHE_DIR=/tmp/uv_cache

USER 1001

# Install dependencies
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/tmp/uv_cache,uid=1001 \
    mkdir -p ${UV_CACHE_DIR} && uv sync --frozen --no-install-project --link-mode=copy

# other project related files
COPY LICENSE README.md Makefile ./

# the source code
COPY rh_aws_saml_login ./rh_aws_saml_login
COPY tests ./tests

# Sync the project
RUN --mount=type=cache,target=/tmp/uv_cache,uid=1001 \
    uv sync --frozen --no-editable --link-mode=copy

RUN make $MAKE_TARGET
