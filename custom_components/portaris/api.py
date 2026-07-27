"""Cliente HTTP da API de integração do Portaris."""

from __future__ import annotations

import asyncio
from typing import Any

import aiohttp


class PortarisApiError(Exception):
    """Erro genérico da API."""


class PortarisAuthError(PortarisApiError):
    """401 — token ausente, inválido, revogado ou expirado. Reautenticar pode resolver."""


class PortarisForbiddenError(PortarisApiError):
    """403 — token válido, mas sem o escopo exigido. Reautenticar NÃO resolve."""


class PortarisClient:
    """Wrapper fino sobre `api/v1/integration/*`.

    Recebe a sessão aiohttp do próprio Home Assistant (não cria uma nova).
    """

    def __init__(self, session: aiohttp.ClientSession, host: str, token: str) -> None:
        self._session = session
        self._base = host.rstrip("/") + "/api/v1/integration"
        self._headers = {"Authorization": f"Bearer {token}"}
        self._timeout = aiohttp.ClientTimeout(total=15)

    async def _get(self, path: str, params: dict | None = None) -> Any:
        try:
            async with self._session.get(
                self._base + path,
                headers=self._headers,
                params=params,
                timeout=self._timeout,
            ) as resp:
                if resp.status == 401:
                    raise PortarisAuthError("Token inválido, revogado ou expirado (401).")
                if resp.status == 403:
                    raise PortarisForbiddenError("Token sem o escopo necessário (403).")
                resp.raise_for_status()
                return await resp.json()
        except aiohttp.ClientError as err:
            raise PortarisApiError(str(err)) from err
        except asyncio.TimeoutError as err:
            raise PortarisApiError("Tempo esgotado ao contatar o Portaris.") from err

    async def ping(self) -> dict:
        """Handshake — devolve tenant + escopos concedidos."""
        return await self._get("/ping")

    async def get_doors(self) -> list[dict]:
        return await self._get("/doors")

    async def get_readers(self) -> list[dict]:
        return await self._get("/readers")

    async def get_events(self, since: str | None = None, limit: int = 100) -> list[dict]:
        params: dict[str, Any] = {"limit": limit}
        if since:
            params["since"] = since
        return await self._get("/events", params)

    async def unlock(self, door_id: str) -> None:
        """Abre a porta. Erros de gate (offline/sem leitor/desabilitada) vêm como 4xx."""
        try:
            async with self._session.post(
                f"{self._base}/doors/{door_id}/unlock",
                headers=self._headers,
                timeout=self._timeout,
            ) as resp:
                if resp.status == 401:
                    raise PortarisAuthError("Token inválido, revogado ou expirado (401).")
                if resp.status == 403:
                    raise PortarisForbiddenError("Token sem o escopo necessário (403).")
                resp.raise_for_status()
        except aiohttp.ClientError as err:
            raise PortarisApiError(str(err)) from err
        except asyncio.TimeoutError as err:
            raise PortarisApiError("Tempo esgotado ao abrir a porta.") from err
