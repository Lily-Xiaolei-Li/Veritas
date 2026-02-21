# Gnosiplexio Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p /app/data/gnosiplexio

# Expose port
EXPOSE 8002

# Set environment variables
ENV PYTHONPATH=/app
ENV GNOSIPLEXIO_DATA_DIR=/app/data/gnosiplexio

# Run the application
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8002"]
