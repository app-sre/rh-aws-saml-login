FROM registry.access.redhat.com/ubi9/python-311
ARG POETRY_VERSION
ARG TWINE_USERNAME
ARG TWINE_PASSWORD
ARG MAKE_TARGET

RUN pip install --upgrade pip && \
    pip install poetry==$POETRY_VERSION

# venv configuration
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root

# other project related files
COPY README.md Makefile ./

# the source code
COPY rh_aws_saml_login ./rh_aws_saml_login
COPY tests ./tests
RUN poetry install --only-root

RUN make $MAKE_TARGET
