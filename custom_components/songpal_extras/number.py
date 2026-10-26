"""Number platform for Songpal Extras."""

import logging
import re

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SongpalCoordinator, SongpalError
from .receiver import Receiver, receivers

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
    entities = []
    for receiver in receivers(hass):
        # Parse settings from the coordinator's initial data
        settings = receiver.coordinator.data.speakers if receiver.coordinator.data else None
        if not settings:
            _LOGGER.warning("No settings data returned from Sony receiver during setup")
            continue

        for setting in settings:
            if setting.get("type") == "doubleNumberTarget" and setting.get("isAvailable"):
                entities.append(SongpalSpeakerLevelEntity(receiver, setting))

    async_add_entities(entities)


class SongpalSpeakerLevelEntity(CoordinatorEntity[SongpalCoordinator], NumberEntity):
    """Representation of a speaker level control entity."""

    _attr_has_entity_name = True
    _attr_unit_of_measurement = "dB"
    _attr_icon = "mdi:speaker"

    def __init__(self, receiver: Receiver, setting: dict) -> None:
        """Initialize."""
        super().__init__(receiver.coordinator)
        self._target_key = setting["target"]
        snake_key, human_name = convert_target_to_snake_and_name(self._target_key)
        self._target_key_snake = snake_key

        self._attr_name = human_name
        self.entity_id = f"number.{receiver.object_id}_{self._target_key_snake}"
        self._attr_unique_id = f"{receiver.entry_id}_{self._target_key_snake}"

        # Extract range and step constraints
        candidate = setting.get("candidate")
        if isinstance(candidate, list) and len(candidate) > 0:
            candidate = candidate[0]
        if not isinstance(candidate, dict):
            candidate = {}

        self._attr_native_min_value = float(candidate.get("min", -10.0))
        self._attr_native_max_value = float(candidate.get("max", 10.0))
        self._attr_native_step = float(candidate.get("step", 0.5))

        # Associate with the existing device
        self._attr_device_info = receiver.device_info

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
        for setting in self.coordinator.data.speakers:
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
        try:
            await self.coordinator.call(
                "setSpeakerSettings",
                {"settings": [{"target": self._target_key, "value": str(value)}]},
                "1.0",
            )
        except SongpalError as err:
            raise HomeAssistantError(f"Could not set {self._target_key}: {err}") from err
        # Read back what the receiver now has
        await self.coordinator.async_refresh()
