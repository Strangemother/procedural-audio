"""
Network Event Bridge for Sound Server

Listens to various network event sources (HTTP webhooks, MQTT, etc.) 
and forwards them to the WebSocket Sound Server.

This allows you to map network device events to sounds:
- Home Assistant events
- IoT device notifications
- Custom webhooks
- MQTT messages

Usage:
    python event_bridge.py [--sound-server localhost:8765] [--http-port 8080]

Then configure your devices to send webhooks to:
    POST http://localhost:8080/event
    Body: {"event": "door_open", "device": "front_door", "data": {...}}
"""

import asyncio
import json
import argparse
from typing import Optional, Callable

try:
    import websockets
except ImportError:
    import subprocess
    subprocess.check_call(['pip', 'install', 'websockets'])
    import websockets

try:
    from aiohttp import web
except ImportError:
    import subprocess
    subprocess.check_call(['pip', 'install', 'aiohttp'])
    from aiohttp import web


class EventBridge:
    """
    Bridge between network events and the sound server.
    
    Receives events from various sources and forwards them to the
    WebSocket Sound Server with appropriate sound mappings.
    """
    
    def __init__(self, sound_server_host='localhost', sound_server_port=8765):
        self.sound_server_uri = f"ws://{sound_server_host}:{sound_server_port}"
        self.websocket = None
        self.connected = False
        self.event_handlers: list[Callable] = []
        
        # Custom event transformers - process raw events before sending
        self.transformers = {}
    
    async def connect(self):
        """Connect to the sound server."""
        try:
            self.websocket = await websockets.connect(self.sound_server_uri)
            self.connected = True
            print(f"Connected to sound server at {self.sound_server_uri}")
            return True
        except Exception as e:
            print(f"Failed to connect to sound server: {e}")
            self.connected = False
            return False
    
    async def reconnect(self):
        """Attempt to reconnect to the sound server."""
        while not self.connected:
            print("Attempting to reconnect to sound server...")
            if await self.connect():
                break
            await asyncio.sleep(5)
    
    async def send_to_sound_server(self, event: dict) -> Optional[dict]:
        """Send an event to the sound server."""
        if not self.connected:
            await self.reconnect()
        
        try:
            await self.websocket.send(json.dumps(event))
            response = await self.websocket.recv()
            return json.loads(response)
        except websockets.exceptions.ConnectionClosed:
            self.connected = False
            print("Connection to sound server lost")
            return None
        except Exception as e:
            print(f"Error sending to sound server: {e}")
            return None
    
    async def process_event(self, event_type: str, device: str = 'unknown', data: dict = None):
        """
        Process an incoming network event.
        
        Args:
            event_type: The type of event (e.g., 'door_open', 'motion_detected')
            device: The device identifier
            data: Additional event data
        """
        # Apply any transformers
        if event_type in self.transformers:
            transformer = self.transformers[event_type]
            event_type, device, data = transformer(event_type, device, data)
        
        # Create the sound event
        sound_event = {
            'action': 'device_event',
            'event': event_type,
            'device': device
        }
        
        if data:
            sound_event['data'] = data
        
        print(f"Processing event: {event_type} from {device}")
        response = await self.send_to_sound_server(sound_event)
        
        if response:
            print(f"Sound server response: {response.get('status')}")
        
        # Notify any registered handlers
        for handler in self.event_handlers:
            await handler(event_type, device, data, response)
        
        return response
    
    def add_transformer(self, event_type: str, transformer: Callable):
        """Add a transformer function for a specific event type."""
        self.transformers[event_type] = transformer
    
    def add_event_handler(self, handler: Callable):
        """Add a handler to be called when events are processed."""
        self.event_handlers.append(handler)
    
    async def map_sound(self, event_name: str, note: str, duration: float = 0.2):
        """Configure a sound mapping on the server."""
        return await self.send_to_sound_server({
            'action': 'map_event',
            'event': event_name,
            'sound_action': 'beep',
            'sound_params': {'note': note, 'duration': duration}
        })


