"""Sensores binários: contato da porta + conectividade do leitor."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PortarisCoordinator
from .entity import door_device_info, reader_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: PortarisCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[BinarySensorEntity] = []
    # Sensor de contato só faz sentido em portas monitoradas.
    for door in coordinator.data["doors"].values():
        if door.get("monitored"):
            entities.append(PortarisDoorContact(coordinator, entry.entry_id, door["id"]))
    for reader in coordinator.data["readers"].values():
        entities.append(PortarisReaderOnline(coordinator, entry.entry_id, reader["id"]))

    async_add_entities(entities)


class PortarisDoorContact(CoordinatorEntity[PortarisCoordinator], BinarySensorEntity):
    """Aberta/fechada (sensor de contato da porta)."""

    _attr_device_class = BinarySensorDeviceClass.DOOR
    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, coordinator: PortarisCoordinator, entry_id: str, door_id: str) -> None:
        super().__init__(coordinator)
        self._door_id = door_id
        self._attr_unique_id = f"{entry_id}_door_{door_id}_contact"

    @property
    def _door(self) -> dict | None:
        return self.coordinator.data["doors"].get(self._door_id)

    @property
    def available(self) -> bool:
        return super().available and self._door is not None

    @property
    def is_on(self) -> bool | None:
        door = self._door
        return bool(door["isOpen"]) if door else None

    @property
    def device_info(self):
        return door_device_info(self._door) if self._door else None


class PortarisReaderOnline(CoordinatorEntity[PortarisCoordinator], BinarySensorEntity):
    """Conectividade do leitor (Online = conectado)."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_has_entity_name = True
    _attr_translation_key = "reader_online"

    def __init__(self, coordinator: PortarisCoordinator, entry_id: str, reader_id: str) -> None:
        super().__init__(coordinator)
        self._reader_id = reader_id
        self._attr_unique_id = f"{entry_id}_reader_{reader_id}_online"

    @property
    def _reader(self) -> dict | None:
        return self.coordinator.data["readers"].get(self._reader_id)

    @property
    def available(self) -> bool:
        return super().available and self._reader is not None

    @property
    def is_on(self) -> bool | None:
        reader = self._reader
        return reader["status"] == "Online" if reader else None

    @property
    def device_info(self):
        return reader_device_info(self._reader) if self._reader else None
