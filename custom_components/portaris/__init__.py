"""Integração Portaris para o Home Assistant."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryError,
    ConfigEntryNotReady,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PortarisApiError, PortarisAuthError, PortarisClient
from .const import CONF_HOST, CONF_TOKEN, DOMAIN, SCOPE_STATE_READ
from .coordinator import PortarisCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.SENSOR,
    Platform.EVENT,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configura uma conta Portaris."""
    session = async_get_clientsession(hass)
    client = PortarisClient(session, entry.data[CONF_HOST], entry.data[CONF_TOKEN])

    # Ping: valida o token e ancora o cursor de eventos no relógio do servidor.
    try:
        info = await client.ping()
    except PortarisAuthError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except PortarisApiError as err:
        raise ConfigEntryNotReady(str(err)) from err

    # A leitura de estado (portas/leitores/eventos) é a base da integração. Sem 'state:read'
    # todo poll levaria 403 → falha clara no setup, em vez de um loop de reautenticação.
    scopes = info.get("scopes", [])
    if SCOPE_STATE_READ not in scopes:
        raise ConfigEntryError(
            "O token de integração precisa da permissão 'Ler estado' (state:read). "
            "Gere um novo token no painel do Portaris com essa permissão marcada."
        )

    coordinator = PortarisCoordinator(
        hass,
        client,
        scopes=scopes,
        initial_cursor=info.get("serverTime"),
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Descarrega a conta."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
