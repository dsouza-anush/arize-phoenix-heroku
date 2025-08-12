FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set Python to not buffer stdout and stderr to get logs in real time
ENV PYTHONUNBUFFERED=1

# Disable gRPC port for Heroku (since Heroku only exposes one port)
ENV PHOENIX_OTLP_GRPC_ENABLED=false

# Set up environment for Heroku
ENV PHOENIX_HOST=0.0.0.0

# Install Arize Phoenix and OpenAI client
RUN pip install arize-phoenix[pg]==11.21.1 openai requests rich

# Copy our custom scripts
COPY entrypoint.sh /app/entrypoint.sh
COPY configure_api.sh /app/configure_api.sh
COPY simple_test.py /app/simple_test.py
COPY phoenix_response_fix.py /app/phoenix_response_fix.py
COPY debug_api.py /app/debug_api.py
RUN chmod +x /app/entrypoint.sh /app/configure_api.sh /app/simple_test.py

# Expose the Heroku-assigned port
# Note: Heroku will set PORT environment variable at runtime
EXPOSE $PORT

# Use our custom entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]