"""Test configuration: the integration set up beside a native songpal entry, against a fake receiver."""

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
    AiohttpClientMockResponse,
)

from custom_components.songpal_extras.const import DOMAIN

FIXTURES = Path(__file__).parent / "fixtures"
ENDPOINT = "http://192.168.1.3:10000/sony"


def fixture(name: str) -> Any:
    """A JSON fixture."""
    return json.loads((FIXTURES / name).read_text())


class Receiver:
    """A Sony receiver's audio service: its speaker and sound settings as an STR-AN1000 reported them, and
    the requests it was sent. Like the real one, it answers an unknown target with a JSON-RPC error."""

    def __init__(self) -> None:
        self.settings: list[dict[str, Any]] = copy.deepcopy(fixture("speaker_settings.json")["result"][0])
        self.sound: list[dict[str, Any]] = copy.deepcopy(fixture("sound_settings.json")["result"][0])
        self.requests: list[dict[str, Any]] = []

    def setting(self, target: str) -> dict[str, Any]:
        """The receiver's speaker setting for a target."""
        return next(setting for setting in self.settings if setting["target"] == target)

    def sound_setting(self, target: str) -> dict[str, Any]:
        """The receiver's sound setting for a target."""
        return next(setting for setting in self.sound if setting["target"] == target)

    @staticmethod
    def change(settings: list[dict[str, Any]], request: dict[str, Any]) -> dict[str, Any]:
        """Applies a set request's changes to settings, or answers the error the receiver would."""
        for change in request["params"][0]["settings"]:
            if not any(setting["target"] == change["target"] for setting in settings):
                return {"error": [3, "Illegal Argument"], "id": request["id"]}
        for change in request["params"][0]["settings"]:
            next(s for s in settings if s["target"] == change["target"])["currentValue"] = change["value"]
        return {"result": [], "id": request["id"]}

    async def answer(self, method: str, url: Any, data: Any) -> AiohttpClientMockResponse:
        """Answers one request to the audio service."""
        request = json.loads(data) if isinstance(data, (str, bytes)) else data
        self.requests.append(request)
        if request["method"] == "getSpeakerSettings":
            body = {"result": [self.settings], "id": request["id"]}
        elif request["method"] == "setSpeakerSettings":
            body = self.change(self.settings, request)
        elif request["method"] == "getSoundSettings":
            target = request["params"][0]["target"]
            body = {"result": [[s for s in self.sound if target in ("", s["target"])]], "id": request["id"]}
        elif request["method"] == "setSoundSettings":
            body = self.change(self.sound, request)
        else:
            body = {"error": [12, "No Such Method"], "id": request["id"]}
        return AiohttpClientMockResponse(method, url, json=body)

    def sets(self, method: str = "setSpeakerSettings") -> list[dict[str, Any]]:
        """The settings each request to a set method sent."""
        return [
            change
            for request in self.requests
            if request["method"] == method
            for change in request["params"][0]["settings"]
        ]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def receiver(aioclient_mock: AiohttpClientMocker) -> Receiver:
    """The fake receiver, answering at the songpal entry's endpoint."""
    receiver = Receiver()
    aioclient_mock.post(f"{ENDPOINT}/audio", side_effect=receiver.answer)
    return receiver


@pytest.fixture
def songpal_entry(hass: HomeAssistant) -> MockConfigEntry:
    """The native songpal integration's entry, with its device and media player, as songpal leaves them.
    songpal itself counts as loaded: these tests are about what this integration adds beside it."""
    entry = MockConfigEntry(
        domain="songpal",
        title="Living Room Receiver",
        data={"name": "Living Room Receiver", "endpoint": ENDPOINT},
        unique_id="00:11:22:33:44:55",
    )
    entry.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={("songpal", "00:11:22:33:44:55")},
        connections={(dr.CONNECTION_NETWORK_MAC, "00:11:22:33:44:55")},
        manufacturer="Sony Corporation",
        model="STR-AN1000",
        name="Living Room Receiver",
    )
    er.async_get(hass).async_get_or_create(
        "media_player",
        "songpal",
        "00:11:22:33:44:55",
        config_entry=entry,
        device_id=device.id,
        suggested_object_id="living_room_receiver",
    )
    hass.config.components.add("songpal")
    return entry


@pytest.fixture
def extras_entry(hass: HomeAssistant) -> MockConfigEntry:
    """This integration's one entry."""
    entry = MockConfigEntry(domain=DOMAIN, title="Songpal Extras", data={})
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
async def setup_integration(
    hass: HomeAssistant, receiver: Receiver, songpal_entry: MockConfigEntry, extras_entry: MockConfigEntry
) -> MockConfigEntry:
    """Sets the integration up beside the songpal entry."""
    assert await hass.config_entries.async_setup(extras_entry.entry_id)
    await hass.async_block_till_done()
    return extras_entry
