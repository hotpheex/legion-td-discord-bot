.PHONY: test lint format install-lambda-deps install-dev-deps install-all-deps install-dispatcher-deps install-manage-deps

test:
	poetry run pytest

lint:
	poetry run black . --check
	poetry run isort . --check-only
	poetry run flake8 .

format:
	poetry run black .
	poetry run isort .

install-lambda-deps:
	poetry install --only lambda-shared

install-dev-deps:
	poetry install --only dev

install-all-deps:
	poetry install --with lambda-shared,dev

install-dispatcher-deps:
	poetry install --with lambda-shared,lambda-dispatcher

install-manage-deps:
	poetry install --with lambda-shared,lambda-manage
