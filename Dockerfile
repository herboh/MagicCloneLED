# Multi-stage build for efficiency
FROM node:18-slim AS frontend-build

WORKDIR /app/frontend
COPY package.json bun.lock ./
RUN npm install -g bun
RUN bun install

COPY . .
RUN bun run build

# Final runtime image
FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies
COPY main.py led_control.py config.json ./
COPY controllers/ ./controllers/
COPY services/ ./services/
COPY utils/ ./utils/

# FastAPI doesn't need many dependencies since most are built-in
RUN pip install fastapi uvicorn python-multipart

# Copy built frontend
COPY --from=frontend-build /app/frontend/.next ./.next
COPY --from=frontend-build /app/frontend/public ./public
COPY --from=frontend-build /app/frontend/node_modules ./node_modules
COPY --from=frontend-build /app/frontend/package.json ./

# Install Node.js for serving the frontend
RUN apt-get update && apt-get install -y nodejs npm && rm -rf /var/lib/apt/lists/*

EXPOSE 8000 3000

# Start both services
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port 8000 & npm start --prefix . -- --port 3000 & wait"]
