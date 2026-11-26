"""Mojio connected car integration (UI configured)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

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
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.helpers import device_registry as dr
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


_SECRET_KEYS = ("api", "session", "token", "password", "secret", "client")


def _serialize(obj: Any, depth: int = 0) -> Any:
    """Turn SDK objects into JSON-friendly data (without credentials)."""
    if depth > 6:
        return str(obj)
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {
            str(k): _serialize(v, depth + 1)
            for k, v in obj.items()
            if not any(s in str(k).lower() for s in _SECRET_KEYS)
        }
    if isinstance(obj, (list, tuple, set)):
        return [_serialize(v, depth + 1) for v in obj]
    if hasattr(obj, "__dict__"):
        return _serialize(vars(obj), depth + 1)
    return str(obj)


_PAGE = 100
_DROP_KEYS = ("Polyline", "OwnerId", "Links", "Permissions")


def _fetch_trips(api: Any, limit: int) -> list[dict[str, Any]]:
    """Page through /v2/trips (newest first) up to ``limit`` trips."""
    styles = (("top", "skip"), ("$top", "$skip"))
    for top_key, skip_key in styles:
        trips: list[dict[str, Any]] = []
        skip = 0
        while len(trips) < limit:
            size = min(_PAGE, limit - len(trips))
            data = api._get_response(f"trips?{top_key}={size}&{skip_key}={skip}")  # noqa: SLF001
            page = (data or {}).get("Data") or []
            trips.extend(page)
            if len(page) < size:
                break
            skip += size
        # The API ignores unknown paging keys and returns its default page
        # (10 trips) – then try the other syntax.
        if len(trips) > 10 or top_key == styles[-1][0]:
            return trips[:limit]
    return []


async def _async_get_trips(call: ServiceCall) -> ServiceResponse:
    """Return trips from the Mojio cloud (newest first) for every configured account."""
    hass = call.hass
    limit = int(call.data.get("limit", 1000))
    trips: list[Any] = []
    for entry in hass.config_entries.async_loaded_entries(DOMAIN):
        coordinator: MojioCoordinator = entry.runtime_data
        raw = await hass.async_add_executor_job(_fetch_trips, coordinator.api, limit)
        for trip in raw:
            trips.append(
                _serialize({k: v for k, v in trip.items() if k not in _DROP_KEYS})
            )
    return {"count": len(trips), "trips": trips}


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register services and import a legacy YAML block into a config entry."""
    hass.services.async_register(
        DOMAIN,
        "get_trips",
        _async_get_trips,
        schema=vol.Schema(
            {vol.Optional("limit", default=1000): vol.All(int, vol.Range(min=1, max=5000))}
        ),
        supports_response=SupportsResponse.ONLY,
    )
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


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: MojioConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Allow removing a vehicle that is no longer reported by the account."""
    current = set((entry.runtime_data.data or {}).keys())
    return not any(
        domain == DOMAIN and vehicle_id in current
        for domain, vehicle_id in device_entry.identifiers
    )
