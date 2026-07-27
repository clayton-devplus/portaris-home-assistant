"""Sensores: último heartbeat do leitor."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import PortarisCoordinator
from .entity import reader_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: PortarisCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        PortarisReaderHeartbeat(coordinator, entry.entry_id, reader["id"])
        for reader in coordinator.data["readers"].values()
    ]
    async_add_entities(entities)


class PortarisReaderHeartbeat(CoordinatorEntity[PortarisCoordinator], SensorEntity):
    """Último heartbeat recebido do leitor."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_has_entity_name = True
    _attr_translation_key = "last_heartbeat"
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: PortarisCoordinator, entry_id: str, reader_id: str) -> None:
        super().__init__(coordinator)
        self._reader_id = reader_id
        self._attr_unique_id = f"{entry_id}_reader_{reader_id}_heartbeat"

    @property
    def _reader(self) -> dict | None:
        return self.coordinator.data["readers"].get(self._reader_id)

    @property
    def available(self) -> bool:
        return super().available and self._reader is not None

    @property
    def native_value(self):
        reader = self._reader
        if not reader or not reader.get("lastHeartbeatAt"):
            return None
        return dt_util.parse_datetime(reader["lastHeartbeatAt"])

    @property
    def device_info(self):
        return reader_device_info(self._reader) if self._reader else None
