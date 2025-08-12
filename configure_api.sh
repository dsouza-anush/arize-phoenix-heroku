#!/bin/bash

# This script configures Phoenix to properly integrate with the Heroku AI addon

# Function to log message
log_message() {
  echo "[CONFIG] $1"
}

# Check if Heroku AI addon environment variables are available
if [ -n "$INFERENCE_URL" ] && [ -n "$INFERENCE_KEY" ]; then
  log_message "Heroku AI addon detected, configuring integration"
  
  # Export necessary environment variables for Phoenix
  export OPENAI_API_KEY="Bearer ${INFERENCE_KEY}"
  export OPENAI_BASE_URL="${INFERENCE_URL}/v1"
  export PHOENIX_MODEL_NAME="${INFERENCE_MODEL_ID:-claude-4-sonnet}"
  
  log_message "Configured for model: $PHOENIX_MODEL_NAME"
else
  log_message "Heroku AI addon not detected or configuration incomplete"
fi

# Fix for common hydration issues
export PHOENIX_SSR_ENABLED=false

log_message "Configuration completed"