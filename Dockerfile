FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set Python to not buffer stdout and stderr to get logs in real time
ENV PYTHONUNBUFFERED=1

# Disable gRPC port for Heroku (since Heroku only exposes one port)
ENV PHOENIX_OTLP_GRPC_ENABLED=false

# Set up environment for Heroku
ENV PHOENIX_HOST=0.0.0.0

# Install Arize Phoenix and OpenAI package
RUN pip install arize-phoenix[pg] openai

# Copy our custom entrypoint script
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Expose the Heroku-assigned port
# Note: Heroku will set PORT environment variable at runtime
EXPOSE $PORT

# Use our custom entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]