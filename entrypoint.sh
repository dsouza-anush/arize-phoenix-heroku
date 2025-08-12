#!/bin/bash
set -e

# Parse DATABASE_URL from Heroku environment if exists
if [ -n "$DATABASE_URL" ]; then
  echo "Configuring Phoenix to use Heroku Postgres"
  
  # Extract database connection parameters from DATABASE_URL
  # Format: postgres://username:password@host:port/database_name
  regex="postgres://([^:]+):([^@]+)@([^:]+):([^/]+)/(.+)"
  
  if [[ $DATABASE_URL =~ $regex ]]; then
    DB_USER="${BASH_REMATCH[1]}"
    DB_PASSWORD="${BASH_REMATCH[2]}"
    DB_HOST="${BASH_REMATCH[3]}"
    DB_PORT="${BASH_REMATCH[4]}"
    DB_NAME="${BASH_REMATCH[5]}"
    
    # Configure Phoenix to use PostgreSQL
    export PHOENIX_SQL_DATABASE_URL="postgresql+asyncpg://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"
    echo "Database connection configured"
  else
    echo "Warning: DATABASE_URL format not recognized. Using default SQLite database."
  fi
else
  echo "No DATABASE_URL found. Using default SQLite database."
fi

# Use the PORT environment variable provided by Heroku
if [ -n "$PORT" ]; then
  echo "Setting Phoenix port to $PORT"
  export PHOENIX_PORT="$PORT"
else
  echo "No PORT environment variable found. Using default port 6006."
  export PHOENIX_PORT=6006
fi

# Set working directory to ephemeral storage
export PHOENIX_WORKING_DIR="/tmp/phoenix"
mkdir -p "$PHOENIX_WORKING_DIR"

# Configure authentication if env vars are set
if [ -n "$PHOENIX_SECRET" ]; then
  echo "Authentication enabled"
  export PHOENIX_ENABLE_AUTH=true
else
  echo "Authentication disabled"
  export PHOENIX_ENABLE_AUTH=false
fi

# Disable gRPC to work with Heroku's single port model
export PHOENIX_OTLP_GRPC_ENABLED=false

# Source the configuration script for Heroku AI addon
source /app/configure_api.sh

# Run response fix script
echo "Checking for response fix script..."
if [ -f "/app/phoenix_response_fix.py" ]; then
  echo "Running Phoenix response fix script"
  python /app/phoenix_response_fix.py &
fi

# Run simple API test
echo "Testing API connection..."
python /app/simple_test.py > /tmp/api_test_results.log 2>&1
echo "API test completed. Results in /tmp/api_test_results.log"

echo "Starting Arize Phoenix on port $PHOENIX_PORT"

# Execute the command passed to the entrypoint
export PHOENIX_HOST=0.0.0.0
export PHOENIX_DEFAULT_ROUTE_COMPONENT=true
exec python -m phoenix.server.main serve