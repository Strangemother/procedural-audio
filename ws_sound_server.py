"""
WebSocket Sound Server for SunVox

A WebSocket server that receives JSON events and plays sounds using the SunVox library.

Example events:
    {"action": "note", "note": "C4"}
    {"action": "note", "note": 49, "velocity": 100}
    {"action": "note_off"}
    {"action": "play_file", "file": "assets/test.sunvox"}
    {"action": "stop"}
    {"action": "volume", "value": 0.8}
    {"action": "beep", "note": "C4", "duration": 0.3}

Usage:
    python ws_sound_server.py [--host 0.0.0.0] [--port 8765]

Then connect via WebSocket and send JSON events.
"""

import asyncio
import json
import time
import argparse
from pathlib import Path

try:
    import websockets
except ImportError:
    print("Installing websockets...")
    import subprocess
    subprocess.check_call(['pip', 'install', 'websockets'])
    import websockets

from modules import Generator, Module
from notes import Notes
from player import player_factory, Player


class SoundEventHandler:
    """Handles sound events from WebSocket messages."""

    def __init__(self):
        self.player = None
        self.module = None
        self.notes = Notes()
        self._running = False
        self._loaded_file = None  # Track currently loaded file
        self._module_cache = {}   # Cache module IDs by name

        # Map device/event names to sounds
        self.event_sound_map = {
            # Example mappings - customize these for your network events
            'door_open': ('beep', {'note': 'C4', 'duration': 0.2}),
            'door_close': ('beep', {'note': 'E4', 'duration': 0.2}),
            'motion_detected': ('beep', {'note': 'G4', 'duration': 0.1}),
            'light_on': ('beep', {'note': 'C5', 'duration': 0.15}),
            'light_off': ('beep', {'note': 'A3', 'duration': 0.15}),
            'button_press': ('beep', {'note': 'F4', 'duration': 0.1}),
            'alarm': ('play_file', {'file': 'assets/test.sunvox'}),
        }

    def init(self):
        """Initialize the sound system."""
        if self._running:
            return True

        print("Initializing SunVox sound system...")
        self.player = player_factory.spawn_player()

        if self.player is None:
            print("ERROR: Failed to create player")
            return False

        # Create a generator module for playing notes
        self.module = Generator()
        self.player.add_module(self.module, connect_to=self.player.OUTPUT)

        self._running = True
        print("Sound system initialized!")
        return True

    def shutdown(self):
        """Shutdown the sound system."""
        if self.player and self._running:
            print("Shutting down sound system...")
            self.player.stop()
            self.player.close()
            self._running = False

    def parse_note(self, note_value):
        """Parse a note value - can be string like 'C4' or integer."""
        if isinstance(note_value, str):
            # Try to get from Notes class
            note = getattr(self.notes, note_value, None)
            if note is None:
                # Try parsing as octave_note format
                try:
                    letter = note_value[0].upper()
                    octave = int(note_value[1:])
                    note_map = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
                    note = self.notes.octave_note(octave, note_map.get(letter, 0))
                except (IndexError, ValueError):
                    note = self.notes.C4  # Default
            return note
        return int(note_value)

    @property
    def action_handlers(self) -> dict:
        """Map of action names to handler functions."""
        return {
            'note': self._handle_note,
            'note_off': self._handle_note_off,
            'beep': self._handle_beep,
            'play_file': self._handle_play_file,
            'play_module_note': self._handle_play_module_note,
            'load_file': self._handle_load_file,
            'list_modules': self._handle_list_modules,
            'stop': self._handle_stop,
            'volume': self._handle_volume,
            'device_event': self._handle_device_event,
            'map_event': self._handle_map_event,
            'list_mappings': lambda data: {'status': 'ok', 'mappings': self.event_sound_map},
            'ping': lambda data: {'status': 'ok', 'message': 'pong'},
            # Instrument building
            'create_module': self._handle_create_module,
            'remove_module': self._handle_remove_module,
            'connect_modules': self._handle_connect_modules,
            'load_module_file': self._handle_load_module_file,
            'get_module_ctls': self._handle_get_module_ctls,
            'set_module_ctl': self._handle_set_module_ctl,
            'list_module_types': self._handle_list_module_types,
            'build_piano': self._handle_build_piano,
        }

    async def handle_event(self, event_data: dict) -> dict:
        """
        Handle a sound event.

        Args:
            event_data: Dictionary with event parameters

        Returns:
            Response dictionary with status
        """
        if not self._running:
            return {'status': 'error', 'message': 'Sound system not initialized'}

        action = event_data.get('action', '').lower()

        try:
            handler = self.action_handlers.get(action)
            if handler:
                result = handler(event_data)
                # Handle both async and sync handlers
                if asyncio.iscoroutine(result):
                    return await result
                return result
            else:
                return {'status': 'error', 'message': f'Unknown action: {action}'}

        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    async def _handle_note(self, data: dict) -> dict:
        """Play a note."""
        note = self.parse_note(data.get('note', 'C4'))
        velocity = data.get('velocity', 129)
        track = data.get('track', 0)

        self.module.sv_send_event(track, note, velocity)
        return {'status': 'ok', 'action': 'note', 'note': note}

    async def _handle_note_off(self, data: dict) -> dict:
        """Stop the current note."""
        track = data.get('track', 0)
        self.module.sv_send_event(track, self.notes.NOTE_OFF)
        return {'status': 'ok', 'action': 'note_off'}

    async def _handle_beep(self, data: dict) -> dict:
        """Play a note for a duration then stop."""
        note = self.parse_note(data.get('note', 'C4'))
        duration = data.get('duration', 0.3)
        velocity = data.get('velocity', 129)
        track = data.get('track', 0)

        self.module.sv_send_event(track, note, velocity)
        await asyncio.sleep(duration)
        self.module.sv_send_event(track, self.notes.NOTE_OFF)

        return {'status': 'ok', 'action': 'beep', 'note': note, 'duration': duration}

    async def _handle_play_file(self, data: dict) -> dict:
        """Play a SunVox file."""
        filename = data.get('file', 'assets/test.sunvox')

        if not Path(filename).exists():
            return {'status': 'error', 'message': f'File not found: {filename}'}

        self.player.play_file(filename)
        return {'status': 'ok', 'action': 'play_file', 'file': filename}

    async def _handle_stop(self, data: dict) -> dict:
        """Stop playback."""
        self.player.stop()
        return {'status': 'ok', 'action': 'stop'}

    async def _handle_load_file(self, data: dict) -> dict:
        """Load a SunVox file without playing it."""
        filename = data.get('file', 'assets/sounds.sunvox')

        if not Path(filename).exists():
            return {'status': 'error', 'message': f'File not found: {filename}'}

        self.player.load_file(self.player.slotnr, filename)
        self._loaded_file = filename
        self._module_cache = {}  # Clear cache when loading new file

        return {'status': 'ok', 'action': 'load_file', 'file': filename}

    async def _handle_list_modules(self, data: dict) -> dict:
        """List all modules currently in the slot (loaded or built at runtime)."""
        modules = []
        num_modules = self.player.sv_get_number_of_modules()

        for i in range(num_modules):
            flags = self.player.sv_get_module_flags(i)
            # Check if module exists (SV_MODULE_FLAG_EXISTS = 1)
            if flags & 1:
                name = self.player.sv_get_module_name(i)
                if name:
                    name = name.decode('utf-8') if isinstance(name, bytes) else name
                    modules.append({'id': i, 'name': name})

        return {'status': 'ok', 'action': 'list_modules', 'modules': modules}

    def _find_module_by_name(self, module_name: str) -> int:
        """Find a module ID by name, with caching."""
        if module_name in self._module_cache:
            return self._module_cache[module_name]

        module_id = self.player.svlib.sv_find_module(
            self.player.slotnr,
            module_name.encode('utf-8')
        )

        if module_id >= 0:
            self._module_cache[module_name] = module_id

        return module_id

    async def _handle_play_module_note(self, data: dict) -> dict:
        """
        Play a note on a named module from a loaded SunVox file.

        Example:
            {"action": "play_module_note", "file": "assets/sounds.sunvox",
             "module": "Alpha", "note": "C4", "duration": 0.3}
        """
        filename = data.get('file')
        module_name = data.get('module', 'Alpha')
        note = self.parse_note(data.get('note', 'C4'))
        velocity = data.get('velocity', 129)
        duration = data.get('duration', 0.3)
        track = data.get('track', 0)

        # Load file if specified and different from current
        if filename and filename != self._loaded_file:
            if not Path(filename).exists():
                return {'status': 'error', 'message': f'File not found: {filename}'}
            self.player.load_file(self.player.slotnr, filename)
            self._loaded_file = filename
            self._module_cache = {}

        # Find module by name (works for both loaded files and runtime-built modules)
        module_id = self._find_module_by_name(module_name)

        if module_id < 0:
            return {'status': 'error', 'message': f'Module not found: {module_name}'}

        # Play note on that module
        self.player.sv_send_event(track, note, velocity, module_id)

        if duration > 0:
            await asyncio.sleep(duration)
            self.player.sv_send_event(track, self.notes.NOTE_OFF, 129, module_id)

        return {
            'status': 'ok',
            'action': 'play_module_note',
            'file': self._loaded_file,
            'module': module_name,
            'module_id': module_id,
            'note': note,
            'duration': duration
        }

    async def _handle_volume(self, data: dict) -> dict:
        """Set volume (0.0 to 1.0)."""
        value = float(data.get('value', 1.0))
        value = max(0.0, min(1.0, value))
        self.player.volume(value)
        return {'status': 'ok', 'action': 'volume', 'value': value}

    # ------------------------------------------------------------
    # Instrument-building actions
    # ------------------------------------------------------------

    # Friendly aliases for the main built-in module types.
    MODULE_TYPES = [
        'Analog Generator', 'DrumSynth', 'FM', 'FMX', 'Generator', 'Input',
        'Kicker', 'Vorbis player', 'Sampler', 'SpectraVoice',
        'Amplifier', 'Compressor', 'DC Blocker', 'Delay', 'Distortion',
        'Echo', 'EQ', 'Filter', 'Filter Pro', 'Flanger', 'LFO', 'Loop',
        'Modulator', 'Pitch shifter', 'Reverb', 'Vocal filter', 'WaveShaper',
        'MultiCtl', 'MultiSynth', 'Pitch Detector', 'Sound2Ctl', 'Velocity2Ctl',
        'Glide',
    ]

    async def _handle_create_module(self, data: dict) -> dict:
        """Create a new module in the current project.

        Example:
            {"action": "create_module", "type": "FMX", "name": "Piano",
             "x": 512, "y": 512, "connect_to_output": true}
        """
        mtype = data.get('type', 'Generator')
        name = data.get('name', mtype)
        x = int(data.get('x', 512))
        y = int(data.get('y', 512))
        z = int(data.get('z', 0))
        connect_to_output = bool(data.get('connect_to_output', False))

        mod_id = self.player.sv_new_module(self.player.slotnr, mtype, name, x, y, z)
        if mod_id < 0:
            return {'status': 'error', 'message': f'sv_new_module failed: {mod_id}'}

        if connect_to_output:
            self.player.sv_connect_module(mod_id, self.player.OUTPUT)

        return {'status': 'ok', 'action': 'create_module',
                'id': mod_id, 'name': name, 'type': mtype}

    async def _handle_remove_module(self, data: dict) -> dict:
        target = data.get('module')
        mod_id = self._resolve_module(target)
        if mod_id is None:
            return {'status': 'error', 'message': f'module not found: {target}'}
        rc = self.player.sv_remove_module(mod_id)
        return {'status': 'ok' if rc == 0 else 'error',
                'action': 'remove_module', 'id': mod_id, 'code': rc}

    async def _handle_connect_modules(self, data: dict) -> dict:
        """Connect source -> destination.

        {"action": "connect_modules", "source": "Piano", "destination": "Reverb"}
        destination=0 or "OUT" to connect to output.
        """
        src = self._resolve_module(data.get('source'))
        dst_raw = data.get('destination', 0)
        if isinstance(dst_raw, str) and dst_raw.upper() == 'OUT':
            dst = 0
        else:
            dst = self._resolve_module(dst_raw)
            if dst is None:
                dst = int(dst_raw) if isinstance(dst_raw, int) else None

        if src is None or dst is None:
            return {'status': 'error', 'message': 'source/destination not found'}
        rc = self.player.sv_connect_module(src, dst)
        return {'status': 'ok' if rc == 0 else 'error',
                'action': 'connect_modules', 'source': src, 'destination': dst, 'code': rc}

    async def _handle_load_module_file(self, data: dict) -> dict:
        """Load a .sunsynth / .xi / .wav file as a new module.

        {"action": "load_module_file", "file": "path/to/piano.sunsynth",
         "connect_to_output": true}
        """
        filename = data.get('file')
        if not filename or not Path(filename).exists():
            return {'status': 'error', 'message': f'file not found: {filename}'}
        x = int(data.get('x', 512))
        y = int(data.get('y', 512))
        mod_id = self.player.sv_load_module_file(filename, x, y, 0)
        if mod_id < 0:
            return {'status': 'error', 'message': f'sv_load_module failed: {mod_id}'}
        if data.get('connect_to_output', True):
            self.player.sv_connect_module(mod_id, self.player.OUTPUT)
        # Refresh module cache
        self._module_cache = {}
        return {'status': 'ok', 'action': 'load_module_file',
                'id': mod_id, 'file': filename}

    def _resolve_module(self, ref) -> int:
        """Resolve a module reference (int id, str name, or dict) to an id."""
        if ref is None:
            return None
        if isinstance(ref, int):
            return ref
        if isinstance(ref, str):
            mid = self._find_module_by_name(ref)
            return mid if mid >= 0 else None
        return None

    async def _handle_get_module_ctls(self, data: dict) -> dict:
        """Return the list of controllers for a module with current values."""
        target = data.get('module')
        mod_id = self._resolve_module(target)
        if mod_id is None:
            return {'status': 'error', 'message': f'module not found: {target}'}

        n = self.player.sv_get_number_of_module_ctls(mod_id)
        ctls = []
        for i in range(1, n + 1):
            name = self.player.sv_get_module_ctl_name(mod_id, i - 1)
            raw = self.player.sv_get_module_ctl_value(mod_id, i - 1, 0)
            scaled = self.player.sv_get_module_ctl_value(mod_id, i - 1, 1)
            ctls.append({'index': i, 'name': name, 'raw': raw, 'scaled': scaled})
        return {'status': 'ok', 'action': 'get_module_ctls',
                'module': target, 'id': mod_id, 'ctls': ctls}

    async def _handle_set_module_ctl(self, data: dict) -> dict:
        """Set a controller on a module.

        {"action": "set_module_ctl", "module": "Piano", "ctl": 3, "value": 16384}
        """
        target = data.get('module')
        mod_id = self._resolve_module(target)
        if mod_id is None:
            return {'status': 'error', 'message': f'module not found: {target}'}
        ctl = int(data.get('ctl', 1))
        value = int(data.get('value', 0))
        track = int(data.get('track', 0))
        self.player.set_module_ctl(mod_id, ctl, value, track=track)
        return {'status': 'ok', 'action': 'set_module_ctl',
                'module': target, 'ctl': ctl, 'value': value}

    async def _handle_list_module_types(self, data: dict) -> dict:
        return {'status': 'ok', 'action': 'list_module_types',
                'types': self.MODULE_TYPES}

    async def _handle_build_piano(self, data: dict) -> dict:
        """Build a gentle piano-like instrument chain.

        Chain:  FMX (Piano) -> Filter Pro -> Echo -> Reverb -> OUT

        The FMX synth's default patch is a bell/e-piano tone; we add a gentle
        low-pass filter, a short stereo echo for sparkle, and a hall reverb
        for air. Returns the module IDs so the UI can route notes / edit ctls.
        """
        name = data.get('name', 'Piano')
        reverb_wet = int(data.get('reverb_wet', 18000))   # 0..32768
        echo_wet = int(data.get('echo_wet', 9000))

        # Remove any prior instance so the action is idempotent
        for suffix in ('', ' Filter', ' Echo', ' Reverb'):
            existing = self._find_module_by_name(name + suffix)
            if existing >= 0:
                try:
                    self.player.sv_remove_module(existing)
                except Exception:
                    pass
        self._module_cache = {}

        created = []   # track created ids so we can clean up on failure

        def mk(mtype_candidates, mname, x, y):
            # Accept a list of fallback type names; use the first that succeeds.
            if isinstance(mtype_candidates, str):
                mtype_candidates = [mtype_candidates]
            last_err = None
            for mtype in mtype_candidates:
                mid = self.player.sv_new_module(
                    self.player.slotnr, mtype, mname, x, y, 0)
                if mid >= 0:
                    created.append(mid)
                    return mid, mtype
                last_err = mid
            raise RuntimeError(
                f'could not create {mname}: tried {mtype_candidates}, '
                f'last error code {last_err}')

        try:
            piano, piano_type = mk(['FMX', 'FM'], name, 400, 500)
            flt, flt_type = mk(['Filter Pro', 'Filter'], f'{name} Filter', 500, 500)
            echo, echo_type = mk(['Echo'], f'{name} Echo', 600, 500)
            rev, rev_type = mk(['Reverb'], f'{name} Reverb', 700, 500)
        except Exception as e:
            # Roll back any partial modules so we don't litter the project.
            for mid in created:
                try: self.player.sv_remove_module(mid)
                except Exception: pass
            return {'status': 'error', 'message': str(e)}

        # Connect chain: piano -> filter -> echo -> reverb -> OUT
        self.player.sv_connect_module(piano, flt)
        self.player.sv_connect_module(flt, echo)
        self.player.sv_connect_module(echo, rev)
        self.player.sv_connect_module(rev, self.player.OUTPUT)

        # Gentle defaults via controller events.
        # NOTE: these indices assume SunVox 2.x built-in modules. If a
        # controller doesn't exist, the call is silently ignored by the lib.
        try:
            # Reverb: ctl 1 = "Wet", ctl 2 = "Dry"
            self.player.set_module_ctl(rev, 1, reverb_wet)
            # Echo: ctl 1 = "Dry", ctl 2 = "Wet", ctl 3 = "Delay"
            self.player.set_module_ctl(echo, 2, echo_wet)
            # Filter Pro: ctl 3 = "Cutoff" (0..32768)
            self.player.set_module_ctl(flt, 3, 22000)
        except Exception:
            pass

        # Clear cached lookups so the new "Piano" is findable by name.
        self._module_cache = {}

        return {
            'status': 'ok',
            'action': 'build_piano',
            'modules': {
                'piano': {'id': piano, 'name': name, 'type': piano_type},
                'filter': {'id': flt, 'name': f'{name} Filter', 'type': flt_type},
                'echo': {'id': echo, 'name': f'{name} Echo', 'type': echo_type},
                'reverb': {'id': rev, 'name': f'{name} Reverb', 'type': rev_type},
            },
            'hint': f'Use play_module_note with "module": "{name}" to play notes through it.',
        }

    async def _handle_device_event(self, data: dict) -> dict:
        """
        Handle a device event from your network.
        Maps device events to sounds based on event_sound_map.

        Example:
            {"action": "device_event", "event": "door_open", "device": "front_door"}
        """
        event_name = data.get('event', '')
        device = data.get('device', 'unknown')

        if event_name in self.event_sound_map:
            sound_action, sound_params = self.event_sound_map[event_name]
            sound_event = {'action': sound_action, **sound_params}
            result = await self.handle_event(sound_event)
            result['device'] = device
            result['original_event'] = event_name
            return result

        return {
            'status': 'ok',
            'message': f'No sound mapped for event: {event_name}',
            'device': device
        }

    async def _handle_map_event(self, data: dict) -> dict:
        """
        Add or update a device event to sound mapping.

        Example:
            {"action": "map_event", "event": "custom_event",
             "sound_action": "beep", "sound_params": {"note": "D4", "duration": 0.2}}
        """
        event_name = data.get('event')
        sound_action = data.get('sound_action', 'beep')
        sound_params = data.get('sound_params', {'note': 'C4', 'duration': 0.2})

        if not event_name:
            return {'status': 'error', 'message': 'Event name required'}

        self.event_sound_map[event_name] = (sound_action, sound_params)
        return {
            'status': 'ok',
            'action': 'map_event',
            'event': event_name,
            'mapped_to': (sound_action, sound_params)
        }


