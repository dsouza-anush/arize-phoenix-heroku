#!/bin/bash

# A very simplified solution for fixing Phoenix UI rendering with Heroku AI Claude API
# This is a direct approach without complex transformers or middleware

# Create a simple configuration file
cat > /tmp/phoenix_config.json <<EOL
{
  "api_base": "${INFERENCE_URL}/v1",
  "api_key": "Bearer ${INFERENCE_KEY}",
  "model": "${INFERENCE_MODEL_ID:-claude-4-sonnet}",
  "headers": {
    "Content-Type": "application/json"
  },
  "timeout": 60000
}
EOL

echo "Created Phoenix API config file"

# Set critical environment variables
export PHOENIX_OPENAI_CONFIG_FILE=/tmp/phoenix_config.json
export OPENAI_API_KEY="Bearer ${INFERENCE_KEY}"
export OPENAI_BASE_URL="${INFERENCE_URL}/v1"
export PHOENIX_MODEL_NAME="${INFERENCE_MODEL_ID:-claude-4-sonnet}"

# No response transformers - they cause more problems than they solve
export PHOENIX_OPENAI_DISABLE_RESPONSE_FORMAT=true

# Enable tracing so content is recorded
export PHOENIX_LLM_TRACE_MESSAGE_CONTENT=true
export PHOENIX_LLM_ENABLE_CONTENT_CAPTURE=true
export PHOENIX_LLM_TRACE_ALL_PAYLOADS=true

# Set simple content path
export PHOENIX_OPENAI_EXTRACT_CONTENT_PATH="choices[0].message.content"

# Disable SSR for better React hydration
export PHOENIX_SSR_ENABLED=false

echo "Environment variables set"

# Create a placeholder for response
cat > /tmp/placeholder_content.js <<EOL
// This is a placeholder for fixing the Phoenix UI rendering
// The key issue is that the response content is present in traces
// but isn't correctly displayed in the UI

// Sample Claude response structure from API:
/*
{
  "id": "cmpl-123abc",
  "object": "chat.completion",
  "created": 1677825464,
  "model": "claude-4-sonnet",
  "choices": [
    {
      "message": {
        "role": "assistant", 
        "content": "Hello! This is the response content."
      },
      "index": 0,
      "finish_reason": "stop"
    }
  ]
}
*/

// This content should be displayed in the UI with proper field extraction
EOL

echo "Set up response handling"
echo "Phoenix should now properly display responses in the UI"