"""Config flow for Mojio (UI setup and YAML import)."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_DOMAIN,
    CONF_PASSWORD,
    CONF_USERNAME,
)

from .const import DEFAULT_DOMAIN, DOMAIN
from .coordinator import create_api

_LOGGER = logging.getLogger(__name__)


def _try_login(data: dict[str, Any]) -> str | None:
    """Return None on success, otherwise an error code."""
    try:
        return None if create_api(data).login() else "invalid_auth"
    except Exception:  # noqa: BLE001
        _LOGGER.exception("Mojio: unexpected error during login")
        return "cannot_connect"


class MojioConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Mojio."""

    VERSION = 1

    async def _create(self, data: dict[str, Any]) -> ConfigFlowResult | str:
        await self.async_set_unique_id(f"{data[CONF_DOMAIN]}_{data[CONF_USERNAME].lower()}")
        self._abort_if_unique_id_configured()
        error = await self.hass.async_add_executor_job(_try_login, data)
        if error:
            return error
        return self.async_create_entry(title=f"Mojio ({data[CONF_USERNAME]})", data=data)

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            result = await self._create(user_input)
            if not isinstance(result, str):
                return result
            errors["base"] = result

        schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Required(CONF_CLIENT_ID): str,
                vol.Required(CONF_CLIENT_SECRET): str,
                vol.Required(CONF_DOMAIN, default=DEFAULT_DOMAIN): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_import(self, import_data: dict[str, Any]) -> ConfigFlowResult:
        """Import credentials from the `mojio:` YAML block."""
        data = {**import_data}
        data.setdefault(CONF_DOMAIN, DEFAULT_DOMAIN)
        result = await self._create(data)
        if isinstance(result, str):
            return self.async_abort(reason=result)
        return result
