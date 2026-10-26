"""The Songpal Extras integration."""

import asyncio
import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[Platform] = [Platform.NUMBER, Platform.SELECT]


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


@dataclass
class SongpalData:
    """What the receiver reports: its speaker settings, and its sound field setting (None when it has none)."""

    speakers: list[dict[str, Any]]
    sound_field: dict[str, Any] | None


class SongpalError(Exception):
    """The receiver couldn't be reached, or answered with an error."""


class SongpalCoordinator(DataUpdateCoordinator[SongpalData]):
    """Coordinator to manage fetching speaker and sound settings from Sony API."""

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

    async def call(self, method: str, params: dict[str, Any], version: str) -> list[Any]:
        """Calls a method of the receiver's audio service and returns its result. The receiver answers an
        error with HTTP 200 and an 'error' in the body, so both are checked."""
        payload = {"method": method, "id": 1, "params": [params], "version": version}
        try:
            async with asyncio.timeout(5):
                async with self.session.post(f"{self.endpoint}/audio", json=payload) as response:
                    if response.status != 200:
                        raise SongpalError(f"{method}: HTTP {response.status}")
                    data = await response.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError) as err:
            raise SongpalError(f"{method}: {err}") from err
        if "error" in data:
            raise SongpalError(f"{method}: {data['error']}")
        return data["result"]

    async def _async_update_data(self) -> SongpalData:
        """Fetch speaker and sound settings from API."""
        try:
            speakers = await self.call("getSpeakerSettings", {"target": ""}, "1.0")
            sound = await self.call("getSoundSettings", {"target": "soundField"}, "1.1")
        except SongpalError as err:
            raise UpdateFailed(f"Error communicating with Sony API: {err}") from err
        sound_field = next((s for s in sound[0] if s.get("target") == "soundField"), None)
        return SongpalData(speakers=speakers[0], sound_field=sound_field)
