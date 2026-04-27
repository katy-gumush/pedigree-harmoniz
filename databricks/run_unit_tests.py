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
    dbg = globals().get("dbutils")
    if dbg is not None:
        raw = dbg.notebook.entry_point.getDbutils().notebook.getContext().notebookPath().get()
        start = Path(raw).parent
        for ancestor in [start] + list(start.parents):
            if (ancestor / "pyproject.toml").exists():
                return ancestor
        return start.parent
    here = Path(__file__).resolve()
    for ancestor in [here.parent] + list(here.parents):
        if (ancestor / "pyproject.toml").exists():
            return ancestor
    return here.parent.parent


root = _repo_root()
os.chdir(root)
src = str(root / "src")
if src not in sys.path:
    sys.path.insert(0, src)
sys.dont_write_bytecode = True
retcode = pytest.main([str(root / "tests"), "-v", "-p", "no:cacheprovider"])
assert retcode == 0, "The pytest invocation failed. See the log for details."
