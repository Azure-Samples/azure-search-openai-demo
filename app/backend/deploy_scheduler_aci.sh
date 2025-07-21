#!/bin/bash
"""
Deploy SharePoint Scheduler to Azure Container Instances
========================================================
"""

# Variables
RESOURCE_GROUP="rg-volaris-dev-eus-001"
CONTAINER_NAME="sharepoint-scheduler"
IMAGE_NAME="sharepoint-scheduler:latest"
REGISTRY_NAME="crvolaris.azurecr.io"

echo "🚀 Desplegando SharePoint Scheduler a Azure Container Instances..."

# 1. Build y push de imagen
echo "📦 Construyendo imagen Docker..."
docker build -f Dockerfile.scheduler -t $IMAGE_NAME .

echo "📤 Subiendo a Azure Container Registry..."
az acr login --name $REGISTRY_NAME
docker tag $IMAGE_NAME $REGISTRY_NAME/$IMAGE_NAME
docker push $REGISTRY_NAME/$IMAGE_NAME

# 2. Crear Container Instance
echo "🏗️ Creando Azure Container Instance..."
az container create \
  --resource-group $RESOURCE_GROUP \
  --name $CONTAINER_NAME \
  --image $REGISTRY_NAME/$IMAGE_NAME \
  --cpu 1 \
  --memory 2 \
  --restart-policy Always \
  --environment-variables \
    AZURE_ENV_NAME=dev \
    PYTHONUNBUFFERED=1 \
  --assign-identity \
  --command-line "python3 scheduler_sharepoint_sync.py --interval 6" \
  --logs

echo "✅ SharePoint Scheduler desplegado exitosamente"
echo "📊 Para ver logs: az container logs --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME"
