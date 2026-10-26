"""Select platform for Songpal Extras: Music or Surround, each one of the receiver's sound fields."""

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SongpalCoordinator, SongpalError
from .receiver import Receiver, receivers

# Each sound mode's sound field: Multi Stereo plays music from every speaker, and Auto Format Decoding
# plays films and TV in their own surround format
SOUND_MODES = {
    "Music": "multiStereo",
    "Surround": "AFD",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Songpal Extras select platform."""
    entities = []
    for receiver in receivers(hass):
        sound_field = receiver.coordinator.data.sound_field if receiver.coordinator.data else None
        if sound_field and available_modes(sound_field):
            entities.append(SongpalSoundModeEntity(receiver))
    async_add_entities(entities)


def available_modes(sound_field: dict) -> list[str]:
    """The sound modes whose sound field the receiver offers."""
    offered = {candidate.get("value") for candidate in sound_field.get("candidate", []) if candidate.get("isAvailable")}
    return [mode for mode, field in SOUND_MODES.items() if field in offered]


class SongpalSoundModeEntity(CoordinatorEntity[SongpalCoordinator], SelectEntity):
    """The receiver's sound field as Music or Surround; neither when it's in another one."""

    _attr_has_entity_name = True
    _attr_name = "Sound Mode"
    _attr_icon = "mdi:surround-sound"

    def __init__(self, receiver: Receiver) -> None:
        """Initialize."""
        super().__init__(receiver.coordinator)
        self.entity_id = f"select.{receiver.object_id}_sound_mode"
        self._attr_unique_id = f"{receiver.entry_id}_sound_mode"
        self._attr_device_info = receiver.device_info
        self._update_from_coordinator()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_from_coordinator()
        self.async_write_ha_state()

    def _update_from_coordinator(self) -> None:
        """The modes the receiver offers, and which one it's in."""
        sound_field = self.coordinator.data.sound_field if self.coordinator.data else None
        if not sound_field:
            self._attr_available = False
            return
        self._attr_available = bool(sound_field.get("isAvailable"))
        self._attr_options = available_modes(sound_field)
        current = sound_field.get("currentValue")
        self._attr_current_option = next(
            (mode for mode in self._attr_options if SOUND_MODES[mode] == current), None
        )

    async def async_select_option(self, option: str) -> None:
        """Switch the receiver to the mode's sound field."""
        try:
            await self.coordinator.call(
                "setSoundSettings",
                {"settings": [{"target": "soundField", "value": SOUND_MODES[option]}]},
                "1.1",
            )
        except SongpalError as err:
            raise HomeAssistantError(f"Could not switch to {option}: {err}") from err
        # Read back what the receiver now has
        await self.coordinator.async_refresh()
