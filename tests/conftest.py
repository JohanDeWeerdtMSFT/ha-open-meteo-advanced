"""Fixtures for public Home Assistant integration boundaries."""

import pytest


@pytest.fixture(autouse=True)
def custom_integrations(enable_custom_integrations):
    """Allow Home Assistant to discover the custom integration."""
