"""Mojio vehicles as device_tracker entities."""
from __future__ import annotations

from typing import Any

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import MojioConfigEntry
from .const import DOMAIN
from .coordinator import MojioCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MojioConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add a tracker per vehicle, including vehicles added later."""
    coordinator = entry.runtime_data
    known: set[str] = set()

    @callback
    def _add_new() -> None:
        new = [vid for vid in coordinator.data if vid not in known]
        known.update(new)
        if new:
            async_add_entities(MojioTracker(coordinator, vid) for vid in new)

    _add_new()
    entry.async_on_unload(coordinator.async_add_listener(_add_new))


class MojioTracker(CoordinatorEntity[MojioCoordinator], TrackerEntity):
    """A single vehicle."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_icon = "mdi:car"

    def __init__(self, coordinator: MojioCoordinator, vehicle_id: str) -> None:
        super().__init__(coordinator)
        self._vid = vehicle_id
        self._attr_unique_id = f"mojio_{vehicle_id}"
        attrs = coordinator.data[vehicle_id]["attrs"]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, vehicle_id)},
            name=attrs.get("name") or vehicle_id,
            manufacturer="Mojio",
            model="Connected car adapter",
            serial_number=attrs.get("VIN"),
        )

    @property
    def _data(self) -> dict[str, Any] | None:
        return (self.coordinator.data or {}).get(self._vid)

    @property
    def available(self) -> bool:
        return super().available and self._data is not None

    @property
    def source_type(self) -> SourceType:
        return SourceType.GPS

    @property
    def latitude(self) -> float | None:
        return self._data["latitude"] if self._data else None

    @property
    def longitude(self) -> float | None:
        return self._data["longitude"] if self._data else None

    @property
    def location_accuracy(self) -> float:
        return 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return dict(self._data["attrs"]) if self._data else {}
