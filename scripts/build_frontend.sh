#!/bin/bash

# Script to build the frontend for Azure deployment
cd "$(dirname "$0")/../app/frontend"
echo "Installing frontend dependencies..."
npm install
echo "Building frontend..."
npm run build
echo "Frontend build completed successfully!"
