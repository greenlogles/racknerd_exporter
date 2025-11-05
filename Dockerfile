FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY racknerd_exporter.py .
COPY entrypoint.sh .

# Make entrypoint executable and create non-root user
RUN chmod +x entrypoint.sh && \
    useradd -m -u 1000 exporter && \
    chown -R exporter:exporter /app

USER exporter

# Expose metrics port
EXPOSE 9100

# Use entrypoint script
ENTRYPOINT ["./entrypoint.sh"]