#!/bin/bash

# Docker Health Check Script for RestlessResume
# Verifies that all services are running and healthy

set -e

echo "RestlessResume Docker Health Check"
echo "=================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    local service=$1
    local status=$2
    if [ "$status" = "healthy" ]; then
        echo -e "${GREEN}✓${NC} $service: $status"
    elif [ "$status" = "unhealthy" ]; then
        echo -e "${RED}✗${NC} $service: $status"
        exit 1
    else
        echo -e "${YELLOW}⚠${NC} $service: $status"
    fi
}

# Function to check service health
check_service() {
    local service=$1
    local status=$(docker-compose ps $service --format "{{.State}}" 2>/dev/null || echo "not found")
    print_status "$service" "$status"
}

echo "Checking container status..."
docker-compose ps

echo ""
echo "Checking service health..."

# Check PostgreSQL
echo ""
echo "Database Service (PostgreSQL):"
if docker-compose exec -T postgres pg_isready -U ${DB_USER:-resumeuser} > /dev/null 2>&1; then
    print_status "PostgreSQL" "healthy"
else
    print_status "PostgreSQL" "unhealthy"
    exit 1
fi

# Check API
echo ""
echo "Application Service (FastAPI):"
if curl -f -s http://localhost:8000/docs > /dev/null 2>&1; then
    print_status "FastAPI" "healthy"
else
    print_status "FastAPI" "unhealthy"
    exit 1
fi

echo ""
echo "Checking database connectivity..."
db_status=$(docker-compose exec -T postgres psql -U ${DB_USER:-resumeuser} -d ${DB_NAME:-restless_resume} -c "SELECT 1" 2>&1)
if [ $? -eq 0 ]; then
    print_status "Database Connection" "healthy"
else
    print_status "Database Connection" "unhealthy"
    exit 1
fi

echo ""
echo "=================================="
echo -e "${GREEN}All services are healthy!${NC}"
echo ""
echo "Quick Links:"
echo "  Web Interface: http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo "  Database: postgresql://localhost:5432/${DB_NAME:-restless_resume}"
echo ""
echo "Useful Commands:"
echo "  View logs:     docker-compose logs -f app"
echo "  Database CLI:  docker-compose exec postgres psql -U ${DB_USER:-resumeuser} -d ${DB_NAME:-restless_resume}"
echo "  App shell:     docker-compose exec app bash"
echo ""
