# WebSocket Sound Server

A WebSocket-based sound server using the SunVox library. Send JSON events over WebSocket to play sounds, and map network device events to unique audio notifications.

## Quick Start

### 1. Start the Sound Server

```bash
cd sunaudio
python ws_sound_server.py --host 0.0.0.0 --port 8765
```

### 2. Send Sound Events

Using the client:
```bash
python ws_sound_client.py

# Interactive commands:
> note C4
> beep G4 0.5
> device door_open
> stop
```

Or send events directly via WebSocket:
```python
import asyncio
import websockets
import json

async def play_sound():
    async with websockets.connect('ws://localhost:8765') as ws:
        await ws.send(json.dumps({"action": "beep", "note": "C4", "duration": 0.3}))
        response = await ws.recv()
        print(response)

asyncio.run(play_sound())
```

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ Network Devices │───▶│  Event Bridge    │────▶│  Sound Server   │
│  (IoT, HA, etc) │     │  (HTTP/MQTT)     │     │  (WebSocket)    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                          │
                                                          ▼
                                                  ┌─────────────────┐
                                                  │  SunVox Library │
                                                  │  (Audio Output) │
                                                  └─────────────────┘
```

## Components

### ws_sound_server.py
The main WebSocket server that receives events and plays sounds.

### ws_sound_client.py
Interactive and programmatic client for testing and sending events.

### event_bridge.py
HTTP webhook receiver that bridges network events to the sound server.

## Available Actions

### Note Control
```json
{"action": "note", "note": "C4", "velocity": 129}
{"action": "note_off"}
{"action": "beep", "note": "G4", "duration": 0.5}
```

### Playback Control
```json
{"action": "play_file", "file": "assets/test.sunvox"}
{"action": "stop"}
{"action": "volume", "value": 0.8}
```

### Device Events
```json
{"action": "device_event", "event": "door_open", "device": "front_door"}
{"action": "map_event", "event": "my_event", "sound_action": "beep", "sound_params": {"note": "D4", "duration": 0.2}}
{"action": "list_mappings"}
```

## Note Values

Notes can be specified as:
- String: `"C4"`, `"G5"`, `"A3"`, etc. (C0 through B9)
- Integer: MIDI-style note number

### Note Reference
| Octave | C | D | E | F | G | A | B |
|--------|---|---|---|---|---|---|---|
| 4      | C4 | D4 | E4 | F4 | G4 | A4 | B4 |
| 5      | C5 | D5 | E5 | F5 | G5 | A5 | B5 |

## Network Integration

### HTTP Webhooks (via Event Bridge)

Start the event bridge:
```bash
python event_bridge.py --sound-server localhost:8765 --http-port 8080
```

Send events via HTTP:
```bash
curl -X POST http://localhost:8080/event \
     -H "Content-Type: application/json" \
     -d '{"event": "door_open", "device": "front_door"}'
```

### Home Assistant Integration

1. Start the event bridge with HA support:
```bash
python event_bridge.py --home-assistant
```

2. Configure Home Assistant to send webhooks to the bridge.

### Custom Python Integration

```python
from ws_sound_client import SoundClient
import asyncio

async def my_device_handler():
    client = SoundClient('localhost', 8765)
    await client.connect()

    # Map custom events to sounds
    await client.map_event('sensor_triggered', 'beep', {'note': 'E5', 'duration': 0.1})

    # When sensor triggers:
    await client.device_event('sensor_triggered', 'my_sensor')

    await client.disconnect()

asyncio.run(my_device_handler())
```

## Default Sound Mappings

| Event | Sound |
|-------|-------|
| door_open | C4, 0.2s |
| door_close | E4, 0.2s |
| motion_detected | G4, 0.1s |
| light_on | C5, 0.15s |
| light_off | A3, 0.15s |
| button_press | F4, 0.1s |

## Examples

### Doorbell Sound
```json
{"action": "beep", "note": "G5", "duration": 0.4}
```

### Alert Sequence (via multiple calls)
```python
async def alert():
    for note in ['C4', 'E4', 'G4', 'C5']:
        await client.beep(note, 0.1)
        await asyncio.sleep(0.05)
```

### Play a SunVox File
```json
{"action": "play_file", "file": "assets/alarm.sunvox"}
```

## Files

- `ws_sound_server.py` - Main WebSocket server
- `ws_sound_client.py` - Client library and CLI
- `event_bridge.py` - HTTP/network event bridge
- `player.py` - SunVox player wrapper
- `modules.py` - SunVox module definitions
- `notes.py` - Note constants and helpers
