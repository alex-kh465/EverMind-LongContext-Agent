FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared directory (contains models.py)
COPY shared ./shared

# Copy backend code
COPY backend ./backend

# Copy tools directory
COPY tools ./tools

# Create directories for database and logs
RUN mkdir -p /app/data /app/logs

# Set environment variables
ENV PYTHONPATH=/app:/app/shared:/app/backend
ENV DATABASE_URL=sqlite:///./data/memory.db
ENV ENVIRONMENT=production

# Create startup script
COPY backend/start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Change to backend directory for execution
WORKDIR /app/backend

# Expose port (Render will set PORT env var)
EXPOSE 8000

# Run the application
CMD ["/app/start.sh"]