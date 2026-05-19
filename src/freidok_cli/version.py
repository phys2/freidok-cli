import importlib.metadata
import pathlib
import tomllib

# Retrieve package version either from pyproject.toml or from package metadata
try:
    project_root = pathlib.Path(__file__).parent.parent.parent
    if (project_root / "pyproject.toml").exists():
        with open(project_root / "pyproject.toml", "rb") as f:
            version = tomllib.load(f)['project']['version']
    else:
        version = importlib.metadata.version("package")
except Exception:  # noqa
    version = "<unknown>"

__version__ = version
