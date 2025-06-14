.PHONY: test lint build-lambda synth

test:
	poetry run pytest

lint:
	poetry run ruff check .
	poetry run ruff format --check .

build-lambda:
	poetry run python infra/libs/build_lambda.py

synth: build-lambda
	poetry run cdk synth

%:
	@:
