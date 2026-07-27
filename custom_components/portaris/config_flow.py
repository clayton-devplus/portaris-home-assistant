"""Fluxo de configuração da integração Portaris."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PortarisApiError, PortarisAuthError, PortarisClient
from .const import CONF_HOST, CONF_TOKEN, DEFAULT_HOST, DOMAIN


class PortarisConfigFlow(ConfigFlow, domain=DOMAIN):
    """Coleta host + token e valida via /ping."""

    VERSION = 1

    async def _validate(self, host: str, token: str) -> dict:
        session = async_get_clientsession(self.hass)
        client = PortarisClient(session, host, token)
        return await client.ping()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            token = user_input[CONF_TOKEN].strip()
            try:
                info = await self._validate(host, token)
            except PortarisAuthError:
                errors["base"] = "invalid_auth"
            except PortarisApiError:
                errors["base"] = "cannot_connect"
            else:
                tenant = info.get("tenant") or "Portaris"
                await self.async_set_unique_id(f"{host}::{tenant}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=tenant,
                    data={CONF_HOST: host, CONF_TOKEN: token},
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
                vol.Required(CONF_TOKEN): str,
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Disparado quando o token para de valer (revogado/expirado)."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry: ConfigEntry | None = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        if user_input is not None and entry is not None:
            host = entry.data[CONF_HOST]
            token = user_input[CONF_TOKEN].strip()
            try:
                await self._validate(host, token)
            except PortarisAuthError:
                errors["base"] = "invalid_auth"
            except PortarisApiError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(
                    entry, data={**entry.data, CONF_TOKEN: token}
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_TOKEN): str}),
            errors=errors,
        )
