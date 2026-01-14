"""Fixtures for Quiet Mode tests."""

import pytest

from homeassistant.core import HomeAssistant


@pytest.fixture
def hass(hass: HomeAssistant) -> HomeAssistant:
    """Return a Home Assistant instance for testing."""
    return hass
