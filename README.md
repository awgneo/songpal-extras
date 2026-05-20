# Songpal Extras

A custom Home Assistant integration that adds dynamic speaker level controls to Sony AV receivers configured via the native `songpal` integration.

## Features

- **Dynamic Speaker Configuration:** Queries the receiver API to discover only the active speaker channels for your model (e.g., 2.0, 5.1, 7.2) and sets up sliders for them.
- **Dynamic Capabilities:** Detects the allowed range (min, max, step size) for speaker levels directly from the device.
- **No YAML Configuration:** Automatically finds existing `songpal` integrations and adds controls under the same device cards.
- **Premium Performance:** Optimistic state updates for smooth slider responses in the UI.

## Installation

Install via HACS by adding this repository as a custom repository under settings.
