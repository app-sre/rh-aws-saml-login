DIRS := rh_aws_saml_login
BUILD_ARGS := TWINE_USERNAME TWINE_PASSWORD
# TWINE_USERNAME & TWINE_PASSWORD are available in jenkins job
UV_PUBLISH_USERNAME := $(TWINE_USERNAME)
UV_PUBLISH_PASSWORD := $(TWINE_PASSWORD)
export UV_PUBLISH_USERNAME
export UV_PUBLISH_PASSWORD

tapes = $(wildcard demo/*.tape)
gifs = $(tapes:%.tape=%.gif)

all:
	@echo $(tapes)
	@echo $(tape_files)
	@echo $(patsubst %.tape,%.c,$(tape_files))

format:
	uv run ruff check
	uv run ruff format
.PHONY: format

pr-check:
	docker build -t rh-aws-saml-login-test --build-arg MAKE_TARGET=test $(foreach arg,$(BUILD_ARGS),--build-arg $(arg)) .
.PHONY: pr-check

test:
	uv run ruff check --no-fix
	uv run ruff format --check
	uv run mypy $(DIRS)
	uv run pytest -vv
.PHONY: test

build-deploy:
	docker build -t rh-aws-saml-login-test --build-arg MAKE_TARGET=pypi $(foreach arg,$(BUILD_ARGS),--build-arg $(arg)) .
.PHONY: build-deploy

pypi:
	uv build
	uv publish
.PHONY: pypi


update-demos: $(gifs)

$(gifs): %.gif: %.tape
	ifeq (, $(shell which vhs2))
	$(error "No vhs command not found in $$PATH. Please install https://github.com/charmbracelet/vhs")
	endif
	cd demo && vhs < $(notdir $?)
