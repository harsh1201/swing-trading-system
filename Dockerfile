FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Environment variables (should be set via Fly secrets)
# DISCORD_WEBHOOK_URL
# DISCORD_LONG_WEBHOOK_URL
# DISCORD_SHORT_WEBHOOK_URL

# Default command (Safety catch: do nothing. Scheduled machines override this)
CMD ["echo", "Swing Trading System deployed. Triggered via Fly scheduled machines."]
