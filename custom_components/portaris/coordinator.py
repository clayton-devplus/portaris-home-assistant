"""Coordenador de polling do Portaris."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import PortarisApiError, PortarisAuthError, PortarisClient
from .const import DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class PortarisCoordinator(DataUpdateCoordinator[dict]):
    """Puxa portas + leitores + eventos incrementais num único ciclo.

    `new_events` guarda só os eventos surgidos no último ciclo (ordem crescente),
    para as EventEntity dispararem sem reprocessar histórico.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        client: PortarisClient,
        scopes: list[str],
        initial_cursor: str | None,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )
        self.client = client
        self.scopes = scopes
        # Cursor iniciado no serverTime do ping → só eventos NOVOS disparam (não o histórico).
        self._event_cursor = initial_cursor
        self.new_events: list[dict] = []

    async def _async_update_data(self) -> dict:
        try:
            doors = await self.client.get_doors()
            readers = await self.client.get_readers()
            events = await self.client.get_events(since=self._event_cursor, limit=200)
        except PortarisAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except PortarisApiError as err:
            raise UpdateFailed(str(err)) from err

        if events:
            self._event_cursor = events[-1]["occurredAt"]
        self.new_events = events

        return {
            "doors": {d["id"]: d for d in doors},
            "readers": {r["id"]: r for r in readers},
        }
