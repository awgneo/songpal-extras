"""The Songpal Extras integration."""

import logging
from datetime import timedelta
import asyncio
import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[Platform] = [Platform.NUMBER]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Songpal Extras from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["coordinators"] = {}

    session = async_get_clientsession(hass)
    songpal_entries = hass.config_entries.async_entries("songpal")

    if not songpal_entries:
        _LOGGER.warning(
            "No native Songpal integrations configured. Please add one first."
        )

    for songpal_entry in songpal_entries:
        endpoint = songpal_entry.data.get("endpoint")
        if not endpoint:
            continue

        coordinator = SongpalCoordinator(
            hass, session, endpoint, songpal_entry.title or "Receiver"
        )
        try:
            # Fetch initial data
            await coordinator.async_config_entry_first_refresh()
            hass.data[DOMAIN]["coordinators"][songpal_entry.entry_id] = coordinator
        except Exception as err:
            _LOGGER.error(
                "Error during first refresh for %s: %s", songpal_entry.title, err
            )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.pop(DOMAIN, None)
    return unload_ok


class SongpalCoordinator(DataUpdateCoordinator[list[dict]]):
    """Coordinator to manage fetching speaker settings from Sony API."""

    def __init__(
        self,
        hass: HomeAssistant,
        session: aiohttp.ClientSession,
        endpoint: str,
        name: str,
    ) -> None:
        """Initialize."""
        self.endpoint = endpoint
        self.session = session
        super().__init__(
            hass,
            _LOGGER,
            name=f"Songpal Extras {name}",
            update_interval=timedelta(seconds=30),
        )

    async def _async_update_data(self) -> list[dict]:
        """Fetch speaker settings from API."""
        url = f"{self.endpoint}/audio"
        payload = {
            "method": "getSpeakerSettings",
            "id": 1,
            "params": [{"target": ""}],
            "version": "1.0",
        }
        try:
            async with asyncio.timeout(5):
                async with self.session.post(url, json=payload) as response:
                    if response.status != 200:
                        raise UpdateFailed(f"HTTP error {response.status}")

                    data = await response.json()
                    if "error" in data:
                        raise UpdateFailed(f"API error: {data['error']}")

                    return data["result"][0]
        except Exception as err:
            raise UpdateFailed(f"Error communicating with Sony API: {err}") from err
