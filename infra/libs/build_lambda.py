#!/usr/bin/env python3
import os
import shutil
import subprocess
from pathlib import Path


def build_lambda_function(function_name: str):
    # Get the project root directory (two levels up from this file)
    project_root = Path(__file__).parent.parent.parent
    function_dir = project_root / "functions" / function_name
    
    # Create a deployment directory
    deployment_dir = project_root / "cdk.build" / function_name
    if deployment_dir.exists():
        shutil.rmtree(deployment_dir)
    deployment_dir.mkdir(parents=True)
    
    # Copy the function code directly into the deployment directory
    for item in function_dir.iterdir():
        if item.is_file():
            shutil.copy2(item, deployment_dir)
        elif item.is_dir() and item.name != "__pycache__":
            shutil.copytree(item, deployment_dir / item.name)
    
    # Copy pyproject.toml and poetry.lock from parent project
    shutil.copy2(project_root / "pyproject.toml", deployment_dir)
    shutil.copy2(project_root / "poetry.lock", deployment_dir)
    
    # Install dependencies directly into the deployment directory
    os.chdir(deployment_dir)
    
    # Export dependencies to requirements.txt
    subprocess.run([
        "poetry",
        "export",
        "--only",
        f"lambda-shared,lambda-{function_name}",
        "--format",
        "requirements.txt",
        "--output",
        "requirements.txt",
        "--without-hashes"
    ], check=True)
    
    # Install dependencies using pip with platform specification for Lambda
    subprocess.run([
        "pip",
        "install",
        "--platform",
        "manylinux2014_x86_64",
        "--implementation",
        "cp",
        "--only-binary=:all:",
        "--upgrade",
        "-r",
        "requirements.txt",
        "--target",
        "."
    ], check=True)
    
    # Clean up temporary files
    os.remove("requirements.txt")
    os.remove("pyproject.toml")
    os.remove("poetry.lock")
    
    print(f"Built Lambda function {function_name} in {deployment_dir}")

if __name__ == "__main__":
    # Build all functions
    build_lambda_function("dispatcher")
    build_lambda_function("manage") 