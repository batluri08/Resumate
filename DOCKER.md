# Docker Setup Guide - RestlessResume

This guide covers running RestlessResume using Docker and Docker Compose for development and production environments.

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 2GB minimum RAM available
- Port 8000 (app) and 5432 (database) available

## Quick Start

### 1. Clone and Setup

```bash
git clone <repository>
cd RestlessResume
cp .env.example .env
```

### 2. Configure Environment Variables

Edit `.env` with your settings:

```env
# Database
DB_USER=resumeuser
DB_PASSWORD=your_secure_password_here
DB_NAME=restless_resume

# OpenAI
OPENAI_API_KEY=sk-your-key-here

# Google OAuth2
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret

# Environment
ENVIRONMENT=development
```

### 3. Start Services

```bash
docker-compose up -d
```

This will:
- Build the RestlessResume Docker image
- Start PostgreSQL database
- Start the FastAPI application
- Create necessary volumes and networks

### 4. Access Application

- **Web Interface**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Database**: PostgreSQL on localhost:5432

## Common Commands

### View Logs

```bash
# View all services
docker-compose logs

# View specific service
docker-compose logs app
docker-compose logs postgres

# Follow logs in real-time
docker-compose logs -f app
```

### Stop Services

```bash
# Stop without removing
docker-compose stop

# Stop and remove containers
docker-compose down

# Remove containers and volumes (data loss!)
docker-compose down -v
```

### Rebuild Application

```bash
# Rebuild Docker image after code changes
docker-compose build

# Rebuild and start
docker-compose up -d --build
```

### Access Database

```bash
# Connect to PostgreSQL in container
docker-compose exec postgres psql -U resumeuser -d restless_resume

# Run query
docker-compose exec postgres psql -U resumeuser -d restless_resume -c "SELECT * FROM users;"
```

### Run Commands in Container

```bash
# Execute shell command in app
docker-compose exec app bash

# Run Python script
docker-compose exec app python -c "print('Hello')"
```

## Development vs Production

### Development Setup (docker-compose.yml)

- Uses local code mounting for hot-reload
- Logs to stdout
- Health checks enabled
- Volumes for uploads and logs

**Start**: `docker-compose up`

### Production Setup (docker-compose.prod.yml)

For production, create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    container_name: restless-resume-db-prod
    environment:
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: ${DB_NAME}
    volumes:
      - /data/postgres:/var/lib/postgresql/data
    restart: always
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  app:
    image: restless-resume:1.0
    container_name: restless-resume-app-prod
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/${DB_NAME}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      GOOGLE_CLIENT_ID: ${GOOGLE_CLIENT_ID}
      GOOGLE_CLIENT_SECRET: ${GOOGLE_CLIENT_SECRET}
      ENVIRONMENT: production
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/docs"]
      interval: 30s
      timeout: 10s
      retries: 3
```

**Build and run**:
```bash
docker build -t restless-resume:1.0 .
docker-compose -f docker-compose.prod.yml up -d
```

## Using Nginx Reverse Proxy

For production with Nginx:

```yaml
nginx:
  image: nginx:alpine
  container_name: restless-resume-proxy
  ports:
    - "80:80"
    - "443:443"
  volumes:
    - ./nginx.conf:/etc/nginx/nginx.conf:ro
    - /etc/letsencrypt:/etc/letsencrypt:ro
  depends_on:
    - app
  restart: always
```

## Building Docker Image Manually

```bash
# Build image
docker build -t restless-resume:latest .

# Run container
docker run -d \
  --name restless-resume \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:pass@host:5432/db \
  -e OPENAI_API_KEY=sk-... \
  restless-resume:latest

# Run with volume mounts
docker run -d \
  --name restless-resume \
  -p 8000:8000 \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/logs:/app/logs \
  -e DATABASE_URL=... \
  restless-resume:latest
```

## Troubleshooting

### Application won't start

```bash
# Check logs
docker-compose logs app

# Common issues:
# 1. Database not ready - wait a bit, health check retries 5 times
# 2. Missing environment variables - check .env file
# 3. Port already in use - change port in docker-compose.yml
```

### Database connection error

```bash
# Verify database is running and healthy
docker-compose ps

# Check database logs
docker-compose logs postgres

# Try connecting directly
docker-compose exec postgres psql -U resumeuser -d restless_resume
```

### Rebuild everything from scratch

```bash
docker-compose down -v
docker-compose build --no-cache
docker-compose up
```

### Permission denied errors

```bash
# Fix volume permissions (Linux)
sudo chown -R $USER:$USER uploads logs
# Or run with sudo
sudo docker-compose up
```

## Performance Tips

1. **Use .dockerignore** - Already configured to exclude unnecessary files
2. **Multi-stage builds** - Dockerfile uses multi-stage to reduce image size
3. **Volume mounting** - Don't mount large directories (use named volumes)
4. **Resource limits** - Add to docker-compose.yml:
   ```yaml
   services:
     app:
       deploy:
         resources:
           limits:
             cpus: '1'
             memory: 1G
   ```

## Health Checks

Both services have health checks configured:

- **PostgreSQL**: Checks if it's accepting connections
- **App**: Checks if /docs endpoint responds

View health status:
```bash
docker-compose ps
# STATUS shows "healthy" or "unhealthy"
```

## Backing Up Data

```bash
# Backup database
docker-compose exec postgres pg_dump -U resumeuser restless_resume > backup.sql

# Backup uploads
tar -czf uploads-backup.tar.gz uploads/

# Restore database
docker-compose exec -T postgres psql -U resumeuser restless_resume < backup.sql
```

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [PostgreSQL in Docker](https://hub.docker.com/_/postgres)

## Support

For issues or questions:
1. Check logs: `docker-compose logs`
2. Verify environment variables in `.env`
3. Ensure ports 8000 and 5432 are available
4. Check Docker and Docker Compose versions
