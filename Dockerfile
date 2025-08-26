# Multi-stage build for efficiency
FROM oven/bun:1-slim AS frontend-build

# Accept build-time config for the API URL so Next.js embeds it
ARG NEXT_PUBLIC_API_URL
ARG NODE_ENV=production
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV NODE_ENV=${NODE_ENV}

WORKDIR /app
COPY package.json bun.lock ./
RUN bun install --frozen-lockfile

# Copy source files needed for build
COPY components/ ./components/
COPY lib/ ./lib/
COPY pages/ ./pages/
COPY public/ ./public/
COPY styles/ ./styles/
COPY next.config.js postcss.config.js tailwind.config.js tsconfig.json next-env.d.ts ./

RUN bun run build

# Final runtime image
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y curl unzip && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir fastapi uvicorn[standard] python-multipart

# Copy Python source files
COPY main.py config.json ./
COPY controllers/ ./controllers/
COPY services/ ./services/
COPY utils/ ./utils/

# Install Node.js/Bun for serving frontend
RUN curl -fsSL https://bun.sh/install | bash
ENV PATH="/root/.bun/bin:$PATH"

# Copy built frontend and install production dependencies
COPY --from=frontend-build /app/.next ./.next
COPY --from=frontend-build /app/public ./public
COPY --from=frontend-build /app/package.json ./
RUN bun install --production

EXPOSE 8000 3000

# Start both services
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port 8000 & bun run start & wait"]
