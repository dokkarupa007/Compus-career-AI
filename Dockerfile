FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Initialize and seed database
RUN python database/init_db.py

EXPOSE 5000

ENV FLASK_ENV=production
ENV SECRET_KEY=careercompass-docker-secret-key-2026

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
