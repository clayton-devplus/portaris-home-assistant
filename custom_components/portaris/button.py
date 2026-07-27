"""Botão de abertura de porta (só com o escopo door:unlock)."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import PortarisApiError
from .const import DOMAIN, SCOPE_DOOR_UNLOCK
from .coordinator import PortarisCoordinator
from .entity import door_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: PortarisCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Sem o escopo de abertura, não expõe botão nenhum.
    if SCOPE_DOOR_UNLOCK not in coordinator.scopes:
        return

    entities = [
        PortarisUnlockButton(coordinator, entry.entry_id, door["id"])
        for door in coordinator.data["doors"].values()
        if door.get("receptionEnabled")
    ]
    async_add_entities(entities)


class PortarisUnlockButton(CoordinatorEntity[PortarisCoordinator], ButtonEntity):
    """Abre a porta (ação momentânea). Só existe para portas habilitadas na recepção."""

    _attr_has_entity_name = True
    _attr_translation_key = "unlock"
    _attr_icon = "mdi:door-open"

    def __init__(self, coordinator: PortarisCoordinator, entry_id: str, door_id: str) -> None:
        super().__init__(coordinator)
        self._door_id = door_id
        self._attr_unique_id = f"{entry_id}_door_{door_id}_unlock"

    @property
    def _door(self) -> dict | None:
        return self.coordinator.data["doors"].get(self._door_id)

    @property
    def available(self) -> bool:
        door = self._door
        # Barra na UI o que o servidor barraria: leitor offline não abre.
        return super().available and door is not None and bool(door.get("online"))

    @property
    def device_info(self):
        return door_device_info(self._door) if self._door else None

    async def async_press(self) -> None:
        try:
            await self.coordinator.client.unlock(self._door_id)
        except PortarisApiError as err:
            raise HomeAssistantError(f"Não foi possível abrir a porta: {err}") from err
        # Reflete rápido a mudança de estado (porta abrindo).
        await self.coordinator.async_request_refresh()
