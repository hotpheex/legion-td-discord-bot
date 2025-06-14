from pathlib import Path
from aws_cdk.aws_lambda import Runtime

# Lambda runtime version
LAMBDA_RUNTIME = Runtime.PYTHON_3_13

# Build output directory
BUILD_DIR = Path(__file__).parent.parent.parent / "cdk.build"
