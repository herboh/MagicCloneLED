# LED Controller

A modern web-based controller for MagicHome LED bulbs with real-time HSV color wheel interface. Built with Next.js frontend and FastAPI backend for direct TCP communication with bulbs.

![LED Controller Interface](https://img.shields.io/badge/status-stable-green.svg)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)
![Node.js](https://img.shields.io/badge/node.js-18%2B-green.svg)

## Features

- **Real-time HSV Color Control** - Interactive color wheel with live updates
- **Multiple Bulb Management** - Control individual bulbs or groups
- **WebSocket Communication** - Real-time state synchronization
- **Modern UI** - Clean, responsive interface with Gruvbox theme
- **Docker Support** - Easy deployment with Docker Compose
- **Direct TCP Control** - No cloud dependencies or external apps required

## Quick Start

### Prerequisites

- Python 3.11 or higher
- Node.js 18 or higher (or Bun)
- MagicHome LED bulbs on your local network

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
   # Frontend (choose one)
   npm install  # or
   bun install
   
   # Backend
   pip install fastapi uvicorn python-multipart
   ```

4. **Start the application**
   ```bash
   # Terminal 1 - Backend
   python main.py
   
   # Terminal 2 - Frontend
   npm run dev  # or bun run dev
   ```

5. **Open your browser**
   - Frontend: http://localhost:3000
   - API: http://localhost:8000

## Docker Deployment

The easiest way to run the LED controller is with Docker:

```bash
# Clone and configure
git clone https://github.com/yourusername/led-controller.git
cd led-controller
cp config.example.json config.json
# Edit config.json with your bulb settings

# Run with Docker Compose
docker-compose up -d
```

Access the application at:
- Frontend: http://localhost:3000
- API: http://localhost:8000

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

Use your router's admin panel or network scanning tools to find your MagicHome bulbs. They typically appear as "ESP_" devices and listen on port 5577.

## API Documentation

The FastAPI backend provides a REST API with automatic documentation:

- **Interactive Docs**: http://localhost:8000/docs
- **OpenAPI Schema**: http://localhost:8000/openapi.json

### Key Endpoints

- `GET /bulbs/status` - Get status of all bulbs
- `POST /bulbs/{name}/command` - Send commands to specific bulb
- `POST /groups/command` - Send commands to bulb groups
- `WebSocket /ws` - Real-time state updates

### Command Examples

```bash
# Turn on a bulb
curl -X POST "http://localhost:8000/bulbs/living_room/command" \
     -H "Content-Type: application/json" \
     -d '{"action": "on"}'

# Set HSV color
curl -X POST "http://localhost:8000/bulbs/living_room/command" \
     -H "Content-Type: application/json" \
     -d '{"action": "hsv", "h": 240, "s": 100, "v": 80}'

# Control group
curl -X POST "http://localhost:8000/groups/command" \
     -H "Content-Type: application/json" \
     -d '{"group": "all", "action": "off"}'
```

## Development

### Project Structure

```
led-controller/
├── components/           # React components
│   ├── color/           # Color control components
│   └── controls/        # Main control interfaces
├── controllers/         # Hardware communication
├── services/           # Business logic
├── utils/              # Utility functions
├── pages/              # Next.js pages
├── main.py             # FastAPI backend entry
└── config.json         # Bulb configuration
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
