"""
WebSocket Sound Client

A simple client to send sound events to the WebSocket Sound Server.

Usage:
    python ws_sound_client.py [--host localhost] [--port 8765]
    
    # Then type commands like:
    # note C4
    # beep G4 0.5
    # stop
    # device door_open
"""

import asyncio
import json
import argparse
import sys

try:
    import websockets
except ImportError:
    print("Installing websockets...")
    import subprocess
    subprocess.check_call(['pip', 'install', 'websockets'])
    import websockets


class SoundClient:
    """Client for sending sound events to the WebSocket Sound Server."""
    
    def __init__(self, host='localhost', port=8765):
        self.uri = f"ws://{host}:{port}"
        self.websocket = None
    
    async def connect(self):
        """Connect to the server."""
        self.websocket = await websockets.connect(self.uri)
        print(f"Connected to {self.uri}")
        return self
    
    async def disconnect(self):
        """Disconnect from the server."""
        if self.websocket:
            await self.websocket.close()
    
    async def send_event(self, event: dict) -> dict:
        """Send an event and wait for response."""
        await self.websocket.send(json.dumps(event))
        response = await self.websocket.recv()
        return json.loads(response)
    
    # Convenience methods
    async def note(self, note='C4', velocity=129, track=0):
        """Play a note."""
        return await self.send_event({
            'action': 'note',
            'note': note,
            'velocity': velocity,
            'track': track
        })
    
    async def note_off(self, track=0):
        """Stop the current note."""
        return await self.send_event({'action': 'note_off', 'track': track})
    
    async def beep(self, note='C4', duration=0.3, velocity=129):
        """Play a beep (note with auto-off)."""
        return await self.send_event({
            'action': 'beep',
            'note': note,
            'duration': duration,
            'velocity': velocity
        })
    
    async def play_file(self, filename):
        """Play a SunVox file."""
        return await self.send_event({'action': 'play_file', 'file': filename})
    
    async def stop(self):
        """Stop playback."""
        return await self.send_event({'action': 'stop'})
    
    async def volume(self, value):
        """Set volume (0.0 to 1.0)."""
        return await self.send_event({'action': 'volume', 'value': value})
    
    async def device_event(self, event_name, device='unknown'):
        """Send a device event."""
        return await self.send_event({
            'action': 'device_event',
            'event': event_name,
            'device': device
        })
    
    async def map_event(self, event_name, sound_action='beep', sound_params=None):
        """Map a device event to a sound."""
        return await self.send_event({
            'action': 'map_event',
            'event': event_name,
            'sound_action': sound_action,
            'sound_params': sound_params or {'note': 'C4', 'duration': 0.2}
        })
    
    async def list_mappings(self):
        """List all event-to-sound mappings."""
        return await self.send_event({'action': 'list_mappings'})
    
    async def ping(self):
        """Ping the server."""
        return await self.send_event({'action': 'ping'})


def parse_command(line: str) -> dict:
    """Parse a command line into an event dict."""
    parts = line.strip().split()
    if not parts:
        return None
    
    cmd = parts[0].lower()
    
    if cmd == 'note':
        note = parts[1] if len(parts) > 1 else 'C4'
        vel = int(parts[2]) if len(parts) > 2 else 129
        return {'action': 'note', 'note': note, 'velocity': vel}
    
    elif cmd == 'off' or cmd == 'note_off':
        return {'action': 'note_off'}
    
    elif cmd == 'beep':
        note = parts[1] if len(parts) > 1 else 'C4'
        dur = float(parts[2]) if len(parts) > 2 else 0.3
        return {'action': 'beep', 'note': note, 'duration': dur}
    
    elif cmd == 'play':
        filename = parts[1] if len(parts) > 1 else 'assets/test.sunvox'
        return {'action': 'play_file', 'file': filename}
    
    elif cmd == 'load':
        filename = parts[1] if len(parts) > 1 else 'assets/sounds.sunvox'
        return {'action': 'load_file', 'file': filename}
    
    elif cmd == 'modules':
        return {'action': 'list_modules'}
    
    elif cmd == 'modnote' or cmd == 'mn':
        # modnote <module> <note> [duration] [file]
        # e.g., modnote Alpha C4 0.3 assets/sounds.sunvox
        module = parts[1] if len(parts) > 1 else 'Alpha'
        note = parts[2] if len(parts) > 2 else 'C4'
        dur = float(parts[3]) if len(parts) > 3 else 0.3
        result = {'action': 'play_module_note', 'module': module, 'note': note, 'duration': dur}
        if len(parts) > 4:
            result['file'] = parts[4]
        return result
    
    elif cmd == 'stop':
        return {'action': 'stop'}
    
    elif cmd == 'volume' or cmd == 'vol':
        val = float(parts[1]) if len(parts) > 1 else 1.0
        return {'action': 'volume', 'value': val}
    
    elif cmd == 'device':
        event = parts[1] if len(parts) > 1 else 'unknown'
        device = parts[2] if len(parts) > 2 else 'unknown'
        return {'action': 'device_event', 'event': event, 'device': device}
    
    elif cmd == 'map':
        if len(parts) < 3:
            print("Usage: map <event_name> <note> [duration]")
            return None
        event = parts[1]
        note = parts[2]
        dur = float(parts[3]) if len(parts) > 3 else 0.2
        return {
            'action': 'map_event',
            'event': event,
            'sound_action': 'beep',
            'sound_params': {'note': note, 'duration': dur}
        }
    
    elif cmd == 'mappings' or cmd == 'list':
        return {'action': 'list_mappings'}
    
    elif cmd == 'ping':
        return {'action': 'ping'}
    
    elif cmd == 'help':
        print_help()
        return None
    
    else:
        # Try to parse as raw JSON
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            print(f"Unknown command: {cmd}")
            return None


