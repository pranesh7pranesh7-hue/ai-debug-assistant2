FROM python:3.11-slim

WORKDIR /app

# Install system build dependencies for psycopg2 and static analysis tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r ./backend/requirements.txt

# Copy repository contents (backend + frontend)
COPY . .

# Change directory to backend so app imports resolve
WORKDIR /app/backend

EXPOSE 8000

# Use PORT environment variable set by Render (default 8000)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
