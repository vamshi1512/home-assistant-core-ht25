"""Tests for the Quiet Mode integration."""

from unittest.mock import MagicMock

from homeassistant.components.media_player import (
    ATTR_MEDIA_VOLUME_LEVEL,
    DOMAIN as MEDIA_PLAYER_DOMAIN,
)
from homeassistant.components.quiet_mode.const import (
    DEFAULT_VOLUME,
    DOMAIN,
    HELPER_SELECT_LIVING_ROOM,
    HELPER_VOLUME,
)
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_VOLUME_SET
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.setup import async_setup_component


async def test_setup(hass: HomeAssistant) -> None:
    """Test the component setup."""
    assert await async_setup_component(hass, DOMAIN, {})
    assert DOMAIN in hass.data


async def test_enable_quiet_mode(hass: HomeAssistant) -> None:
    """Test enabling quiet mode."""
    await async_setup_component(hass, DOMAIN, {})

    # Setup the helpers
    target_entity = "media_player.living_room"
    hass.states.async_set(HELPER_SELECT_LIVING_ROOM, "on")
    hass.states.async_set(HELPER_VOLUME, "0.15")

    # Setup the media player
    hass.states.async_set(target_entity, "playing", {ATTR_MEDIA_VOLUME_LEVEL: 0.5})

    # Register a mock service for media_player.volume_set
    mock_volume_set = MagicMock()

    async def async_mock_volume_set(call: ServiceCall) -> None:
        mock_volume_set(call)

    hass.services.async_register(
        MEDIA_PLAYER_DOMAIN, SERVICE_VOLUME_SET, async_mock_volume_set
    )

    # Call enable service
    await hass.services.async_call(
        DOMAIN,
        "enable",
        {},
        blocking=True,
    )

    # Check if volume was stored
    assert hass.data[DOMAIN][target_entity] == 0.5

    # Check if set_volume_level was called with helper volume
    assert mock_volume_set.called
    call_args = mock_volume_set.call_args[0][0]
    assert call_args.data[ATTR_ENTITY_ID] == target_entity
    assert call_args.data[ATTR_MEDIA_VOLUME_LEVEL] == 0.15


async def test_enable_quiet_mode_default_volume(hass: HomeAssistant) -> None:
    """Test enabling quiet mode with default volume (helper missing/invalid)."""
    await async_setup_component(hass, DOMAIN, {})

    target_entity = "media_player.living_room"
    hass.states.async_set(HELPER_SELECT_LIVING_ROOM, "on")
    # No HELPER_VOLUME set, should default

    hass.states.async_set(target_entity, "playing", {ATTR_MEDIA_VOLUME_LEVEL: 0.8})

    mock_volume_set = MagicMock()

    async def async_mock_volume_set(call: ServiceCall) -> None:
        mock_volume_set(call)

    hass.services.async_register(
        MEDIA_PLAYER_DOMAIN, SERVICE_VOLUME_SET, async_mock_volume_set
    )

    await hass.services.async_call(
        DOMAIN,
        "enable",
        {},
        blocking=True,
    )

    assert hass.data[DOMAIN][target_entity] == 0.8

    assert mock_volume_set.called
    call_args = mock_volume_set.call_args[0][0]
    assert call_args.data[ATTR_ENTITY_ID] == target_entity
    assert call_args.data[ATTR_MEDIA_VOLUME_LEVEL] == DEFAULT_VOLUME


async def test_disable_quiet_mode(hass: HomeAssistant) -> None:
    """Test disabling quiet mode."""
    await async_setup_component(hass, DOMAIN, {})

    entity_id = "media_player.living_room"
    # Pre-populate stored volume
    hass.data[DOMAIN][entity_id] = 0.6

    # Register a mock service for media_player.volume_set
    mock_volume_set = MagicMock()

    async def async_mock_volume_set(call: ServiceCall) -> None:
        mock_volume_set(call)

    hass.services.async_register(
        MEDIA_PLAYER_DOMAIN, SERVICE_VOLUME_SET, async_mock_volume_set
    )

    await hass.services.async_call(
        DOMAIN,
        "disable",
        {},
        blocking=True,
    )

    # Check if volume was removed from storage
    assert entity_id not in hass.data[DOMAIN]

    assert mock_volume_set.called
    call_args = mock_volume_set.call_args[0][0]
    assert call_args.data[ATTR_ENTITY_ID] == entity_id
    assert call_args.data[ATTR_MEDIA_VOLUME_LEVEL] == 0.6


async def test_enable_quiet_mode_no_selection(hass: HomeAssistant) -> None:
    """Test enabling quiet mode with no entities selected."""
    await async_setup_component(hass, DOMAIN, {})

    # Ensure helper is off
    hass.states.async_set(HELPER_SELECT_LIVING_ROOM, "off")

    mock_volume_set = MagicMock()

    async def async_mock_volume_set(call: ServiceCall) -> None:
        mock_volume_set(call)

    hass.services.async_register(
        MEDIA_PLAYER_DOMAIN, SERVICE_VOLUME_SET, async_mock_volume_set
    )

    await hass.services.async_call(
        DOMAIN,
        "enable",
        {},
        blocking=True,
    )

    assert not mock_volume_set.called


async def test_disable_quiet_mode_not_enabled(hass: HomeAssistant) -> None:
    """Test disabling quiet mode when not enabled."""
    await async_setup_component(hass, DOMAIN, {})

    mock_volume_set = MagicMock()

    async def async_mock_volume_set(call: ServiceCall) -> None:
        mock_volume_set(call)

    hass.services.async_register(
        MEDIA_PLAYER_DOMAIN, SERVICE_VOLUME_SET, async_mock_volume_set
    )

    await hass.services.async_call(
        DOMAIN,
        "disable",
        {},
        blocking=True,
    )

    assert not mock_volume_set.called
