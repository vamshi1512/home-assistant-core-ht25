"""The Quiet Mode integration."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.components.media_player import (
    ATTR_MEDIA_VOLUME_LEVEL,
    DOMAIN as MEDIA_PLAYER_DOMAIN,
)
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_VOLUME_SET
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.typing import ConfigType

from .const import (
    DEFAULT_VOLUME,
    DOMAIN,
    ENTITY_SPOTIFY,
    HELPER_INCLUDE_SPOTIFY,
    HELPER_TARGET_SELECTOR,
    HELPER_VOLUME,
    OPTION_ALL,
    ROOM_ENTITY_MAPPING,
)

_LOGGER = logging.getLogger(__name__)

SERVICE_ENABLE = "enable"
SERVICE_DISABLE = "disable"

ATTR_VOLUME_LEVEL = "volume_level"

# Schema is now empty as we read from helpers
ENABLE_SCHEMA = vol.Schema({})
DISABLE_SCHEMA = vol.Schema({})

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Quiet Mode integration."""
    hass.data.setdefault(DOMAIN, {})

    def get_target_entities(hass: HomeAssistant) -> list[str]:
        """Get list of entities selected via input_select and input_boolean."""
        entities: list[str] = []

        # Check Room Selection (Dropdown)
        target_selection = hass.states.get(HELPER_TARGET_SELECTOR)
        selection = target_selection.state if target_selection else None

        if selection == OPTION_ALL:
            entities.extend(ROOM_ENTITY_MAPPING.values())
        elif selection in ROOM_ENTITY_MAPPING:
            entities.append(ROOM_ENTITY_MAPPING[selection])

        # Check Spotify Selection (Toggle)
        spotify_state = hass.states.get(HELPER_INCLUDE_SPOTIFY)
        if spotify_state and spotify_state.state == "on":
            entities.append(ENTITY_SPOTIFY)

        return list(set(entities))  # Deduplicate just in case

    def get_target_volume(hass: HomeAssistant) -> float:
        """Get target volume from input_number helper."""
        state = hass.states.get(HELPER_VOLUME)
        if state:
            try:
                # input_number state is string, cast to float
                return float(state.state)
            except ValueError:
                _LOGGER.warning("Invalid value for %s: %s", HELPER_VOLUME, state.state)
        return DEFAULT_VOLUME

    async def async_enable_quiet_mode(call: ServiceCall) -> None:
        """Enable quiet mode for selected media players."""
        # ignore passed entity_ids, read from helpers
        entity_ids = get_target_entities(hass)
        target_volume = get_target_volume(hass)

        if not entity_ids:
            _LOGGER.warning("No media players selected for Quiet Mode")
            return

        _LOGGER.debug(
            "Enabling Quiet Mode. Target: %s. Entities: %s", target_volume, entity_ids
        )

        for entity_id in entity_ids:
            state = hass.states.get(entity_id)
            if state is None:
                _LOGGER.debug("Entity %s not found", entity_id)
                continue

            current_volume = state.attributes.get(ATTR_MEDIA_VOLUME_LEVEL)

            if current_volume is None:
                _LOGGER.debug(
                    "Entity %s does not support volume level or is off/idle", entity_id
                )
                continue

            # Store the current volume if not already stored
            if entity_id not in hass.data[DOMAIN]:
                hass.data[DOMAIN][entity_id] = current_volume
                _LOGGER.debug("Stored volume %s for %s", current_volume, entity_id)

            # Set the new volume
            try:
                await hass.services.async_call(
                    MEDIA_PLAYER_DOMAIN,
                    SERVICE_VOLUME_SET,
                    {ATTR_ENTITY_ID: entity_id, ATTR_MEDIA_VOLUME_LEVEL: target_volume},
                    blocking=True,
                )
            except HomeAssistantError as e:
                _LOGGER.error("Failed to set volume for %s: %s", entity_id, e)

    async def async_disable_quiet_mode(call: ServiceCall) -> None:
        """Disable quiet mode and restore volume."""
        stored_entities = list(hass.data[DOMAIN].keys())

        if not stored_entities:
            _LOGGER.debug("No active Quiet Mode sessions to restore")
            return

        for entity_id in stored_entities:
            original_volume = hass.data[DOMAIN].pop(entity_id)
            _LOGGER.debug("Restoring volume %s for %s", original_volume, entity_id)

            try:
                await hass.services.async_call(
                    MEDIA_PLAYER_DOMAIN,
                    SERVICE_VOLUME_SET,
                    {
                        ATTR_ENTITY_ID: entity_id,
                        ATTR_MEDIA_VOLUME_LEVEL: original_volume,
                    },
                    blocking=True,
                )
            except HomeAssistantError as e:
                _LOGGER.error("Failed to restore volume for %s: %s", entity_id, e)

    hass.services.async_register(
        DOMAIN, SERVICE_ENABLE, async_enable_quiet_mode, schema=ENABLE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_DISABLE, async_disable_quiet_mode, schema=DISABLE_SCHEMA
    )

    return True