class HTTPEventReceiver:
    """HTTP server for receiving webhook events."""
    
    def __init__(self, bridge: EventBridge, port: int = 8080):
        self.bridge = bridge
        self.port = port
        self.app = web.Application()
        self._setup_routes()
    
    def _setup_routes(self):
        """Set up HTTP routes."""
        self.app.router.add_post('/event', self.handle_event)
        self.app.router.add_post('/webhook', self.handle_webhook)
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_post('/map', self.handle_map)
        self.app.router.add_get('/', self.index)
    
    async def index(self, request):
        """Index page with usage info."""
        html = """
        <html>
        <head><title>Sound Event Bridge</title></head>
        <body>
            <h1>Sound Event Bridge</h1>
            <p>POST events to /event or /webhook</p>
            <h2>Endpoints:</h2>
            <ul>
                <li><b>POST /event</b> - Send a device event<br>
                    Body: {"event": "door_open", "device": "front_door"}</li>
                <li><b>POST /webhook</b> - Generic webhook handler</li>
                <li><b>POST /map</b> - Map event to sound<br>
                    Body: {"event": "custom", "note": "C4", "duration": 0.2}</li>
                <li><b>GET /health</b> - Health check</li>
            </ul>
        </body>
        </html>
        """
        return web.Response(text=html, content_type='text/html')
    
    async def handle_event(self, request):
        """Handle a POST /event request."""
        try:
            data = await request.json()
            event_type = data.get('event', 'unknown')
            device = data.get('device', 'unknown')
            extra_data = data.get('data', {})
            
            response = await self.bridge.process_event(event_type, device, extra_data)
            
            return web.json_response({
                'status': 'ok',
                'sound_response': response
            })
        except json.JSONDecodeError:
            return web.json_response({'status': 'error', 'message': 'Invalid JSON'}, status=400)
        except Exception as e:
            return web.json_response({'status': 'error', 'message': str(e)}, status=500)
    
    async def handle_webhook(self, request):
        """
        Handle generic webhooks.
        Attempts to extract event info from various webhook formats.
        """
        try:
            data = await request.json()
            
            # Try to extract event type from common webhook formats
            event_type = (
                data.get('event') or 
                data.get('event_type') or 
                data.get('type') or
                data.get('action') or
                'webhook'
            )
            
            device = (
                data.get('device') or 
                data.get('device_id') or 
                data.get('entity_id') or
                data.get('source') or
                'webhook'
            )
            
            response = await self.bridge.process_event(event_type, device, data)
            
            return web.json_response({
                'status': 'ok',
                'event_type': event_type,
                'device': device,
                'sound_response': response
            })
        except Exception as e:
            return web.json_response({'status': 'error', 'message': str(e)}, status=500)
    
    async def handle_map(self, request):
        """Handle sound mapping requests."""
        try:
            data = await request.json()
            event = data.get('event')
            note = data.get('note', 'C4')
            duration = float(data.get('duration', 0.2))
            
            if not event:
                return web.json_response({'status': 'error', 'message': 'Event name required'}, status=400)
            
            response = await self.bridge.map_sound(event, note, duration)
            return web.json_response({'status': 'ok', 'response': response})
        except Exception as e:
            return web.json_response({'status': 'error', 'message': str(e)}, status=500)
    
    async def health_check(self, request):
        """Health check endpoint."""
        return web.json_response({
            'status': 'ok',
            'sound_server_connected': self.bridge.connected
        })
    
    async def start(self):
        """Start the HTTP server."""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()
        print(f"HTTP Event Receiver running on http://0.0.0.0:{self.port}")


class HomeAssistantBridge:
    """
    Helper for Home Assistant integration.
    
    Use this to transform Home Assistant events into sound events.
    """
    
    # Common HA event types and their sound mappings
    DEFAULT_MAPPINGS = {
        'state_changed': {
            'light.': ('light_on', 'light_off'),
            'switch.': ('switch_on', 'switch_off'),
            'binary_sensor.door': ('door_open', 'door_close'),
            'binary_sensor.motion': ('motion_detected', 'motion_clear'),
            'binary_sensor.window': ('window_open', 'window_close'),
        }
    }
    
    @staticmethod
    def transform_state_change(event_type: str, device: str, data: dict):
        """Transform a Home Assistant state_changed event."""
        if not data:
            return event_type, device, data
        
        entity_id = data.get('entity_id', '')
        new_state = data.get('new_state', {})
        old_state = data.get('old_state', {})
        
        # Get the state value
        state = new_state.get('state', 'unknown') if isinstance(new_state, dict) else 'unknown'
        
        # Determine sound event based on entity type and state
        for prefix, (on_event, off_event) in HomeAssistantBridge.DEFAULT_MAPPINGS['state_changed'].items():
            if entity_id.startswith(prefix):
                if state in ('on', 'open', 'detected', 'home'):
                    return on_event, entity_id, data
                else:
                    return off_event, entity_id, data
        
        return f"ha_{event_type}", entity_id, data


async def main(args):
    """Main entry point."""
    # Parse sound server address
    sound_host, sound_port = args.sound_server.split(':')
    sound_port = int(sound_port)
    
    # Create the bridge
    bridge = EventBridge(sound_host, sound_port)
    
    # Add Home Assistant transformer if enabled
    if args.home_assistant:
        bridge.add_transformer('state_changed', HomeAssistantBridge.transform_state_change)
    
    # Connect to sound server
    await bridge.connect()
    
    # Set up default sound mappings
    print("Setting up default sound mappings...")
    await bridge.map_sound('door_open', 'C4', 0.2)
    await bridge.map_sound('door_close', 'E4', 0.2)
    await bridge.map_sound('motion_detected', 'G4', 0.1)
    await bridge.map_sound('light_on', 'C5', 0.15)
    await bridge.map_sound('light_off', 'A3', 0.15)
    await bridge.map_sound('switch_on', 'D5', 0.15)
    await bridge.map_sound('switch_off', 'B3', 0.15)
    await bridge.map_sound('button_press', 'F4', 0.1)
    
    # Start HTTP receiver
    http_receiver = HTTPEventReceiver(bridge, args.http_port)
    await http_receiver.start()
    
    print(f"\nEvent Bridge running!")
    print(f"  Sound Server: ws://{sound_host}:{sound_port}")
    print(f"  HTTP Webhook: http://0.0.0.0:{args.http_port}/event")
    print(f"\nSend events with:")
    print(f'  curl -X POST http://localhost:{args.http_port}/event \\')
    print(f'       -H "Content-Type: application/json" \\')
    print(f'       -d \'{{"event": "door_open", "device": "front_door"}}\'')
    
    # Keep running
    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        print("\nShutting down...")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Network Event Bridge for Sound Server')
    parser.add_argument('--sound-server', default='localhost:8765',
                        help='Sound server address (default: localhost:8765)')
    parser.add_argument('--http-port', type=int, default=8080,
                        help='HTTP webhook port (default: 8080)')
    parser.add_argument('--home-assistant', action='store_true',
                        help='Enable Home Assistant event transformations')
    args = parser.parse_args()
    
    asyncio.run(main(args))
