# LED Controller

**Reverse-engineered TCP protocol implementation for MagicHome LED bulbs, built from first principles.**

When cheap smart bulbs arrived from Alibaba without documentation or existing libraries, I decoded the proprietary protocol through packet analysis and built a complete full-stack controller. This project demonstrates network protocol reverse engineering, async TCP socket programming, color space mathematics, and production deployment—all without relying on third-party LED libraries.

![LED Controller Interface](https://img.shields.io/badge/status-production%20ready-brightgreen.svg)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)
![React](https://img.shields.io/badge/react-18%2B-blue.svg)
![FastAPI](https://img.shields.io/badge/fastapi-0.100%2B-teal.svg)

## The Challenge: Reverse Engineering a Proprietary Protocol

**Problem**: MagicHome BL606A LED bulbs communicate over TCP port 5577 with an undocumented binary protocol. No Python libraries, no API specs, no documentation.

**Solution**: Packet capture analysis and protocol reverse engineering:

1. **Traffic Analysis**: Captured TCP packets while using the vendor's mobile app
2. **Pattern Recognition**: Identified command structures through hex dump analysis
3. **Protocol Decoding**: Discovered command format: `[header][r][g][b][warm_white][mode][checksum]`
4. **Checksum Algorithm**: Reverse-engineered simple sum-based checksum validation
5. **State Query Protocol**: Decoded bidirectional status query/response mechanism

**Result**: Direct TCP control with <100ms latency, zero cloud dependencies, complete local network ownership.

## Technical Highlights

### Protocol Implementation
- ✅ **Async TCP Sockets** - Native asyncio connection handling with 3-second timeouts
- ✅ **Binary Protocol** - Direct byte-level command construction (`0x31` RGB, `0x71` power)
- ✅ **Bidirectional Communication** - Status queries return 14-byte response packets
- ✅ **Checksum Validation** - Custom sum-based integrity checking

### Color Space Mathematics
- ✅ **HSV ↔ RGB Conversion** - Custom implementation of color space transformations
- ✅ **Hue (0-360°), Saturation (0-100%), Value (0-100%)** - Accurate color representation
- ✅ **Warm White Mode** - Separate LED channel control for 2700K lighting
- ✅ **Hex Color Support** - Full color format conversion pipeline

### System Architecture
- ✅ **FastAPI Backend** - REST API + WebSocket for real-time state broadcasting
- ✅ **React SPA Frontend** - Vite-powered TypeScript app with canvas-based color wheel
- ✅ **State Management** - Centralized bulb state with exponential backoff polling
- ✅ **Docker Deployment** - Multi-stage build with Nginx reverse proxy
- ✅ **Production-Ready** - SSL termination via Traefik, health monitoring, log aggregation

## Quick Start

### Prerequisites

- Python 3.11 or higher
- Bun (recommended) or Node.js 18+
- MagicHome/BL606A LED bulbs on your local network (port 5577)
- Modern web browser with WebSocket support

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/led-controller.git
   cd led-controller
   ```

2. **Configure your bulbs**
   ```bash
   cp config.example.json config.json
   # Edit config.json with your bulb IPs and names
   ```

3. **Install dependencies**
   ```bash
   # Frontend
   bun install

   # Backend
   pip install fastapi uvicorn websockets
   ```

4. **Start the application**
   ```bash
   # Terminal 1 - Backend
   cd backend && python main.py

   # Terminal 2 - Frontend
   bun run dev
   ```

5. **Open your browser**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Docker Deployment (Recommended)

Production deployment with multi-stage builds and Nginx reverse proxy:

```bash
# Clone and configure
git clone https://github.com/yourusername/led-controller.git
cd led-controller
cp config.example.json config.json
# Edit config.json with your bulb IPs

# Build and run
docker-compose up -d
```

**Container Architecture:**
- Frontend: Vite production build served by Nginx
- Backend: FastAPI with uvicorn
- Reverse proxy: Nginx routes `/api/*` → FastAPI, `/ws` → WebSocket
- Process manager: Supervisor manages both services
- Port: Single container exposes port 80 (mapped to 3001 on host)

Access at: http://localhost:3001

## Configuration

Create a `config.json` file based on `config.example.json`:

```json
{
  "bulbs": {
    "living_room": "192.168.1.100",
    "bedroom": "192.168.1.101",
    "kitchen": "192.168.1.102"
  },
  "groups": {
    "all": ["living_room", "bedroom", "kitchen"],
    "downstairs": ["living_room", "kitchen"],
    "upstairs": ["bedroom"]
  },
  "colors": {
    "red": "#FF0000",
    "green": "#00FF00",
    "blue": "#0000FF",
    "warmwhite": "WW"
  }
}
```

### Finding Your Bulb IPs

MagicHome bulbs broadcast on your local network and listen on **TCP port 5577**. Find them using:

```bash
# Option 1: nmap scan
nmap -p 5577 192.168.1.0/24

# Option 2: Router admin panel
# Look for devices named "ESP_XXXXXX" or "LEDnetXXXXXX"

# Option 3: Mobile app
# Use MagicHome app to identify IPs, then switch to this controller
```

## API Documentation

The FastAPI backend provides automatic OpenAPI documentation:

- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/bulbs` | Retrieve all bulb states |
| `GET` | `/bulbs/{name}` | Get single bulb state |
| `POST` | `/bulbs/{name}/command` | Send command to bulb (HSV, power, etc.) |
| `POST` | `/groups/command` | Batch control multiple bulbs |
| `POST` | `/bulbs/sync` | Force refresh all bulb states from hardware |
| `GET` | `/groups` | List available groups |
| `WS` | `/ws` | WebSocket for real-time state updates |

### Command Examples

```bash
# Turn on a bulb
curl -X POST "http://localhost:8000/bulbs/lamp/command" \
     -H "Content-Type: application/json" \
     -d '{"action": "on"}'

# Set HSV color (native color space)
curl -X POST "http://localhost:8000/bulbs/lamp/command" \
     -H "Content-Type: application/json" \
     -d '{"action": "hsv", "h": 240, "s": 100, "v": 80}'

# Set hex color (converted to HSV internally)
curl -X POST "http://localhost:8000/bulbs/lamp/command" \
     -H "Content-Type: application/json" \
     -d '{"action": "color", "hex": "#FF5733"}'

# Warm white mode
curl -X POST "http://localhost:8000/bulbs/lamp/command" \
     -H "Content-Type: application/json" \
     -d '{"action": "warm_white", "brightness": 75}'

# Control multiple bulbs (group)
curl -X POST "http://localhost:8000/groups/command" \
     -H "Content-Type: application/json" \
     -d '{"targets": ["lamp", "dlamp"], "action": "hsv", "h": 180, "s": 100, "v": 90}'

# Force hardware sync (bypasses cache)
curl -X POST "http://localhost:8000/bulbs/sync"
```

### WebSocket Protocol

Connect to `ws://localhost:8000/ws` for real-time updates:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  // Initial state on connect
  if (data.type === "initial_state") {
    console.log(`Received ${data.data.length} bulbs`);
  }

  // Real-time bulb updates
  if (data.type === "bulb_update") {
    console.log(`Bulb ${data.data.name} changed`, data.data);
  }
};
```

## Architecture Deep Dive

### Protocol Layer (`backend/led_controller.py`)

**Direct TCP Socket Implementation** - No external LED libraries

```python
# Example: Power on command
cmd = [0x71, 0x23, 0x0F]  # header, power_on, mode
cmd.append(sum(cmd) & 0xFF)  # checksum
await writer.write(bytes(cmd))

# RGB color command
cmd = [0x31, r, g, b, 0x00, 0x00, 0xF0, 0x0F]
cmd.append(sum(cmd) & 0xFF)
```

**Key Implementation Details:**
- 3-second connection timeout for unreliable IoT devices
- Async context managers for proper socket cleanup
- Status query returns 14-byte response: `[header][power][mode][speed][r][g][b][ww][checksum]`
- Graceful offline detection (mark bulb offline vs. throwing errors)

### State Management (`backend/bulb_manager.py`)

**Centralized state with smart polling:**
- Background polling every 60 seconds (configurable per bulb)
- Exponential backoff for offline bulbs: 60s → 2min → 5min → 10min max
- Skip polling for recently commanded bulbs (<10s) to prevent state conflicts
- Subscriber pattern for WebSocket broadcasting

**State synchronization strategy:**
```python
# Skip recent commands to avoid race conditions
if time_since_command < 10:
    return  # Don't poll, use cached state

# Exponential backoff for offline bulbs
if consecutive_failures > 3:
    poll_interval = 600  # 10 minutes
```

### Color Space (`backend/color_utils.py`)

**Custom HSV ↔ RGB implementation** (not using colorsys):

```python
def hsv_to_rgb(h: float, s: float, v: float) -> tuple[int, int, int]:
    """
    h: 0-360 (degrees)
    s: 0-100 (percentage)
    v: 0-100 (percentage)
    Returns: (r, g, b) as 0-255 integers
    """
    # Sector-based conversion for accurate hue mapping
    sector = int(h / 60) % 6
    # ... mathematical transformation
```

**Why custom implementation?**
- Standard library `colorsys` uses float ranges (0.0-1.0)
- Direct integer RGB output (0-255) for LED commands
- Optimized for real-time color wheel interactions

### API Layer (`backend/main.py`)

**Request debouncing** to handle color wheel dragging:
- 100ms debounce window per bulb+action combination
- Prevents API flooding from rapid UI updates
- Allows 10 color updates/second without overwhelming hardware

**WebSocket management:**
- Broadcast state changes to all connected clients
- Dead connection detection and cleanup
- Ping/pong heartbeat every 30 seconds

### Frontend Architecture

**HSV Color Wheel** (`src/components/color/ColorWheel.tsx`):
- Canvas-based rendering for 60fps color selection
- Polar coordinates: angle = hue, radius = saturation
- Static wheel rendered once, only selection dot redrawn
- Direct HSV state (no RGB intermediate conversion)

**State Flow:**
```
User drags color wheel
  ↓
Update HSV state (React)
  ↓
Debounced API call (200ms)
  ↓
POST /bulbs/{name}/command
  ↓
BulbManager updates state
  ↓
WebSocket broadcast
  ↓
All clients update UI
```

**Production optimizations:**
- Vite code splitting for fast initial load
- Static asset caching (immutable, 1 year)
- HTML not cached (allows instant updates)
- WebSocket reconnection with exponential backoff

## Development

### Project Structure

```
led-controller/
├── backend/
│   ├── led_controller.py      # TCP protocol implementation (114 lines)
│   ├── bulb_manager.py        # State management + polling (368 lines)
│   ├── color_utils.py         # HSV/RGB math (109 lines)
│   └── main.py                # FastAPI routes + WebSocket (462 lines)
├── src/
│   ├── components/
│   │   ├── color/
│   │   │   ├── ColorWheel.tsx       # Canvas-based HSV picker (492 lines)
│   │   │   ├── BrightnessSlider.tsx # Value/brightness control (56 lines)
│   │   │   └── QuickColors.tsx      # Preset color buttons (62 lines)
│   │   └── controls/
│   │       └── BulbControls.tsx     # Main container + WebSocket (532 lines)
│   ├── App.tsx                # React SPA root
│   └── main.tsx               # Vite entry point
├── config.json                # Bulb IPs and group definitions
├── Dockerfile                 # Multi-stage build (97 lines)
├── docker-compose.yml         # Production orchestration
├── vite.config.js             # Vite configuration
└── package.json               # Bun/Node dependencies
```

**Total codebase:** ~2,300 lines (excluding dependencies)
- Backend: ~1,050 lines Python
- Frontend: ~1,140 lines TypeScript/React
- Config/Deploy: ~110 lines

### Development Commands

```bash
# Frontend Development
bun install              # Install dependencies
bun run dev              # Start Vite dev server → http://localhost:5173
bun run build            # Production build → dist/
bun run preview          # Preview production build
bun run lint             # ESLint check

# Backend Development
cd backend
python main.py           # Start FastAPI → http://localhost:8000
python main.py --debug   # Enable debug logging to file + console

# Docker Development
docker-compose up -d          # Build and run container
docker-compose logs -f lights # Follow logs
docker-compose down           # Stop and remove container
```

### Environment Configuration

**Development mode** (`.env.development`):
```env
VITE_API_BASE=http://192.168.2.2:8000
VITE_WS_URL=ws://192.168.2.2:8000/ws
```

**Production mode** (`.env.production`):
```env
VITE_API_BASE=/api
VITE_WS_URL=
```

Vite automatically selects the correct environment. In production, Nginx proxies `/api/*` and `/ws` to the FastAPI backend.

### Testing the Protocol

**Manual TCP test** (without the full app):

```python
import asyncio

async def test_bulb():
    reader, writer = await asyncio.open_connection('192.168.1.100', 5577)

    # Power on
    cmd = [0x71, 0x23, 0x0F, 0xA3]
    writer.write(bytes(cmd))
    await writer.drain()

    # Set red
    cmd = [0x31, 0xFF, 0x00, 0x00, 0x00, 0x00, 0xF0, 0x0F]
    cmd.append(sum(cmd) & 0xFF)
    writer.write(bytes(cmd))
    await writer.drain()

    writer.close()

asyncio.run(test_bulb())
```

## Production Deployment

### Current Deployment
- **Platform**: Docker container on home server
- **Reverse Proxy**: Traefik with SSL (Let's Encrypt)
- **Domain**: lights.chanflix.com (HTTPS)
- **Monitoring**: Supervisor process management, log aggregation
- **Network**: Local network access to bulbs (no port forwarding required)

### Performance Metrics
- **Response time**: <100ms bulb command execution
- **WebSocket latency**: <50ms state update broadcasts
- **Concurrent users**: Tested with 5 simultaneous clients
- **Uptime**: 30+ days (restarted only for updates)

### Security Considerations
- **No authentication** - Designed for private home network only
- **CORS enabled** - Allows cross-origin requests (local network)
- **Direct IP access** - Bulbs communicate on LAN only, no internet access
- **SSL termination** - Traefik handles HTTPS, backend runs HTTP internally

**⚠️ Not recommended for public internet exposure without adding authentication.**

## Skills Demonstrated

This project showcases:

1. **Network Protocol Analysis**
   - Packet capture and reverse engineering
   - Binary protocol implementation
   - TCP socket programming with asyncio

2. **System Design**
   - State management with race condition handling
   - WebSocket real-time communication
   - Request debouncing and optimization

3. **Mathematics & Algorithms**
   - Color space transformations (HSV ↔ RGB)
   - Polar coordinate systems for UI
   - Checksum algorithms

4. **Full-Stack Development**
   - Modern React with TypeScript
   - FastAPI REST + WebSocket APIs
   - Canvas-based interactive graphics

5. **DevOps & Deployment**
   - Multi-stage Docker builds
   - Nginx reverse proxy configuration
   - Process management with Supervisor
   - Production monitoring and logging

## License

MIT License - see [LICENSE](LICENSE) file for details.

---

**Built from first principles when off-the-shelf solutions didn't exist.**
