"""Regression: the production storage backends must resolve to importable classes.

A wrong backend dotted-path (e.g. a class that moved between django-storages
versions) fails only at runtime with InvalidStorageError — surfacing as an opaque
500 on the first artifact write. Importing the paths here catches it at test time.
"""

from django.utils.module_loading import import_string

from config.settings import production


def test_production_storage_backends_are_importable() -> None:
    for alias in ("default", "staticfiles"):
        import_string(production.STORAGES[alias]["BACKEND"])  # raises if the path is wrong


def test_production_default_storage_is_s3() -> None:
    assert production.STORAGES["default"]["BACKEND"] == "storages.backends.s3.S3Storage"
