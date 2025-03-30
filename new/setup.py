from setuptools import setup, find_packages
from pathlib import Path

def create_directories():
    """Create required directories for the project"""
    directories = [
        "logs",
        "models",
        "data",
        "tests",
        "api",
        "core/behavioral_analysis",
        "security",
        "data_processing",
        "enterprise",
        "performance",
        "logging",
        "ml",
        "utils",
        "examples",
        "config"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        # Create __init__.py in each Python package directory
        if directory not in ["logs", "models", "data", "tests"]:
            init_file = Path(directory) / "__init__.py"
            init_file.touch(exist_ok=True)

if __name__ == "__main__":
    create_directories()
    setup(
        name="behavioral-biometrics",
        version="1.0.0",
        packages=find_packages(),
        install_requires=[
            "fastapi>=0.104.1",
            "uvicorn>=0.24.0",
            "websockets>=12.0",
            "aiohttp>=3.9.1",
            "numpy>=1.26.2",
            "pandas>=2.1.3",
            "scikit-learn>=1.3.2",
            "torch>=2.1.1",
            "python-jose>=3.3.0",
            "pydantic>=2.5.2",
            "python-multipart>=0.0.6",
            "python-dotenv>=1.0.0",
            "joblib>=1.3.2",
            "requests>=2.31.0",
            "python-ldap>=3.4.3"
        ],
        python_requires=">=3.8",
    ) 