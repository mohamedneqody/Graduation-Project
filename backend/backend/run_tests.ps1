# Script to automate setting up the testing environment and running pytest
Write-Host "Starting test database and redis..."
docker-compose -f docker-compose.test.yml up -d

Write-Host "Waiting for database to be ready (10 seconds)..."
Start-Sleep -Seconds 10

Write-Host "Running pytest..."
$env:REDIS_URL = "redis://localhost:6389/0"
python -m pytest

Write-Host "Tearing down test environment..."
docker-compose -f docker-compose.test.yml down

Write-Host "Done!"
