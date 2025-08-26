# Multi-stage build for efficiency
FROM oven/bun:1-slim AS frontend-build

ARG NODE_ENV=production
ENV NODE_ENV=${NODE_ENV}

WORKDIR /app
COPY package.json bun.lock ./
RUN bun install --frozen-lockfile

# Copy source files needed for build
COPY src/ ./src/
COPY public/ ./public/
COPY index.html vite.config.js postcss.config.js tailwind.config.js tsconfig.json ./

RUN bun run build

# Final runtime image with nginx for static files
FROM nginx:alpine AS runtime

# Install Python and dependencies
RUN apk add --no-cache python3 py3-pip python3-dev gcc musl-dev

WORKDIR /app

# Install Python dependencies
RUN pip3 install --no-cache-dir fastapi uvicorn[standard] python-multipart

# Copy Python source files
COPY main.py config.json ./
COPY controllers/ ./controllers/
COPY services/ ./services/
COPY utils/ ./utils/

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
    }\n\
    \n\
    # Proxy API calls to Python backend\n\
    location /api/ {\n\
        proxy_pass http://localhost:8000/api/;\n\
        proxy_set_header Host $host;\n\
        proxy_set_header X-Real-IP $remote_addr;\n\
    }\n\
    \n\
    # Proxy WebSocket to Python backend\n\
    location /ws {\n\
        proxy_pass http://localhost:8000/ws;\n\
        proxy_http_version 1.1;\n\
        proxy_set_header Upgrade $http_upgrade;\n\
        proxy_set_header Connection "upgrade";\n\
        proxy_set_header Host $host;\n\
    }\n\
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80

# Start both nginx and Python backend
CMD ["sh", "-c", "python3 main.py & nginx -g 'daemon off;'"]
