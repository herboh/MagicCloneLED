# LED Controller

A modern web-based controller for MagicHome LED bulbs with real-time HSV color wheel interface. Built with React SPA (Vite) frontend and FastAPI backend for direct TCP communication with bulbs.

![LED Controller Interface](https://img.shields.io/badge/status-production%20ready-brightgreen.svg)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)
![Bun](https://img.shields.io/badge/bun-latest-orange.svg)
![React](https://img.shields.io/badge/react-18%2B-blue.svg)
![Vite](https://img.shields.io/badge/vite-5%2B-purple.svg)

## Features

- 🎨 **Real-time HSV Color Control** - Interactive color wheel with instant updates
- 💡 **Multiple Bulb Management** - Control individual bulbs or groups simultaneously
- ⚡ **WebSocket Communication** - Real-time state synchronization across all clients
- 🎯 **Modern React SPA** - Lightning-fast Vite build system with Gruvbox theme
- 🐳 **Docker Support** - Production-ready deployment with Docker Compose
- 🔗 **Direct TCP Control** - No cloud dependencies, works entirely on your local network
- 📱 **Responsive Design** - Works seamlessly on desktop, tablet, and mobile
- 🔄 **Smart State Sync** - Automatic background polling with manual refresh capability
- 🎪 **Warm White Mode** - Dedicated warm white brightness control
- 🚀 **Zero Latency** - Sub-100ms command execution to LED bulbs

## Quick Start

### Prerequisites

- Python 3.11 or higher
- Bun (recommended) or Node.js 18+
- MagicHome LED bulbs on your local network
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
   # Frontend (Bun recommended for speed)
   bun install
   
   # Backend
   pip install fastapi uvicorn python-multipart websockets
   ```

4. **Start the application**
   ```bash
   # Terminal 1 - Backend
   python main.py
   
   # Terminal 2 - Frontend
   bun run dev
   ```

5. **Open your browser**
   - Frontend: http://localhost:5173
   - API: http://localhost:5000

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
- Frontend: http://localhost:5173 (Vite dev server)
- API: http://localhost:5000 (FastAPI backend)

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

- **Interactive Docs**: http://localhost:5000/docs
- **OpenAPI Schema**: http://localhost:5000/openapi.json

### Key Endpoints

- `GET /bulbs/status` - Get status of all bulbs
- `POST /bulbs/{name}/command` - Send commands to specific bulb
- `POST /groups/command` - Send commands to bulb groups
- `WebSocket /ws` - Real-time state updates

### Command Examples

```bash
# Turn on a bulb
curl -X POST "http://localhost:5000/bulbs/living_room/command" \
     -H "Content-Type: application/json" \
     -d '{"action": "on"}'

# Set HSV color
curl -X POST "http://localhost:5000/bulbs/living_room/command" \
     -H "Content-Type: application/json" \
     -d '{"action": "hsv", "h": 240, "s": 100, "v": 80}'

# Control group
curl -X POST "http://localhost:5000/groups/command" \
     -H "Content-Type: application/json" \
     -d '{"group": "all", "action": "off"}'

# Force sync all bulb states
curl -X POST "http://localhost:5000/bulbs/sync"
```

## Architecture

### Backend (FastAPI + Python)
- **Modular Design**: Clean separation of LED control, state management, and API routes
- **HSV-First**: Native HSV color system throughout the backend for accurate color representation
- **WebSocket Integration**: Real-time bidirectional communication with frontend
- **Smart State Management**: Centralized BulbManager with background polling and exponential backoff
- **Direct TCP Communication**: No cloud dependencies, communicates directly with bulbs over local network

### Frontend (React SPA + Vite)  
- **Modern React**: Single-page application with TypeScript and Tailwind CSS
- **Lightning Fast**: Vite build system provides instant HMR and optimized production builds
- **Component Architecture**: Modular HSV-focused components with clean separation of concerns
- **Real-time Updates**: WebSocket integration for instant state synchronization
- **Responsive Design**: Gruvbox theme that works perfectly on all device sizes

### Communication Flow
1. **User Interaction**: Color wheel or control changes in React frontend
2. **WebSocket/REST**: Commands sent to FastAPI backend via REST API
3. **State Management**: BulbManager processes commands and updates internal state
4. **LED Communication**: Direct TCP commands sent to MagicHome bulbs
5. **Broadcast Update**: WebSocket broadcasts state changes to all connected clients

## Development

### Project Structure

```
led-controller/
├── src/
│   ├── components/
│   │   ├── color/           # HSV color wheel, brightness slider, quick colors
│   │   └── controls/        # Main bulb control interface
│   ├── App.tsx             # React SPA entry point
│   └── main.tsx            # Vite/React bootstrap
├── controllers/            # LED TCP communication layer
├── services/              # BulbManager state management
├── utils/                 # HSV/RGB color utilities
├── main.py                # FastAPI backend with WebSocket
├── config.json            # Bulb IP addresses and groups
├── vite.config.ts         # Vite build configuration
└── package.json           # Frontend dependencies
```

### Development Commands

```bash
# Frontend Development
bun run dev          # Start Vite dev server (http://localhost:5173)
bun run build        # Build for production
bun run preview      # Preview production build
bun run lint         # Run ESLint

# Backend Development  
python main.py       # Start FastAPI server (http://localhost:5000)
python main.py --reload  # Auto-reload on changes
```

### Production Deployment

The system is production-ready with:
- ✅ Optimized Vite builds with code splitting
- ✅ Static file serving via Nginx
- ✅ WebSocket connection stability
- ✅ Background state synchronization
- ✅ Error handling and reconnection logic
- ✅ Mobile-responsive interface

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
