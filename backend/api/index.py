"""Vercel serverless entrypoint.

Vercel's Python runtime serves the ASGI `app` exposed here. The parent directory
is added to sys.path so the sibling backend modules (server, engine, briefing,
brief_validation, model_budget, evaluation) import cleanly at runtime.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import app  # noqa: E402,F401
