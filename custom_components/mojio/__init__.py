"""Mojio connected car integration (UI configured)."""
from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_DOMAIN,
    CONF_PASSWORD,
    CONF_USERNAME,
    Platform,
)
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import DEFAULT_DOMAIN, DOMAIN
from .coordinator import MojioCoordinator

PLATFORMS: list[Platform] = [Platform.DEVICE_TRACKER]

# Optional `mojio:` YAML block, used only for a one-time import
# of the credentials into a config entry.
CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Required(CONF_CLIENT_ID): cv.string,
                vol.Required(CONF_CLIENT_SECRET): cv.string,
                vol.Optional(CONF_DOMAIN, default=DEFAULT_DOMAIN): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

type MojioConfigEntry = ConfigEntry[MojioCoordinator]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Import a legacy YAML block into a config entry."""
    if DOMAIN in config:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_IMPORT}, data=dict(config[DOMAIN])
            )
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: MojioConfigEntry) -> bool:
    """Set up Mojio from a config entry."""
    coordinator = MojioCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MojioConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
