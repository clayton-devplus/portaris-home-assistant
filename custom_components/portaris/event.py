"""Entidade de evento: acessos por porta (Granted/Denied/DoorOpened/…)."""

from __future__ import annotations

from homeassistant.components.event import EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, EVENT_TYPES
from .coordinator import PortarisCoordinator
from .entity import door_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: PortarisCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        PortarisDoorEvent(coordinator, entry.entry_id, door["id"])
        for door in coordinator.data["doors"].values()
    ]
    async_add_entities(entities)


class PortarisDoorEvent(CoordinatorEntity[PortarisCoordinator], EventEntity):
    """Dispara a cada novo evento de acesso da porta.

    O coordenador entrega em `new_events` só o que surgiu no último ciclo (cursor ancorado
    no serverTime do ping), então o histórico não é reproduzido no arranque.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "access"
    _attr_event_types = EVENT_TYPES
    _attr_icon = "mdi:badge-account-horizontal"

    def __init__(self, coordinator: PortarisCoordinator, entry_id: str, door_id: str) -> None:
        super().__init__(coordinator)
        self._door_id = door_id
        self._attr_unique_id = f"{entry_id}_door_{door_id}_access"

    @property
    def _door(self) -> dict | None:
        return self.coordinator.data["doors"].get(self._door_id)

    @property
    def device_info(self):
        return door_device_info(self._door) if self._door else None

    @callback
    def _handle_coordinator_update(self) -> None:
        for evt in self.coordinator.new_events:
            if evt.get("doorId") != self._door_id:
                continue
            self._trigger_event(
                evt["type"],
                {
                    "reason": evt.get("reason"),
                    "person": evt.get("personName"),
                    "reader_id": evt.get("readerId"),
                    "occurred_at": evt.get("occurredAt"),
                },
            )
            self.async_write_ha_state()
        super()._handle_coordinator_update()
