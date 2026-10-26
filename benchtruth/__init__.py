"""benchtruth -- a verified hardware-build generator.

The LLM proposes; the solver disposes. See SPEC.md.
"""
from .db import load_db, Db
from .solver import Solver, Plan, solve_spec

__all__ = ["load_db", "Db", "Solver", "Plan", "solve_spec"]
