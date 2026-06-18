# Use official light Python runtime
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Install system dependencies (needed for compiling certain packages if any)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Set environment defaults
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV DATA_RETENTION_HOURS=24
ENV SESSION_COOKIE_SECURE=True
ENV PORT=5000

# Expose port
EXPOSE 5000

# Run with Gunicorn production server
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
