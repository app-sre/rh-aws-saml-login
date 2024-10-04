FROM registry.access.redhat.com/ubi9/python-311:1-77.1726664316
COPY --from=ghcr.io/astral-sh/uv:0.4.18 /uv /bin/uv

ARG TWINE_USERNAME
ARG TWINE_PASSWORD
ARG MAKE_TARGET

# Install dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# other project related files
COPY LICENSE README.md Makefile ./

# the source code
COPY rh_aws_saml_login ./rh_aws_saml_login
COPY tests ./tests

# Sync the project
RUN uv sync --frozen --no-editable

RUN make $MAKE_TARGET
