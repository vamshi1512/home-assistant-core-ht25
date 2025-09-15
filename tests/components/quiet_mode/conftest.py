"""Fixtures for Quiet Mode integration tests."""

import pytest

from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry


@pytest.fixture
def mock_config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Return the default mocked config entry."""
    entry = MockConfigEntry(domain="quiet_mode", data={})
    entry.add_to_hass(hass)
    return entry
