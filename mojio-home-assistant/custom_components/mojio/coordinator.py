"""Data update coordinator for the Mojio cloud."""
from __future__ import annotations

import logging
from typing import Any

from mojio_sdk.api import API
from mojio_sdk.trip import Trip

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_DOMAIN,
    CONF_PASSWORD,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


def create_api(data: dict[str, Any]) -> API:
    """Create a Mojio API client from credentials."""
    return API(
        data[CONF_DOMAIN],
        data[CONF_CLIENT_ID],
        data[CONF_CLIENT_SECRET],
        data[CONF_USERNAME],
        data[CONF_PASSWORD],
    )


def _vehicle_data(api: API, vehicle: Any, trips: Any) -> dict[str, Any]:
    """Build position and attributes for one vehicle (same attributes as the legacy tracker)."""
    last_comp_trip = Trip.get_last_trip(trips, vehicle.mojio_id, True)
    if not last_comp_trip.has_data:
        last_comp_trip = api.get_trip(vehicle.last_trip_id)

    location = vehicle.location
    lat = getattr(location, "latitude", None)
    lon = getattr(location, "longitude", None)

    attrs = {
        "VIN": vehicle.getattribute("vin"),
        "name": vehicle.getattribute("name"),
        "parked": vehicle.getattribute("parked"),
        "status": vehicle.getattribute("status"),
        "direction": vehicle.getattribute("heading_direction"),
        "left_turn": vehicle.getattribute("left_turn"),
        "idle": vehicle.getattribute("idle"),
        "ignition_state": vehicle.getattribute("ignition_state"),
        "disturbance_state": vehicle.getattribute("disturbance_state"),
        "tow_state": vehicle.getattribute("tow_state"),
        "last_contact": vehicle.getattribute("last_contact"),
        "last_trip_id": vehicle.getattribute("last_trip_id"),
        "rpm": vehicle.getattribute("current_rpm", None),
        "speed_mph": vehicle.getattribute("current_speed_mph", None),
        "speed_kph": vehicle.getattribute("current_speed_kph", None),
        "seatbelt_warn": vehicle.getattribute("seatbelt_status_warning", False),
        "address": location.getattribute("formatted_address"),
        "battery_voltage": vehicle.battery.getattribute("value"),
        "fuel_level": vehicle.fuel.getattribute("fuel_level", None),
        "virtual_fuel_level": vehicle.fuel.getattribute("virtual_fuel_level", None),
        "oil_temp_f": vehicle.engine_oil.getattribute("temp_f", None),
        "oil_temp_c": vehicle.engine_oil.getattribute("temp_c", None),
        "dtc_count": vehicle.dtc.getattribute("count"),
        "dtc_details": vehicle.dtc.getattribute("details", None),
        "lct_start": last_comp_trip.getattribute("start_date"),
        "lct_end": last_comp_trip.getattribute("end_date"),
        "lct_mpg": last_comp_trip.getattribute("mpg", None),
        "lct_kpl": last_comp_trip.getattribute("kpl", None),
        "lct_max_mph": last_comp_trip.getattribute("max_speed_mph", None),
        "lct_max_kph": last_comp_trip.getattribute("max_speed_kph", None),
        "lct_distance_mi": last_comp_trip.getattribute("distance_mi", None),
        "lct_distance_km": last_comp_trip.getattribute("distance_km", None),
        "lct_duration": last_comp_trip.getattribute("duration"),
    }
    return {"latitude": lat, "longitude": lon, "attrs": attrs}


class MojioCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Poll all vehicles of the account every 5 minutes."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
            config_entry=entry,
        )
        self.api = create_api(dict(entry.data))
        self._logged_in = False

    def _fetch(self) -> dict[str, dict[str, Any]]:
        if not self._logged_in:
            if not self.api.login():
                raise UpdateFailed("Mojio login failed")
            self._logged_in = True
        try:
            trips = self.api.get_trips()
            vehicles = self.api.get_vehicles()
        except Exception as err:
            # Log in again on the next update (expired token etc.).
            self._logged_in = False
            raise UpdateFailed(f"Mojio returned no data: {err}") from err

        result: dict[str, dict[str, Any]] = {}
        for vehicle in vehicles:
            if not getattr(vehicle, "id", None):
                # Skip empty / unplugged records without an ID.
                continue
            try:
                result[str(vehicle.id)] = _vehicle_data(self.api, vehicle, trips)
            except Exception as err:  # one broken vehicle must not break the others
                _LOGGER.warning("Mojio: no data for vehicle %s: %s", vehicle.id, err)
        return result

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        return await self.hass.async_add_executor_job(self._fetch)
