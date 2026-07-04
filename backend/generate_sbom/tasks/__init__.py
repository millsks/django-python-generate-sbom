"""Celery task modules (pipeline + analysis queues, AD-4)."""

from .sbom_pipeline import run_sbom_pipeline

__all__ = ["run_sbom_pipeline"]
