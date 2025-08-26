# Multi-stage build for efficiency
FROM oven/bun:1-slim AS frontend-build

WORKDIR /app

# Copy package files
COPY package.json bun.lock ./
RUN bun install --frozen-lockfile --production=false

# Copy source files needed for Vite build
COPY src/ ./src/
COPY public/ ./public/
COPY index.html vite.config.js postcss.config.js tailwind.config.js tsconfig.json ./

# Build with Vite
RUN bun run build

# Final runtime image
FROM python:3.11-alpine AS runtime

# Install nginx and minimal dependencies
RUN apk add --no-cache nginx supervisor

WORKDIR /app

# Install Python dependencies
RUN pip install --no-cache-dir fastapi uvicorn[standard] websockets

# Copy Python backend
COPY backend/ ./backend/
COPY config.json ./

# Copy built frontend static files
COPY --from=frontend-build /app/dist /usr/share/nginx/html

# Configure nginx
RUN echo 'server {\n\
    listen 80;\n\
    server_name _;\n\
    \n\
    # Serve static files\n\
    location / {\n\
        root /usr/share/nginx/html;\n\
        try_files $uri $uri/ /index.html;\n\
        add_header Cache-Control "public, max-age=31536000" always;\n\
    }\n\
    \n\
    # Proxy API calls to Python backend\n\
    location /api/ {\n\
        proxy_pass http://127.0.0.1:8000/;\n\
        proxy_set_header Host $host;\n\
        proxy_set_header X-Real-IP $remote_addr;\n\
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n\
        proxy_set_header X-Forwarded-Proto $scheme;\n\
    }\n\
    \n\
    # Proxy WebSocket to Python backend\n\
    location /ws {\n\
        proxy_pass http://127.0.0.1:8000/ws;\n\
        proxy_http_version 1.1;\n\
        proxy_set_header Upgrade $http_upgrade;\n\
        proxy_set_header Connection "upgrade";\n\
        proxy_set_header Host $host;\n\
        proxy_set_header X-Real-IP $remote_addr;\n\
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n\
        proxy_set_header X-Forwarded-Proto $scheme;\n\
    }\n\
}' > /etc/nginx/conf.d/default.conf

# Configure supervisor to manage both processes
RUN echo '[supervisord]\n\
nodaemon=true\n\
user=root\n\
\n\
[program:fastapi]\n\
command=python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000\n\
directory=/app\n\
autostart=true\n\
autorestart=true\n\
stderr_logfile=/var/log/fastapi.err.log\n\
stdout_logfile=/var/log/fastapi.out.log\n\
\n\
[program:nginx]\n\
command=nginx -g "daemon off;"\n\
autostart=true\n\
autorestart=true\n\
stderr_logfile=/var/log/nginx.err.log\n\
stdout_logfile=/var/log/nginx.out.log' > /etc/supervisor/conf.d/supervisord.conf

EXPOSE 80

# Create log directory
RUN mkdir -p /var/log

# Start supervisor
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
