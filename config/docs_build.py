"""Generates every committed API-doc artefact under docs/api/."""

from pathlib import Path

from drf_spectacular.generators import SchemaGenerator
from drf_spectacular.renderers import OpenApiYamlRenderer

from . import postman

DOCS_DIR = Path(__file__).resolve().parent.parent / "docs" / "api"


def generate_schema():
    """The live OpenAPI schema as a dict (hooks applied)."""
    return SchemaGenerator().get_schema(request=None, public=True)


def build_all(schema=None):
    """relative path (under docs/api) -> file text."""
    schema = schema or generate_schema()
    files = {
        "openapi.yaml": OpenApiYamlRenderer()
        .render(schema, renderer_context={})
        .decode(),
    }
    for name, text in postman.build_postman_files(schema).items():
        files[f"postman/{name}"] = text
    return files
