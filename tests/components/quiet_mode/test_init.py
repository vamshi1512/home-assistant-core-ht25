"""Tests for the Quiet Mode integration."""

import pytest

from homeassistant.components.media_player import (
    ATTR_MEDIA_VOLUME_LEVEL,
    DOMAIN as MEDIA_PLAYER_DOMAIN,
)
from homeassistant.components.quiet_mode.const import (
    ATTR_QUIET_VOLUME,
    DEFAULT_QUIET_VOLUME,
    DOMAIN,
    SERVICE_DISABLE,
    SERVICE_ENABLE,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component


@pytest.fixture
async def setup_quiet_mode(hass: HomeAssistant):
    """Set up the Quiet Mode integration."""
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()


async def test_setup(hass: HomeAssistant, setup_quiet_mode) -> None:
    """Test that the integration sets up correctly."""
    assert DOMAIN in hass.data
    assert hass.services.has_service(DOMAIN, SERVICE_ENABLE)
    assert hass.services.has_service(DOMAIN, SERVICE_DISABLE)


async def test_enable_quiet_mode(hass: HomeAssistant, setup_quiet_mode) -> None:
    """Test enabling quiet mode."""
    entity_id = "media_player.test_player"
    current_volume = 0.5
    quiet_volume = 0.12

    # Set up a mock media player state
    hass.states.async_set(
        entity_id,
        "playing",
        {ATTR_MEDIA_VOLUME_LEVEL: current_volume},
    )

    # Mock the media_player.volume_set service
    calls = []

    async def mock_volume_set(call):
        calls.append(call)

    hass.services.async_register(
        MEDIA_PLAYER_DOMAIN,
        "volume_set",
        mock_volume_set,
    )

    # Call enable service
    await hass.services.async_call(
        DOMAIN,
        SERVICE_ENABLE,
        {
            ATTR_ENTITY_ID: [entity_id],
            ATTR_QUIET_VOLUME: quiet_volume,
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    # Verify that volume_set was called
    assert len(calls) == 1
    assert calls[0].data[ATTR_ENTITY_ID] == entity_id
    assert calls[0].data[ATTR_MEDIA_VOLUME_LEVEL] == quiet_volume

    # Verify volume was stored
    assert entity_id in hass.data[DOMAIN]["previous_volumes"]
    assert hass.data[DOMAIN]["previous_volumes"][entity_id] == current_volume


async def test_enable_with_default_volume(
    hass: HomeAssistant, setup_quiet_mode
) -> None:
    """Test enabling quiet mode with default volume."""
    entity_id = "media_player.test_player"
    current_volume = 0.8

    hass.states.async_set(
        entity_id,
        "playing",
        {ATTR_MEDIA_VOLUME_LEVEL: current_volume},
    )

    # Mock the media_player.volume_set service
    calls = []

    async def mock_volume_set(call):
        calls.append(call)

    hass.services.async_register(
        MEDIA_PLAYER_DOMAIN,
        "volume_set",
        mock_volume_set,
    )

    # Call enable without specifying quiet_volume
    await hass.services.async_call(
        DOMAIN,
        SERVICE_ENABLE,
        {ATTR_ENTITY_ID: [entity_id]},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Verify default volume was used
    assert len(calls) == 1
    assert calls[0].data[ATTR_MEDIA_VOLUME_LEVEL] == DEFAULT_QUIET_VOLUME


async def test_disable_quiet_mode(hass: HomeAssistant, setup_quiet_mode) -> None:
    """Test disabling quiet mode."""
    entity_id = "media_player.test_player"
    previous_volume = 0.7

    # Store a previous volume
    hass.data[DOMAIN]["previous_volumes"][entity_id] = previous_volume

    # Set current state to quiet volume
    hass.states.async_set(
        entity_id,
        "playing",
        {ATTR_MEDIA_VOLUME_LEVEL: 0.12},
    )

    # Mock the media_player.volume_set service
    calls = []

    async def mock_volume_set(call):
        calls.append(call)

    hass.services.async_register(
        MEDIA_PLAYER_DOMAIN,
        "volume_set",
        mock_volume_set,
    )

    # Call disable service
    await hass.services.async_call(
        DOMAIN,
        SERVICE_DISABLE,
        {ATTR_ENTITY_ID: [entity_id]},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Verify that volume_set was called with previous volume
    assert len(calls) == 1
    assert calls[0].data[ATTR_ENTITY_ID] == entity_id
    assert calls[0].data[ATTR_MEDIA_VOLUME_LEVEL] == previous_volume

    # Verify stored volume was cleaned up
    assert entity_id not in hass.data[DOMAIN]["previous_volumes"]


async def test_enable_multiple_entities(hass: HomeAssistant, setup_quiet_mode) -> None:
    """Test enabling quiet mode for multiple media players."""
    entity_ids = [
        "media_player.living_room",
        "media_player.bedroom",
    ]
    volumes = [0.6, 0.8]

    # Set up mock states
    for entity_id, volume in zip(entity_ids, volumes, strict=False):
        hass.states.async_set(
            entity_id,
            "playing",
            {ATTR_MEDIA_VOLUME_LEVEL: volume},
        )

    # Mock the media_player.volume_set service
    calls = []

    async def mock_volume_set(call):
        calls.append(call)

    hass.services.async_register(
        MEDIA_PLAYER_DOMAIN,
        "volume_set",
        mock_volume_set,
    )

    await hass.services.async_call(
        DOMAIN,
        SERVICE_ENABLE,
        {
            ATTR_ENTITY_ID: entity_ids,
            ATTR_QUIET_VOLUME: 0.12,
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    # Verify both entities had volume_set called
    assert len(calls) == 2

    # Verify both volumes were stored
    for entity_id, volume in zip(entity_ids, volumes, strict=False):
        assert hass.data[DOMAIN]["previous_volumes"][entity_id] == volume


async def test_enable_entity_not_found(hass: HomeAssistant, setup_quiet_mode) -> None:
    """Test enabling quiet mode for non-existent entity."""
    entity_id = "media_player.nonexistent"

    # Mock the media_player.volume_set service
    calls = []

    async def mock_volume_set(call):
        calls.append(call)

    hass.services.async_register(
        MEDIA_PLAYER_DOMAIN,
        "volume_set",
        mock_volume_set,
    )

    await hass.services.async_call(
        DOMAIN,
        SERVICE_ENABLE,
        {ATTR_ENTITY_ID: [entity_id]},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Verify volume_set was not called
    assert len(calls) == 0

    # Verify nothing was stored
    assert entity_id not in hass.data[DOMAIN]["previous_volumes"]


async def test_enable_entity_without_volume(
    hass: HomeAssistant, setup_quiet_mode
) -> None:
    """Test enabling quiet mode for entity without volume_level."""
    entity_id = "media_player.no_volume"

    # Set up entity without volume_level attribute
    hass.states.async_set(entity_id, "playing", {})

    # Mock the media_player.volume_set service
    calls = []

    async def mock_volume_set(call):
        calls.append(call)

    hass.services.async_register(
        MEDIA_PLAYER_DOMAIN,
        "volume_set",
        mock_volume_set,
    )

    await hass.services.async_call(
        DOMAIN,
        SERVICE_ENABLE,
        {ATTR_ENTITY_ID: [entity_id]},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Verify volume_set was not called
    assert len(calls) == 0


async def test_disable_without_stored_volume(
    hass: HomeAssistant, setup_quiet_mode
) -> None:
    """Test disabling quiet mode when no volume was stored."""
    entity_id = "media_player.test_player"

    # Mock the media_player.volume_set service
    calls = []

    async def mock_volume_set(call):
        calls.append(call)

    hass.services.async_register(
        MEDIA_PLAYER_DOMAIN,
        "volume_set",
        mock_volume_set,
    )

    await hass.services.async_call(
        DOMAIN,
        SERVICE_DISABLE,
        {ATTR_ENTITY_ID: [entity_id]},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Verify volume_set was not called
    assert len(calls) == 0
