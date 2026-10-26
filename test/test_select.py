"""The sound mode: Music (Multi Stereo) or Surround (Auto Format Decoding), switched on the receiver."""

import pytest
from homeassistant.components.select import ATTR_OPTION, DOMAIN as SELECT_DOMAIN, SERVICE_SELECT_OPTION
from homeassistant.const import ATTR_ENTITY_ID, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from conftest import Receiver

SOUND_MODE = "select.living_room_receiver_sound_mode"


async def select(hass: HomeAssistant, option: str) -> None:
    """Picks a sound mode."""
    await hass.services.async_call(
        SELECT_DOMAIN, SERVICE_SELECT_OPTION, {ATTR_ENTITY_ID: SOUND_MODE, ATTR_OPTION: option}, blocking=True
    )


async def test_music_and_surround(hass: HomeAssistant, setup_integration) -> None:
    """The receiver in Multi Stereo is in Music, and offers Surround too."""
    state = hass.states.get(SOUND_MODE)
    assert state.state == "Music"
    assert state.attributes["options"] == ["Music", "Surround"]


async def test_switching_reaches_the_receiver(hass: HomeAssistant, setup_integration, receiver: Receiver) -> None:
    """Surround switches the receiver to Auto Format Decoding."""
    await select(hass, "Surround")
    assert receiver.sets("setSoundSettings") == [{"target": "soundField", "value": "AFD"}]
    assert hass.states.get(SOUND_MODE).state == "Surround"


async def test_another_sound_field_is_neither(
    hass: HomeAssistant, receiver: Receiver, songpal_entry, extras_entry
) -> None:
    """A receiver switched to another sound field elsewhere (Dolby, in the app) is in neither mode."""
    receiver.sound_setting("soundField")["currentValue"] = "dolbyMode"
    assert await hass.config_entries.async_setup(extras_entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(SOUND_MODE).state == STATE_UNKNOWN


async def test_only_what_the_receiver_offers(
    hass: HomeAssistant, receiver: Receiver, songpal_entry, extras_entry
) -> None:
    """A receiver without Multi Stereo offers only Surround."""
    field = receiver.sound_setting("soundField")
    field["candidate"] = [c for c in field["candidate"] if c["value"] != "multiStereo"]
    field["currentValue"] = "AFD"
    assert await hass.config_entries.async_setup(extras_entry.entry_id)
    await hass.async_block_till_done()
    state = hass.states.get(SOUND_MODE)
    assert state.attributes["options"] == ["Surround"]
    assert state.state == "Surround"


async def test_a_switch_the_receiver_refuses(hass: HomeAssistant, setup_integration, receiver: Receiver) -> None:
    """A switch the receiver answers with an error fails the action and keeps the mode."""
    receiver.sound.remove(receiver.sound_setting("soundField"))
    with pytest.raises(HomeAssistantError):
        await select(hass, "Surround")
    assert hass.states.get(SOUND_MODE).state == "Music"
