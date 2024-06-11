DIRS := rh_aws_saml_login
BUILD_ARGS := POETRY_VERSION=1.8.3 TWINE_USERNAME TWINE_PASSWORD
# TWINE_USERNAME & TWINE_PASSWORD are available in jenkins job
POETRY_HTTP_BASIC_PYPI_USERNAME := $(TWINE_USERNAME)
POETRY_HTTP_BASIC_PYPI_PASSWORD := $(TWINE_PASSWORD)
export POETRY_HTTP_BASIC_PYPI_USERNAME
export POETRY_HTTP_BASIC_PYPI_PASSWORD

tapes = $(wildcard demo/*.tape)
gifs = $(tapes:%.tape=%.gif)

all:
	@echo $(tapes)
	@echo $(tape_files)
	@echo $(patsubst %.tape,%.c,$(tape_files))

format:
	poetry run ruff check
	poetry run ruff format
.PHONY: format

pr-check:
	docker build -t rh-aws-saml-login-test --build-arg MAKE_TARGET=test $(foreach arg,$(BUILD_ARGS),--build-arg $(arg)) .
.PHONY: pr-check

test:
	poetry run ruff check --no-fix
	poetry run ruff format --check
	poetry run mypy $(DIRS)
	poetry run pytest -vv
.PHONY: test

build-deploy:
	docker build -t rh-aws-saml-login-test --build-arg MAKE_TARGET=pypi $(foreach arg,$(BUILD_ARGS),--build-arg $(arg)) .
.PHONY: build-deploy

pypi:
	poetry publish --build --skip-existing
.PHONY: pypi


update-demos: $(gifs)

$(gifs): %.gif: %.tape
	ifeq (, $(shell which vhs2))
	$(error "No vhs command not found in $$PATH. Please install https://github.com/charmbracelet/vhs")
	endif
	cd demo && vhs < $(notdir $?)
