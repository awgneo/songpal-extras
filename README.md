# Songpal Extras

A custom Home Assistant integration that adds dynamic speaker level controls to Sony AV receivers configured via the native `songpal` integration.

## Features

- **Dynamic Speaker Configuration:** Queries the receiver API to discover only the active speaker channels for your model (e.g., 2.0, 5.1, 7.2) and sets up sliders for them.
- **Dynamic Capabilities:** Detects the allowed range (min, max, step size) for speaker levels directly from the device.
- **No YAML Configuration:** Automatically finds existing `songpal` integrations and adds controls under the same device cards.
- **Sound Mode:** a `select.<receiver>_sound_mode` with **Music** (Multi Stereo, music from every speaker) and **Surround** (Auto Format Decoding, films and TV in their own format), each offered when the receiver has it. A receiver switched to another sound field elsewhere (the Sony Music Center app, the remote) shows neither; the media player's own sound mode still lists every one.
- **Premium Performance:** Optimistic state updates for smooth slider responses in the UI.

## Installation

Install via HACS by adding this repository as a custom repository under settings.

## Developing

A Python project managed with [uv](https://docs.astral.sh/uv/); everything runs through `./flow` (the [flows](../../cellular/flows) task runner):

| Command | What it does |
| --- | --- |
| `flow test` | Runs the pytest suite under `test/` through uv (uv installs Python 3.14 and the dev dependencies) |
| `flow lint` | Lints the integration and its tests with ruff |

The tests run the integration beside a native songpal entry, against a fake receiver (`test/conftest.py`) that answers with an STR-AN1000's own speaker settings (`test/fixtures/speaker_settings.json`) and, like the real one, with a JSON-RPC error for a target it doesn't have.

Changes go through flows' branch workflow (`flow branch`, `flow commit`, `flow promote`, `flow merge`). Every pushed branch is tested in castle's CI, and `main` only merges a green Pull Request. castle's Forgejo is the source; GitHub is its push mirror, which HACS installs from.
