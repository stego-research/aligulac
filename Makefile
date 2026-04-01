# Makefile for Aligulac

IMAGE_NAME = aligulac-app
TAG = latest

# Detect container tool (docker or podman)
CONTAINER_TOOL := $(shell command -v docker 2> /dev/null || command -v podman 2> /dev/null)

.PHONY: build-image setup-dev run-dev clean help

help:
	@echo "Aligulac Makefile"
	@echo "-----------------"
	@echo "build-image : Build the production image using $(notdir $(CONTAINER_TOOL))"
	@echo "setup-dev   : Install development dependencies (pipenv)"
	@echo "run-dev     : Run the development server locally (pipenv)"
	@echo "clean       : Remove temporary files and virtualenv"

build-image:
	@if [ -z "$(CONTAINER_TOOL)" ]; then \
		echo "Error: Neither docker nor podman found in PATH"; \
		exit 1; \
	fi
	$(CONTAINER_TOOL) build -t $(IMAGE_NAME):$(TAG) .

setup-dev:
	pipenv install

run-dev: setup-dev
	pipenv run python aligulac/manage.py runserver

clean:
	rm -rf .venv
	rm -rf untracked/*
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
