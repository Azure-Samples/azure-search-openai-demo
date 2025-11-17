#!/bin/bash
# Bash script to build and deploy agents service using Docker
# This script builds a Docker image and deploys it to Azure App Service

set -e

IMAGE_TAG=${IMAGE_TAG:-"latest"}
SKIP_BUILD=${SKIP_BUILD:-"false"}

echo "=== Agents Service Docker Deployment ==="

# Check if azd is available
if ! command -v azd &> /dev/null; then
    echo "ERROR: Azure Developer CLI (azd) is not installed."
    exit 1
fi

# Load environment variables
echo "Loading environment variables..."
azd env refresh

# Get required environment variables
RESOURCE_GROUP=$(azd env get-value AZURE_RESOURCE_GROUP)
AGENTS_SERVICE_NAME=$(azd env get-value AZURE_AGENTS_SERVICE_NAME)
SUBSCRIPTION_ID=$(azd env get-value AZURE_SUBSCRIPTION_ID)

# Try to get ACR name (may not exist if using App Service)
ACR_NAME=$(azd env get-value AZURE_CONTAINER_REGISTRY_NAME 2>/dev/null || echo "")

if [ -z "$RESOURCE_GROUP" ] || [ -z "$AGENTS_SERVICE_NAME" ]; then
    echo "ERROR: Required environment variables not found."
    echo "Please ensure AZURE_RESOURCE_GROUP and AZURE_AGENTS_SERVICE_NAME are set."
    exit 1
fi

echo "Resource Group: $RESOURCE_GROUP"
echo "Service Name: $AGENTS_SERVICE_NAME"
echo "Image Tag: $IMAGE_TAG"

# Option 1: Build and push to ACR (if available)
if [ -n "$ACR_NAME" ]; then
    echo ""
    echo "Building Docker image and pushing to Azure Container Registry..."
    
    if [ "$SKIP_BUILD" != "true" ]; then
        az acr build \
            --registry "$ACR_NAME" \
            --image agents-service:$IMAGE_TAG \
            --file Dockerfile \
            .
        
        if [ $? -ne 0 ]; then
            echo "ERROR: Failed to build and push Docker image."
            exit 1
        fi
    fi
    
    IMAGE_NAME="${ACR_NAME}.azurecr.io/agents-service:${IMAGE_TAG}"
    echo "Image: $IMAGE_NAME"
    
    # Configure App Service to use the Docker image
    echo ""
    echo "Configuring App Service to use Docker image..."
    az webapp config container set \
        --name "$AGENTS_SERVICE_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --docker-custom-image-name "$IMAGE_NAME" \
        --docker-registry-server-url "https://${ACR_NAME}.azurecr.io"
    
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to configure App Service."
        exit 1
    fi
    
    echo ""
    echo "✅ Docker deployment completed successfully!"
    echo "App Service is now using Docker image: $IMAGE_NAME"
else
    # Option 2: Build locally and deploy using azd (if ACR not available)
    echo ""
    echo "ACR not found. Building Docker image locally..."
    echo "Note: For production, consider setting up Azure Container Registry."
    
    # Build image locally
    if [ "$SKIP_BUILD" != "true" ]; then
        docker build -t agents-service:$IMAGE_TAG .
        
        if [ $? -ne 0 ]; then
            echo "ERROR: Failed to build Docker image locally."
            exit 1
        fi
    fi
    
    echo ""
    echo "For App Service Docker deployment, you need to:"
    echo "1. Push the image to a container registry (Docker Hub, ACR, etc.)"
    echo "2. Configure App Service to use the image from the registry"
    echo ""
    echo "Or use: azd deploy --service agents (for ZIP deployment)"
fi

echo ""
echo "Deployment script completed."


