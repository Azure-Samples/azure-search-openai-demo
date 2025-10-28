#!/usr/bin/env pwsh

# Script to build the frontend for Azure deployment
Set-Location -Path (Join-Path $PSScriptRoot "../app/frontend")
Write-Host "Installing frontend dependencies..."
npm install
Write-Host "Building frontend..."
npm run build
Write-Host "Frontend build completed successfully!"
