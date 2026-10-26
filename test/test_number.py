"""The speaker levels: one slider per level the receiver has, set on the receiver."""

from homeassistant.components.number import ATTR_VALUE, DOMAIN as NUMBER_DOMAIN, SERVICE_SET_VALUE
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from conftest import Receiver

LEVELS = {
    "number.living_room_receiver_center1_level": "5.0",
    "number.living_room_receiver_center_level": "5.0",
    "number.living_room_receiver_front_left_level": "-1.5",
    "number.living_room_receiver_front_right_level": "-1.5",
    "number.living_room_receiver_subwoofer_level": "-10.0",
    "number.living_room_receiver_surround_back_left_level": "3.5",
    "number.living_room_receiver_surround_back_right_level": "7.5",
    "number.living_room_receiver_surround_left_level": "1.5",
    "number.living_room_receiver_surround_right_level": "10.0",
}


async def test_levels_the_receiver_has(hass: HomeAssistant, setup_integration) -> None:
    """Each level the receiver has connected becomes a slider with its value, and no other does."""
    states = {state.entity_id: state.state for state in hass.states.async_all(NUMBER_DOMAIN)}
    assert states == LEVELS


async def test_levels_take_the_receivers_range(hass: HomeAssistant, setup_integration) -> None:
    """A level's range and step are the receiver's."""
    state = hass.states.get("number.living_room_receiver_subwoofer_level")
    assert state.attributes["min"] == -10.0
    assert state.attributes["max"] == 10.0
    assert state.attributes["step"] == 0.5


async def test_levels_join_the_receivers_device(hass: HomeAssistant, setup_integration) -> None:
    """The sliders belong to the device songpal made for the receiver."""
    device = dr.async_get(hass).async_get_device(identifiers={("songpal", "00:11:22:33:44:55")})
    entity = er.async_get(hass).async_get("number.living_room_receiver_subwoofer_level")
    assert entity.device_id == device.id


async def test_setting_a_level_reaches_the_receiver(
    hass: HomeAssistant, setup_integration, receiver: Receiver
) -> None:
    """Setting a slider sets that level on the receiver."""
    await hass.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: "number.living_room_receiver_subwoofer_level", ATTR_VALUE: -4.5},
        blocking=True,
    )
    assert receiver.sets == [{"target": "subwooferLevel", "value": "-4.5"}]
    assert receiver.setting("subwooferLevel")["currentValue"] == "-4.5"
    assert hass.states.get("number.living_room_receiver_subwoofer_level").state == "-4.5"
