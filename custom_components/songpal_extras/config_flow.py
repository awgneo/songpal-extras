"""Config flow for Songpal Extras integration."""

import logging
from typing import Any

from homeassistant import config_entries
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class SongpalExtrasConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Songpal Extras."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the user step (one-click setup)."""
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")

        if user_input is not None:
            return self.async_create_entry(title="Songpal Extras", data={})

        return self.async_show_form(step_id="user")
