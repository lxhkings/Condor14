# tests/test_trust_pages.py
from datetime import date
from pathlib import Path

from content_engine.json_ld import organization_schema


def test_organization_schema_shape():
    org = organization_schema(
        base_url="https://example.com", contact_email="contact@example.com"
    )
    assert org["@type"] == "Organization"
    assert org["name"] == "QuantOptions Data Lab"
    assert org["url"] == "https://example.com/"
    assert org["contactPoint"]["email"] == "contact@example.com"