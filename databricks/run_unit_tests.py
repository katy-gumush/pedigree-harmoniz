# Databricks notebook source
# Run Python unit tests for pedigree_app (pytest), following:
# https://docs.databricks.com/aws/en/notebooks/testing
#
# Usage: open this file as a notebook in a Databricks Repo cloned from this
# repository, attach a cluster, run all cells.
# MAGIC %pip install pytest
# COMMAND ----------
import os
import sys
from pathlib import Path

import pytest


def _repo_root() -> Path:
    """Find repository root by searching for pyproject.toml.
    
    Works in both notebook and regular Python environments.
    Serverless-compatible: avoids Java/JVM APIs.
    """
    # Try environment variable first (if set by user)
    if "REPO_ROOT" in os.environ:
        return Path(os.environ["REPO_ROOT"])
    
    # Try from __file__ if available (regular Python execution)
    try:
        here = Path(__file__).resolve()
        for ancestor in [here.parent] + list(here.parents):
            if (ancestor / "pyproject.toml").exists():
                return ancestor
    except NameError:
        pass  # __file__ not defined in notebook context
    
    # Fallback: search upward from current working directory
    cwd = Path.cwd()
    for ancestor in [cwd] + list(cwd.parents):
        if (ancestor / "pyproject.toml").exists():
            return ancestor
    
    # Last resort: assume we're in a subdirectory of the repo
    # (e.g., /Workspace/Users/.../pedigree-harmoniz/databricks)
    return cwd.parent


root = _repo_root()
os.chdir(root)
src = str(root / "src")
if src not in sys.path:
    sys.path.insert(0, src)
sys.dont_write_bytecode = True
retcode = pytest.main([str(root / "tests"), "-v", "-p", "no:cacheprovider"])
assert retcode == 0, "The pytest invocation failed. See the log for details."