def print_help():
    """Print help information."""
    print("""
Available commands:
  note <note> [velocity]     - Play a note (e.g., 'note C4', 'note G5 100')
  off / note_off             - Stop current note
  beep <note> [duration]     - Play a beep (e.g., 'beep C4 0.5')
  play <file>                - Play a SunVox file
  load <file>                - Load a SunVox file (for module playback)
  modules                    - List modules in loaded file
  modnote <mod> <note> [dur] - Play note on module (e.g., 'modnote Alpha C4 0.3')
  stop                       - Stop playback
  volume <0.0-1.0>           - Set volume
  device <event> [device]    - Trigger a device event
  map <event> <note> [dur]   - Map event to sound
  mappings / list            - List event mappings
  ping                       - Ping server
  help                       - Show this help
  quit / exit                - Exit client

Notes: C0-B9, e.g., C4, D4, E4, F4, G4, A4, B4, C5
You can also type raw JSON: {"action": "note", "note": "C4"}
""")


async def interactive_client(host, port):
    """Run an interactive client session."""
    client = SoundClient(host, port)
    
    try:
        await client.connect()
        print("Type 'help' for commands, 'quit' to exit")
        print()
        
        while True:
            try:
                line = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: input("> ")
                )
            except EOFError:
                break
            
            if line.strip().lower() in ('quit', 'exit', 'q'):
                break
            
            event = parse_command(line)
            if event:
                try:
                    response = await client.send_event(event)
                    print(f"Response: {json.dumps(response, indent=2)}")
                except Exception as e:
                    print(f"Error: {e}")
    
    except ConnectionRefusedError:
        print(f"Could not connect to server at ws://{host}:{port}")
        print("Make sure the server is running: python ws_sound_server.py")
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        await client.disconnect()


async def send_single_event(host, port, event: dict):
    """Send a single event and exit."""
    client = SoundClient(host, port)
    try:
        await client.connect()
        response = await client.send_event(event)
        print(json.dumps(response, indent=2))
    finally:
        await client.disconnect()


def main():
    parser = argparse.ArgumentParser(description='WebSocket Sound Client')
    parser.add_argument('--host', default='localhost', help='Server host (default: localhost)')
    parser.add_argument('--port', type=int, default=8765, help='Server port (default: 8765)')
    parser.add_argument('--event', '-e', help='Send a single JSON event and exit')
    parser.add_argument('--note', '-n', help='Play a single note and exit')
    parser.add_argument('--beep', '-b', help='Play a beep and exit')
    args = parser.parse_args()
    
    if args.event:
        event = json.loads(args.event)
        asyncio.run(send_single_event(args.host, args.port, event))
    elif args.note:
        event = {'action': 'note', 'note': args.note}
        asyncio.run(send_single_event(args.host, args.port, event))
    elif args.beep:
        event = {'action': 'beep', 'note': args.beep, 'duration': 0.3}
        asyncio.run(send_single_event(args.host, args.port, event))
    else:
        asyncio.run(interactive_client(args.host, args.port))


if __name__ == '__main__':
    main()
