# Local Development Runbook

## Prerequisites
- Docker Desktop
- Python 3.11+

## Setup
1. Copy `.env.example` to `.env` and fill in values.
2. Build containers: `docker-compose build`
3. Start services: `docker-compose up`

## Verification
- Web app: http://localhost:5000
- Model serving: http://localhost:8000/health

## Troubleshooting
- Check container logs with `docker-compose logs`