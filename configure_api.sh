#!/bin/bash

# This script configures Phoenix to properly integrate with the Heroku AI addon

# Initialize variables
PHOENIX_API_CONFIG=/tmp/phoenix_api_config.json

# Function to log message
log_message() {
  echo "[CONFIG] $1"
}

# Check if Heroku AI addon environment variables are available
if [ -n "$INFERENCE_URL" ] && [ -n "$INFERENCE_KEY" ]; then
  log_message "Heroku AI addon detected, configuring integration"
  
  # Create temporary API configuration file
  cat > $PHOENIX_API_CONFIG <<EOL
{
  "api_base": "${INFERENCE_URL}/v1",
  "api_key": "Bearer ${INFERENCE_KEY}",
  "model": "${INFERENCE_MODEL_ID:-claude-4-sonnet}",
  "headers": {
    "Content-Type": "application/json"
  },
  "timeout": 60000,
  "transformers": {
    "response": "if (response && response.choices && response.choices.length > 0) { const choice = response.choices[0]; if (choice.message && choice.message.content) { choice.text = choice.message.content; } else if (choice.text && !choice.message) { choice.message = { role: 'assistant', content: choice.text }; } return response; } else { return response; }",
    "streaming": "if (chunk && chunk.choices && chunk.choices.length > 0) { const choice = chunk.choices[0]; if (choice.delta && choice.delta.content) { choice.text = choice.delta.content; } return chunk; } else { return chunk; }"
  }
}
EOL
  
  # Export Phoenix configuration
  export PHOENIX_OPENAI_CONFIG_FILE=$PHOENIX_API_CONFIG
  log_message "API configuration file created at $PHOENIX_OPENAI_CONFIG_FILE"
  
  # Additional client configuration
  export OPENAI_API_KEY="Bearer ${INFERENCE_KEY}"
  export OPENAI_BASE_URL="${INFERENCE_URL}/v1"
  export PHOENIX_MODEL_NAME="${INFERENCE_MODEL_ID:-claude-4-sonnet}"
  
  # Enable content capture and tracing
  export PHOENIX_LLM_TRACE_MESSAGE_CONTENT=true
  export PHOENIX_LLM_ENABLE_CONTENT_CAPTURE=true
  export PHOENIX_OPENAI_EXTRACT_CONTENT_PATH="choices[0].message.content"
  export PHOENIX_LLM_TRACE_ALL_PAYLOADS=true
  export PHOENIX_TRACE_DEBUG=true
  
  log_message "Configured for model: $PHOENIX_MODEL_NAME"
  
  # Install response fix script to ensure proper rendering
  if [ -f "/app/phoenix_response_fix.py" ]; then
    log_message "Applying Phoenix response fix"
    python /app/phoenix_response_fix.py &
    log_message "Response fix applied"
  fi
else
  log_message "Heroku AI addon not detected or configuration incomplete"
fi

# Fix for common hydration issues
export PHOENIX_SSR_ENABLED=false

log_message "Configuration completed"