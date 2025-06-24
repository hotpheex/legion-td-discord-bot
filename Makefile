.PHONY: test lint build-lambda synth

setup:
	poetry install
	poetry self add poetry-plugin-export

test:
	poetry run pytest --ignore=cdk.out --ignore=cdk.build

format:
	poetry run isort . --skip-glob "cdk.out/*" --skip-glob "cdk.build/*" --skip-glob ".venv/*"
	poetry run black . --extend-exclude "cdk.out/,cdk.build/,.venv/"

build-lambda:
	poetry run python infra/libs/build_lambda.py

synth: build-lambda
	poetry run cdk synth

deploy: build-lambda
	poetry run cdk deploy --require-approval never

%:
	@:
