import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class KocomEnergyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):

    """Kocom Energy config flow."""
    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(self, user_input=None):
        _LOGGER.debug("Config Flow Step ::: async_step_user")

        if user_input is not None:
            return self.async_create_entry(title="",data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=OPTIONS_SCHEMA)


@staticmethod
def async_get_options_flow(config_entry):
    """옵션 플로우 클래스 반환"""
    return KocomEnergyOptionsFlow(config_entry)


OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required("ip", default="10.254.254.1"): str,
        vol.Required("port", default=15000): int,
        vol.Required("auth1", default=""): str,
        vol.Required("auth2", default=""): str,
        vol.Required("update_interval", default=3600): vol.In({
            # 60    : "1분",
            # 180   : "3분",
            300: "5분",
            3600: "1시간",
            86400: "일"
        })
    }
)


class KocomEnergyOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """옵션 설정 폼 표시"""

        if user_input is not None:
            return self.async_create_entry(title="",data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA, self.config_entry.options
            ),
        )
