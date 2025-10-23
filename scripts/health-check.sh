#!/bin/bash

# Quick health check for all services

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

check_service() {
    local name=$1
    local url=$2

    if curl -s "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $name is running"
    else
        echo -e "${RED}✗${NC} $name is NOT running"
    fi
}

echo "Bibliography Health Check"
echo "========================="
echo ""

check_service "Backend API    " "http://localhost:8000/docs"
check_service "Frontend       " "http://localhost:3000"

# Check PostgreSQL
if command -v pg_isready &> /dev/null; then
    if pg_isready -h localhost -p 5432 &> /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} PostgreSQL is running"
    else
        echo -e "${RED}✗${NC} PostgreSQL is NOT running"
    fi
else
    echo -e "${YELLOW}⚠${NC} PostgreSQL status unknown"
fi

echo ""
