"""Fixture-first, loopback-only FastAPI transport for Research Console vNext."""

from .app import create_app

__all__ = ["create_app"]
