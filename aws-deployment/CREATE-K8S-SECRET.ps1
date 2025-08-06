# Script to create Kubernetes secret with your credentials
Write-Host "=== Creating Kubernetes Secret for LegalLLM ===" -ForegroundColor Green
Write-Host "This script will securely create your Kubernetes secrets" -ForegroundColor Cyan
Write-Host ""

# Get RDS and Redis endpoints
Write-Host "Getting your AWS resource endpoints..." -ForegroundColor Yellow

$RDS_ENDPOINT = aws rds describe-db-instances `
    --region ap-southeast-2 `
    --query "DBInstances[?DBName=='legalllm'].Endpoint.Address" `
    --output text

# Try serverless cache first
$REDIS_ENDPOINT = aws elasticache describe-serverless-caches `
    --region ap-southeast-2 `
    --query "ServerlessCaches[?contains(ServerlessCacheName, 'legalllm')].Endpoint.Address" `
    --output text

# If not found, try regular cache clusters
if ([string]::IsNullOrEmpty($REDIS_ENDPOINT)) {
    $REDIS_ENDPOINT = aws elasticache describe-cache-clusters `
        --region ap-southeast-2 `
        --show-cache-node-info `
        --query "CacheClusters[?contains(CacheClusterId, 'legalllm')].CacheNodes[0].Endpoint.Address" `
        --output text
}

if ([string]::IsNullOrEmpty($RDS_ENDPOINT)) {
    Write-Host "No RDS database found. Please enter manually:" -ForegroundColor Yellow
    $RDS_ENDPOINT = Read-Host "Enter RDS Endpoint"
}

if ([string]::IsNullOrEmpty($REDIS_ENDPOINT)) {
    Write-Host "No Redis cluster found. Please enter manually:" -ForegroundColor Yellow
    $REDIS_ENDPOINT = Read-Host "Enter Redis Endpoint"
}

Write-Host "`nFound endpoints:" -ForegroundColor Green
Write-Host "RDS: $RDS_ENDPOINT"
Write-Host "Redis: $REDIS_ENDPOINT"

# Collect passwords
Write-Host "`nPlease enter your passwords (they won't be shown on screen):" -ForegroundColor Yellow

$DB_PASSWORD = Read-Host "Enter your RDS Database Password" -AsSecureString
$DB_PASSWORD_PLAIN = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($DB_PASSWORD))

$REDIS_PASSWORD = Read-Host "Enter your Redis Password" -AsSecureString
$REDIS_PASSWORD_PLAIN = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($REDIS_PASSWORD))

$OPENAI_KEY = Read-Host "Enter your OpenAI API Key" -AsSecureString
$OPENAI_KEY_PLAIN = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($OPENAI_KEY))

# Generate secret keys
Write-Host "`nGenerating secure keys..." -ForegroundColor Yellow
$SECRET_KEY = [System.Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
$JWT_SECRET = [System.Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))

# URL encode password for connection strings
Add-Type -AssemblyName System.Web
$DB_PASSWORD_ENCODED = [System.Web.HttpUtility]::UrlEncode($DB_PASSWORD_PLAIN)
$REDIS_PASSWORD_ENCODED = [System.Web.HttpUtility]::UrlEncode($REDIS_PASSWORD_PLAIN)

# Create the secret YAML
$secretYaml = @"
apiVersion: v1
kind: Secret
metadata:
  name: legalllm-secrets
  namespace: legalllm
type: Opaque
stringData:
  # Database Credentials
  DB_HOST: "$RDS_ENDPOINT"
  DB_PASSWORD: "$DB_PASSWORD_PLAIN"
  DATABASE_URL: "postgresql://legalllm_admin:${DB_PASSWORD_ENCODED}@${RDS_ENDPOINT}:5432/legalllm"
  
  # Redis Credentials
  REDIS_HOST: "$REDIS_ENDPOINT"
  REDIS_PASSWORD: "$REDIS_PASSWORD_PLAIN"
  REDIS_URL: "redis://:${REDIS_PASSWORD_ENCODED}@${REDIS_ENDPOINT}:6379/0"
  
  # OpenAI API Key
  OPENAI_API_KEY: "$OPENAI_KEY_PLAIN"
  
  # Security Keys
  SECRET_KEY: "$SECRET_KEY"
  JWT_SECRET_KEY: "$JWT_SECRET"
"@

# Save to file
$secretYaml | Out-File -FilePath "k8s-secret.yaml" -Encoding UTF8

Write-Host "`nSecret file created successfully!" -ForegroundColor Green
Write-Host "Applying secret to Kubernetes..." -ForegroundColor Yellow

# Apply the secret
kubectl create namespace legalllm 2>$null
kubectl apply -f k8s-secret.yaml

if ($LASTEXITCODE -eq 0) {
    Write-Host "Secret applied successfully!" -ForegroundColor Green
    
    # Delete the file for security
    Write-Host "Deleting secret file for security..." -ForegroundColor Yellow
    Remove-Item -Path "k8s-secret.yaml" -Force
    Write-Host "Secret file deleted" -ForegroundColor Green
} else {
    Write-Host "Failed to apply secret. Please check the error above." -ForegroundColor Red
}

Write-Host "`nSecret creation complete!" -ForegroundColor Green