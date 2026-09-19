#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting test environment...${NC}"

# Start PostgreSQL and Redis containers if not already running
docker-compose up -d postgres redis

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
until docker-compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; do
    sleep 1
done

# Create test database
echo "Creating test database..."
docker-compose exec -T postgres psql -U postgres -c "DROP DATABASE IF EXISTS bookmarks_test;"
docker-compose exec -T postgres psql -U postgres -c "CREATE DATABASE bookmarks_test;"

# Set test database URL
export TEST_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/bookmarks_test"
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/bookmarks"
export REDIS_URL="redis://localhost:6379/0"

echo -e "${GREEN}Running tests...${NC}"

# Run tests with pytest
python -m pytest tests/ -v

# Capture exit code
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
else
    echo -e "${RED}Some tests failed.${NC}"
fi

exit $EXIT_CODE
