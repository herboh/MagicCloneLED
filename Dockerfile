FROM node:20-slim

# Install Python
RUN apt-get update && apt-get install -y python3 python3-pip && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Install Node dependencies and build frontend
COPY package.json bun.lockb* ./
RUN npm install -g bun
RUN bun install
COPY . .
RUN bun run build

EXPOSE 3000 8000

# Start both services
CMD ["sh", "-c", "python3 main.py & bun start & wait"]