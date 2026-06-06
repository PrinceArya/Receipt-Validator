# Use official lightweight Python image.
FROM python:3.11-slim

# Install system dependencies needed for Playwright (headless browser setup)
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency definition
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (chromium) and system dependencies
RUN playwright install --with-deps chromium

# Copy application files
COPY . .

# Expose port 8000
EXPOSE 8000

# Start command
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
