# Mojio for Home Assistant

Custom integration for [Mojio](https://www.moj.io/) connected-car adapters (OBD-II), e.g. the
**T-Mobile Chytré auto** service in the Czech Republic. Every vehicle on your account becomes a
`device_tracker` entity with its position and live OBD data as attributes.

Based on the original legacy component by [Simon Tenbeitel](https://github.com/simontb/mojio-home-assistant)
(MIT), rewritten as a modern UI-configured integration.

## Features

- Setup from the UI (Settings → Devices & services), no YAML needed
- One tracker per vehicle, new vehicles are added automatically
- Cloud polling every 5 minutes
- Attributes: VIN, name, parked / ignition / idle / tow / disturbance state, heading, speed, RPM,
  battery voltage, fuel level, oil temperature, engine fault codes (count + details), address and
  the last completed trip (start, end, distance, duration, max speed, consumption)

## Installation

### Marketplace (recommended)
1. Settings → Marketplace → **Add from link** → `https://github.com/GITHUB_USER/mojio-home-assistant`
2. Install **Mojio**, restart Home Assistant.

### Manual
Copy `custom_components/mojio` into your `config/custom_components` folder and restart.

## Configuration

Settings → Devices & services → **Add integration** → *Mojio*, then enter:

| Field | Description |
|---|---|
| E-mail / Password | Login of your Mojio account (the same as in your operator's app) |
| Client ID / Client secret | Credentials of the Mojio application used by your operator |
| Domain | Operator environment, e.g. `tmobile-cz` |

No credentials are shipped with this integration.

### Migrating from the legacy YAML component
Replace the old `device_tracker: - platform: mojio …` block with:

```yaml
mojio:
  domain: tmobile-cz
  client_id: !secret mojio_client_id
  client_secret: !secret mojio_client_secret
  username: !secret mojio_user
  password: !secret mojio_pass
```

remove the cars from `known_devices.yaml` and restart. The credentials are imported into a config
entry once; afterwards the YAML block can be deleted. To keep your old entity IDs, rename the new
entities in Settings → Entities.

## Example template sensor

```yaml
template:
  - sensor:
      - name: Car battery
        unit_of_measurement: V
        device_class: voltage
        state: "{{ state_attr('device_tracker.my_car', 'battery_voltage') }}"
```

## Disclaimer

This is an unofficial community project, not affiliated with Mojio or any mobile operator.

---

### Česky
Neoficiální integrace pro adaptéry Mojio (např. **T-Mobile Chytré auto**). Instalace přes
Nastavení → Marketplace → Add from link, nastavení přes Nastavení → Zařízení a služby → Přidat
integraci → Mojio. Každé auto je entita `device_tracker` s polohou a daty z OBD v atributech.
