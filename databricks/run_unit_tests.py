# Databricks notebook source
# Run Python unit tests for pedigree_app (pytest), following:
# https://docs.databricks.com/aws/en/notebooks/testing
#
# Usage: open this file as a notebook in a Databricks Repo cloned from this
# repository, attach a cluster, run all cells.
#
# CSV path: pytest sets PEDIGREE_CSV_PATH from PEDIGREE_TEST_CSV or --pedigree-csv,
# default fixtures/csv/clean.csv. Example red demo before pytest:
#   os.environ["PEDIGREE_TEST_CSV"] = str(root / "fixtures/csv/corrupt_immediate_loop.csv")
# MAGIC %pip install pytest httpx
# MAGIC %pip install fastapi
# MAGIC %pip install --upgrade typing_extensions
# MAGIC %pip uninstall -y fastapi pydantic pydantic-core typing_extensions
# MAGIC %pip install fastapi uvicorn jinja2 httpx pytest
# MAGIC %pip install jinja2
# MAGIC %pip install "typing_extensions==4.10.0" "pydantic==1.10.15" "fastapi==0.95.2" "starlette==0.27.0" "httpx==0.24.1"
# MAGIC dbutils.library.restartPython()

# COMMAND ----------
import os
import sys
from pathlib import Path
import pytest

def _repo_root() -> Path:
    if "REPO_ROOT" in os.environ:
        return Path(os.environ["REPO_ROOT"])
    cwd = Path.cwd()
    for ancestor in [cwd] + list(cwd.parents):
        if (ancestor / "pyproject.toml").exists():
            return ancestor
    return cwd.parent

root = _repo_root()
os.chdir(root)

for p in [root, root / "src", root / "tests"]:
    p_str = str(p)
    if p_str not in sys.path:
        sys.path.insert(0, p_str)

(root / "tests" / "__init__.py").touch()

sys.dont_write_bytecode = True

try:
    import fastapi
except ImportError:
    raise ImportError("FastAPI is not installed. Please install it using %pip install fastapi.")

# Run pytest only on existing tests
retcode = pytest.main([
    str(root / "tests"),
    "-v",
    "-p", "no:cacheprovider",
    "--ignore", str(root / "tests" / "test_intentional_failure.py")
])

print("Pytest return code:", retcode)
assert retcode == 0, "The pytest invocation failed. See the log for details."