# Veritas Core Backend Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app ./app

# Create plugin directory
RUN mkdir -p /opt/veritas/plugins

# Expose port
EXPOSE 8000

# Set environment variables
ENV PYTHONPATH=/app
ENV VERITAS_PLUGIN_DIR=/opt/veritas/plugins

# Run the application
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
