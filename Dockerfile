FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        postgresql-client \
        build-essential \
        python3-dev \
        libpq-dev \
        poppler-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /code

# Install Python dependencies
COPY requirements.txt /code/
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Copy project
COPY . /code/

# Create necessary directories and set permissions
RUN mkdir -p /code/media/uploads \
    && mkdir -p /code/media/extracted \
    && mkdir -p /code/logs \
    && mkdir -p /code/staticfiles \
    && chmod -R 777 /code/media \
    && chmod -R 777 /code/logs \
    && chmod -R 777 /code/staticfiles \
    && chmod +x /code/start.sh

    RUN chmod +x ./start.sh
