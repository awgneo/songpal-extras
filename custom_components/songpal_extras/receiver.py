"""The receivers this integration extends: each native songpal entry's device and media player."""

import logging
from dataclasses import dataclass

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo

from . import SongpalCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass
class Receiver:
    """A receiver songpal set up: its entry, its coordinator, its device, and the object ID of its media
    player, which this integration's entity IDs start with."""

    entry_id: str
    coordinator: SongpalCoordinator
    device: dr.DeviceEntry
    object_id: str

    @property
    def device_info(self) -> DeviceInfo:
        """songpal's device, which this integration's entities join."""
        return DeviceInfo(
            identifiers=self.device.identifiers,
            connections=self.device.connections,
            name=self.device.name,
            manufacturer=self.device.manufacturer,
            model=self.device.model,
            sw_version=self.device.sw_version,
        )


def receivers(hass: HomeAssistant) -> list[Receiver]:
    """Each receiver whose coordinator read it at setup, with songpal's device for it."""
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    found = []
    for entry_id, coordinator in hass.data[DOMAIN]["coordinators"].items():
        entry = hass.config_entries.async_get_entry(entry_id)
        if not entry:
            continue

        device = next((d for d in device_registry.devices.values() if entry_id in d.config_entries), None)
        if not device:
            _LOGGER.warning("Could not find matching device for songpal config entry: %s", entry.title)
            continue

        # The media player's object ID, so this integration's entities are named after it
        object_id = next(
            (
                entity.entity_id.split(".")[1]
                for entity in entity_registry.entities.values()
                if entity.device_id == device.id and entity.domain == "media_player"
            ),
            device.name.lower().replace(" ", "_"),
        )
        found.append(Receiver(entry_id, coordinator, device, object_id))
    return found
