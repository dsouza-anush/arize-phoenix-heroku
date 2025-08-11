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

echo "Starting Arize Phoenix on port $PHOENIX_PORT"

# Execute the command passed to the entrypoint
exec python -m phoenix.server.main serve --host=0.0.0.0 --port="$PHOENIX_PORT"