class WebSocketSoundServer:
    """WebSocket server for receiving sound events."""

    def __init__(self, host='0.0.0.0', port=8765):
        self.host = host
        self.port = port
        self.handler = SoundEventHandler()
        self.clients = set()

    async def handle_client(self, websocket):
        """Handle a WebSocket client connection."""
        client_addr = websocket.remote_address
        print(f"Client connected: {client_addr}")
        self.clients.add(websocket)

        try:
            async for message in websocket:
                try:
                    event_data = json.loads(message)
                    print(f"Received: {event_data}")

                    response = await self.handler.handle_event(event_data)
                    await websocket.send(json.dumps(response))

                except json.JSONDecodeError:
                    error_response = {'status': 'error', 'message': 'Invalid JSON'}
                    await websocket.send(json.dumps(error_response))

        except websockets.exceptions.ConnectionClosed:
            print(f"Client disconnected: {client_addr}")
        finally:
            self.clients.discard(websocket)

    async def broadcast(self, message: dict):
        """Broadcast a message to all connected clients."""
        if self.clients:
            msg = json.dumps(message)
            await asyncio.gather(*[client.send(msg) for client in self.clients])

    async def start(self):
        """Start the WebSocket server."""
        if not self.handler.init():
            print("Failed to initialize sound system!")
            return

        print(f"Starting WebSocket Sound Server on ws://{self.host}:{self.port}")
        print("\nAvailable actions:")
        print('  {"action": "note", "note": "C4"}')
        print('  {"action": "note", "note": 49, "velocity": 100}')
        print('  {"action": "note_off"}')
        print('  {"action": "beep", "note": "C4", "duration": 0.3}')
        print('  {"action": "play_file", "file": "assets/jetsons.sunvox"}')
        print('  {"action": "stop"}')
        print('  {"action": "volume", "value": 0.8}')
        print('  {"action": "device_event", "event": "door_open", "device": "front"}')
        print('  {"action": "map_event", "event": "my_event", "sound_action": "beep", "sound_params": {"note": "D4"}}')
        print('  {"action": "list_mappings"}')
        print('  {"action": "ping"}')
        print("\nModule playback (for custom .sunvox files):")
        print('  {"action": "load_file", "file": "assets/sounds.sunvox"}')
        print('  {"action": "list_modules"}')
        print('  {"action": "play_module_note", "file": "assets/sounds.sunvox", "module": "Alpha", "note": "C4", "duration": 0.3}')
        print("\nWaiting for connections...")

        try:
            async with websockets.serve(self.handle_client, self.host, self.port):
                await asyncio.Future()  # Run forever
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            self.handler.shutdown()


def main():
    parser = argparse.ArgumentParser(description='WebSocket Sound Server for SunVox')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8765, help='Port to listen on (default: 8765)')
    args = parser.parse_args()

    server = WebSocketSoundServer(host=args.host, port=args.port)
    asyncio.run(server.start())


if __name__ == '__main__':
    main()
