"""The Quiet Mode integration."""

import logging
from typing import Final

import voluptuous as vol

from homeassistant.components.media_player import (
    ATTR_MEDIA_VOLUME_LEVEL,
    DOMAIN as MEDIA_PLAYER_DOMAIN,
    SERVICE_VOLUME_SET,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_QUIET_VOLUME,
    DATA_PREVIOUS_VOLUMES,
    DEFAULT_QUIET_VOLUME,
    DOMAIN,
    SERVICE_DISABLE,
    SERVICE_ENABLE,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)

SERVICE_ENABLE_SCHEMA: Final = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Optional(ATTR_QUIET_VOLUME, default=DEFAULT_QUIET_VOLUME): vol.All(
            vol.Coerce(float), vol.Range(min=0.0, max=1.0)
        ),
    }
)

SERVICE_DISABLE_SCHEMA: Final = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
    }
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Quiet Mode integration."""
    # Initialize storage for previous volumes
    hass.data[DOMAIN] = {DATA_PREVIOUS_VOLUMES: {}}

    async def async_handle_enable(call: ServiceCall) -> None:
        """Handle the enable service call."""
        entity_ids = call.data[ATTR_ENTITY_ID]
        quiet_volume = call.data[ATTR_QUIET_VOLUME]

        _LOGGER.debug(
            "Enabling quiet mode for %s with volume %s", entity_ids, quiet_volume
        )

        for entity_id in entity_ids:
            # Get current state of the media player
            state = hass.states.get(entity_id)

            if state is None:
                _LOGGER.warning("Entity %s not found", entity_id)
                continue

            # Check if entity supports volume_level
            current_volume = state.attributes.get(ATTR_MEDIA_VOLUME_LEVEL)

            if current_volume is None:
                _LOGGER.warning(
                    "Entity %s does not have volume_level attribute", entity_id
                )
                continue

            # Store the current volume
            hass.data[DOMAIN][DATA_PREVIOUS_VOLUMES][entity_id] = current_volume
            _LOGGER.debug("Stored volume %s for %s", current_volume, entity_id)

            # Set the quiet volume
            await hass.services.async_call(
                MEDIA_PLAYER_DOMAIN,
                SERVICE_VOLUME_SET,
                {
                    ATTR_ENTITY_ID: entity_id,
                    ATTR_MEDIA_VOLUME_LEVEL: quiet_volume,
                },
                blocking=True,
            )
            _LOGGER.info("Set quiet volume %s for %s", quiet_volume, entity_id)

    async def async_handle_disable(call: ServiceCall) -> None:
        """Handle the disable service call."""
        entity_ids = call.data[ATTR_ENTITY_ID]

        _LOGGER.debug("Disabling quiet mode for %s", entity_ids)

        for entity_id in entity_ids:
            # Retrieve stored volume
            previous_volume = hass.data[DOMAIN][DATA_PREVIOUS_VOLUMES].get(entity_id)

            if previous_volume is None:
                _LOGGER.warning(
                    "No previous volume stored for %s, skipping restore", entity_id
                )
                continue

            # Restore the previous volume
            await hass.services.async_call(
                MEDIA_PLAYER_DOMAIN,
                SERVICE_VOLUME_SET,
                {
                    ATTR_ENTITY_ID: entity_id,
                    ATTR_MEDIA_VOLUME_LEVEL: previous_volume,
                },
                blocking=True,
            )
            _LOGGER.info("Restored volume %s for %s", previous_volume, entity_id)

            # Clean up stored volume
            del hass.data[DOMAIN][DATA_PREVIOUS_VOLUMES][entity_id]

    # Register services
    hass.services.async_register(
        DOMAIN,
        SERVICE_ENABLE,
        async_handle_enable,
        schema=SERVICE_ENABLE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_DISABLE,
        async_handle_disable,
        schema=SERVICE_DISABLE_SCHEMA,
    )

    _LOGGER.info("Quiet Mode integration setup complete")
    return True
