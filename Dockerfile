# Multi-stage build for efficiency
FROM oven/bun:1-slim AS frontend-build

WORKDIR /app

# Copy package files
COPY package.json bun.lock ./
RUN bun install --frozen-lockfile

# Copy source files needed for Vite build
COPY src/ ./src/
COPY public/ ./public/
COPY index.html vite.config.js postcss.config.js tailwind.config.js tsconfig.json ./

# Build with Vite
RUN bun run build

# Final runtime image
FROM python:3.11-alpine AS runtime

# Install nginx and minimal dependencies
RUN apk add --no-cache nginx

WORKDIR /app

# Install Python dependencies
RUN pip install --no-cache-dir fastapi uvicorn[standard] websockets

# Copy Python backend and startup script
COPY backend/ ./backend/
COPY config.json ./
COPY start.sh ./
RUN chmod +x /app/start.sh

# Copy built frontend static files
COPY --from=frontend-build /app/dist /usr/share/nginx/html

# Configure nginx with separate file
COPY nginx.conf /etc/nginx/nginx.conf

# Create log directory and set permissions
RUN mkdir -p /var/log

EXPOSE 80

# Start both services with startup script
CMD ["/app/start.sh"]
