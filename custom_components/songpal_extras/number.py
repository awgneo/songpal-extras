"""Number platform for Songpal Extras."""

import logging
import re
import asyncio

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from . import SongpalCoordinator

_LOGGER = logging.getLogger(__name__)


def convert_target_to_snake_and_name(target: str) -> tuple[str, str]:
    """Convert camelCase to snake_case and human readable name."""
    mapping = {
        "frontLLevel": ("front_left_level", "Front Left Level"),
        "frontRLevel": ("front_right_level", "Front Right Level"),
        "centerLevel": ("center_level", "Center Level"),
        "center1Level": ("center1_level", "Center 1 Level"),
        "surroundLLevel": ("surround_left_level", "Surround Left Level"),
        "surroundRLevel": ("surround_right_level", "Surround Right Level"),
        "surroundBackLLevel": ("surround_back_left_level", "Surround Back Left Level"),
        "surroundBackRLevel": (
            "surround_back_right_level",
            "Surround Back Right Level",
        ),
        "subwooferLevel": ("subwoofer_level", "Subwoofer Level"),
        "subwoofer1Level": ("subwoofer1_level", "Subwoofer 1 Level"),
        "subwoofer2Level": ("subwoofer2_level", "Subwoofer 2 Level"),
    }
    if target in mapping:
        return mapping[target]

    s = target
    s = s.replace("LLevel", "_left_level")
    s = s.replace("RLevel", "_right_level")
    s = s.replace("Level", "_level")
    s = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", s)
    s = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s).lower().strip("_")

    name = " ".join(word.capitalize() for word in s.split("_"))
    return s, name


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Songpal Extras number platform."""
    coordinators = hass.data[DOMAIN]["coordinators"]

    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)

    entities = []
    for songpal_entry_id, coordinator in coordinators.items():
        songpal_entry = hass.config_entries.async_get_entry(songpal_entry_id)
        if not songpal_entry:
            continue

        # Find the device associated with this songpal entry
        matching_device = None
        for device in device_registry.devices.values():
            if songpal_entry_id in device.config_entries:
                matching_device = device
                break

        if not matching_device:
            _LOGGER.warning(
                "Could not find matching device for songpal config entry: %s",
                songpal_entry.title,
            )
            continue

        # Search for a media_player entity linked to this device to copy its object ID
        media_player_object_id = None
        for entity in entity_registry.entities.values():
            if (
                entity.device_id == matching_device.id
                and entity.domain == "media_player"
            ):
                media_player_object_id = entity.entity_id.split(".")[1]
                break

        if not media_player_object_id:
            media_player_object_id = matching_device.name.lower().replace(" ", "_")

        # Parse settings from the coordinator's initial data
        settings = coordinator.data
        if not settings:
            _LOGGER.warning("No settings data returned from Sony receiver during setup")
            continue

        for setting in settings:
            if setting.get("type") == "doubleNumberTarget" and setting.get(
                "isAvailable"
            ):
                entities.append(
                    SongpalSpeakerLevelEntity(
                        coordinator,
                        setting,
                        matching_device,
                        media_player_object_id,
                        songpal_entry_id,
                    )
                )

    async_add_entities(entities)


class SongpalSpeakerLevelEntity(CoordinatorEntity[SongpalCoordinator], NumberEntity):
    """Representation of a speaker level control entity."""

    _attr_has_entity_name = True
    _attr_unit_of_measurement = "dB"
    _attr_icon = "mdi:speaker"

    def __init__(
        self,
        coordinator: SongpalCoordinator,
        setting: dict,
        device: dr.DeviceEntry,
        media_player_object_id: str,
        songpal_entry_id: str,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._target_key = setting["target"]
        snake_key, human_name = convert_target_to_snake_and_name(self._target_key)
        self._target_key_snake = snake_key

        self._attr_name = human_name
        self.entity_id = f"number.{media_player_object_id}_{self._target_key_snake}"
        self._attr_unique_id = f"{songpal_entry_id}_{self._target_key_snake}"

        # Extract range and step constraints
        candidate = setting.get("candidate", {})
        self._attr_native_min_value = float(candidate.get("min", -10.0))
        self._attr_native_max_value = float(candidate.get("max", 10.0))
        self._attr_native_step = float(candidate.get("step", 0.5))

        # Associate with the existing device
        self._attr_device_info = DeviceInfo(
            identifiers=device.identifiers,
            connections=device.connections,
            name=device.name,
            manufacturer=device.manufacturer,
            model=device.model,
            sw_version=device.sw_version,
        )

        self._update_value_from_coordinator()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_value_from_coordinator()
        self.async_write_ha_state()

    def _update_value_from_coordinator(self) -> None:
        """Extract the current value for this setting from coordinator data."""
        if not self.coordinator.data:
            self._attr_available = False
            return

        # Find the setting object matching this target
        for setting in self.coordinator.data:
            if setting.get("target") == self._target_key:
                self._attr_available = setting.get("isAvailable", False)
                try:
                    self._attr_native_value = float(setting["currentValue"])
                except ValueError, TypeError:
                    self._attr_native_value = 0.0
                return

        self._attr_available = False

    async def async_set_native_value(self, value: float) -> None:
        """Set new speaker level."""
        url = f"{self.coordinator.endpoint}/audio"
        payload = {
            "method": "setSpeakerSettings",
            "id": 1,
            "params": [
                {"settings": [{"target": self._target_key, "value": str(value)}]}
            ],
            "version": "1.0",
        }
        try:
            async with asyncio.timeout(5):
                async with self.coordinator.session.post(url, json=payload) as response:
                    if response.status != 200:
                        _LOGGER.error(
                            "Failed to set speaker level: HTTP %s", response.status
                        )
                        return

                    # Force immediate update in coordinator data to reflect in UI instantly
                    if self.coordinator.data:
                        for idx, setting in enumerate(self.coordinator.data):
                            if setting.get("target") == self._target_key:
                                self.coordinator.data[idx]["currentValue"] = str(value)
                                break

                    self._update_value_from_coordinator()
                    self.async_write_ha_state()

                    # Trigger a coordinator refresh in the background to sync state
                    self.coordinator.async_set_updated_data(self.coordinator.data)
        except Exception as err:
            _LOGGER.error(
                "Error setting speaker level for %s: %s", self._target_key, err
            )
