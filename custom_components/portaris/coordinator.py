"""Coordenador de polling do Portaris."""

from __future__ import annotations

import logging
import random
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import PortarisApiError, PortarisAuthError, PortarisClient
from .const import BASE_INTERVAL, DOMAIN, MAX_INTERVAL, SCOPE_STATE_READ

_LOGGER = logging.getLogger(__name__)

# Jitter somado ao intervalo para dessincronizar múltiplas entradas/instâncias.
_JITTER = 5
# Janela de sobreposição na busca de eventos: re-consulta um pouco antes do cursor e deduplica
# por id, para não pular eventos de mesmo timestamp na fronteira da página (LIMIT 200).
_EVENT_OVERLAP = timedelta(seconds=2)


class PortarisCoordinator(DataUpdateCoordinator[dict]):
    """Puxa portas + leitores + eventos incrementais num único ciclo.

    `new_events` guarda só os eventos surgidos no último ciclo (deduplicados por id),
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
            update_interval=timedelta(seconds=BASE_INTERVAL),
        )
        self.client = client
        self.scopes = scopes
        # Cursor iniciado no serverTime do ping → só eventos NOVOS disparam (não o histórico).
        self._event_cursor = initial_cursor
        # Ids já emitidos dentro da janela de overlap (mantido pequeno, só o necessário p/ dedup).
        self._emitted_ids: set[str] = set()
        self._fail_streak = 0
        self.new_events: list[dict] = []

    def _reschedule(self, *, failed: bool) -> None:
        """Backoff exponencial em falha, base em sucesso — sempre com jitter."""
        if failed:
            self._fail_streak += 1
            secs = min(BASE_INTERVAL * (2**self._fail_streak), MAX_INTERVAL)
        else:
            self._fail_streak = 0
            secs = BASE_INTERVAL
        self.update_interval = timedelta(seconds=secs + random.uniform(0, _JITTER))

    async def _async_update_data(self) -> dict:
        # Sem state:read não há o que ler (nem eventos); o setup já barra esse caso, mas
        # defende contra qualquer 403 residual sem cair em loop de reautenticação.
        if SCOPE_STATE_READ not in self.scopes:
            self._reschedule(failed=False)
            return {"doors": {}, "readers": {}}

        try:
            doors = await self.client.get_doors()
            readers = await self.client.get_readers()
            events = await self._fetch_new_events()
        except PortarisAuthError as err:
            # 401 → token inválido/expirado: reautenticar pode resolver.
            raise ConfigEntryAuthFailed(str(err)) from err
        except PortarisApiError as err:
            # Inclui 403 (escopo) e falhas de rede: NÃO dispara reauth; aplica backoff.
            self._reschedule(failed=True)
            raise UpdateFailed(str(err)) from err

        self._reschedule(failed=False)
        return {
            "doors": {d["id"]: d for d in doors},
            "readers": {r["id"]: r for r in readers},
        }

    async def _fetch_new_events(self) -> list[dict]:
        """Busca eventos com overlap + dedup por id; avança o cursor e a janela."""
        since = self._event_cursor
        if since:
            dt = dt_util.parse_datetime(since)
            if dt:
                since = (dt - _EVENT_OVERLAP).isoformat()

        events = await self.client.get_events(since=since, limit=200)

        fresh = [e for e in events if e["id"] not in self._emitted_ids]

        if events:
            newest = max(e["occurredAt"] for e in events)
            self._event_cursor = newest
            newest_dt = dt_util.parse_datetime(newest)
            if newest_dt:
                cutoff = newest_dt - _EVENT_OVERLAP
                # Mantém no set só os ids dentro da janela de overlap (limita o tamanho).
                self._emitted_ids = {
                    e["id"]
                    for e in events
                    if (d := dt_util.parse_datetime(e["occurredAt"])) and d >= cutoff
                }

        self.new_events = fresh
        return events
