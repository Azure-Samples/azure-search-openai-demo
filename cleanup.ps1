# Cleanup Script - Removes temporary and cache files
# Safe cleanup - keeps all source code and documentation

Write-Host "`n=== CLEANING UP PROJECT ===" -ForegroundColor Yellow
Write-Host "This will remove temporary files, cache files, and .env files" -ForegroundColor Cyan
Write-Host "Source code and documentation will be preserved`n" -ForegroundColor Green

$itemsRemoved = 0

# Remove Python cache files
Write-Host "Cleaning Python cache files..." -ForegroundColor Yellow
Get-ChildItem -Path . -Recurse -Directory -Filter "__pycache__" -Force -ErrorAction SilentlyContinue | ForEach-Object {
    $itemsRemoved++
    Remove-Item -Path $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "  Removed: $($_.FullName)" -ForegroundColor Gray
}

# Remove .pyc files
Write-Host "Cleaning .pyc files..." -ForegroundColor Yellow
Get-ChildItem -Path . -Recurse -Filter "*.pyc" -Force -ErrorAction SilentlyContinue | ForEach-Object {
    $itemsRemoved++
    Remove-Item -Path $_.FullName -Force -ErrorAction SilentlyContinue
    Write-Host "  Removed: $($_.FullName)" -ForegroundColor Gray
}

# Remove .pyo files
Write-Host "Cleaning .pyo files..." -ForegroundColor Yellow
Get-ChildItem -Path . -Recurse -Filter "*.pyo" -Force -ErrorAction SilentlyContinue | ForEach-Object {
    $itemsRemoved++
    Remove-Item -Path $_.FullName -Force -ErrorAction SilentlyContinue
}

# Remove .env files (WARNING: This removes environment files!)
Write-Host "Cleaning .env files..." -ForegroundColor Yellow
Get-ChildItem -Path . -Recurse -Filter ".env" -Force -ErrorAction SilentlyContinue | ForEach-Object {
    $itemsRemoved++
    Remove-Item -Path $_.FullName -Force -ErrorAction SilentlyContinue
    Write-Host "  Removed: $($_.FullName)" -ForegroundColor Gray
}

# Remove .env.* files (but keep .env.example)
Write-Host "Cleaning .env.* files (keeping .env.example)..." -ForegroundColor Yellow
Get-ChildItem -Path . -Recurse -Filter ".env.*" -Force -ErrorAction SilentlyContinue | Where-Object { $_.Name -notlike "*.example" } | ForEach-Object {
    $itemsRemoved++
    Remove-Item -Path $_.FullName -Force -ErrorAction SilentlyContinue
    Write-Host "  Removed: $($_.FullName)" -ForegroundColor Gray
}

# Remove node_modules (if exists)
Write-Host "Cleaning node_modules..." -ForegroundColor Yellow
Get-ChildItem -Path . -Recurse -Directory -Filter "node_modules" -Force -ErrorAction SilentlyContinue | ForEach-Object {
    $itemsRemoved++
    Write-Host "  Removing: $($_.FullName) (this may take a while)..." -ForegroundColor Gray
    Remove-Item -Path $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
}

# Remove .pytest_cache
Write-Host "Cleaning pytest cache..." -ForegroundColor Yellow
Get-ChildItem -Path . -Recurse -Directory -Filter ".pytest_cache" -Force -ErrorAction SilentlyContinue | ForEach-Object {
    $itemsRemoved++
    Remove-Item -Path $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
}

# Remove .mypy_cache
Write-Host "Cleaning mypy cache..." -ForegroundColor Yellow
Get-ChildItem -Path . -Recurse -Directory -Filter ".mypy_cache" -Force -ErrorAction SilentlyContinue | ForEach-Object {
    $itemsRemoved++
    Remove-Item -Path $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
}

# Remove dist and build folders
Write-Host "Cleaning build artifacts..." -ForegroundColor Yellow
@("dist", "build", ".egg-info") | ForEach-Object {
    Get-ChildItem -Path . -Recurse -Directory -Filter $_ -Force -ErrorAction SilentlyContinue | ForEach-Object {
        $itemsRemoved++
        Remove-Item -Path $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "  Removed: $($_.FullName)" -ForegroundColor Gray
    }
}

# Remove .DS_Store files (macOS)
Write-Host "Cleaning .DS_Store files..." -ForegroundColor Yellow
Get-ChildItem -Path . -Recurse -Filter ".DS_Store" -Force -ErrorAction SilentlyContinue | ForEach-Object {
    $itemsRemoved++
    Remove-Item -Path $_.FullName -Force -ErrorAction SilentlyContinue
}

# Remove Thumbs.db files (Windows)
Write-Host "Cleaning Thumbs.db files..." -ForegroundColor Yellow
Get-ChildItem -Path . -Recurse -Filter "Thumbs.db" -Force -ErrorAction SilentlyContinue | ForEach-Object {
    $itemsRemoved++
    Remove-Item -Path $_.FullName -Force -ErrorAction SilentlyContinue
}

Write-Host "`n=== CLEANUP COMPLETE ===" -ForegroundColor Green
Write-Host "Items removed: $itemsRemoved" -ForegroundColor Cyan
Write-Host "`nSource code and documentation preserved." -ForegroundColor Green
Write-Host "You can now start fresh!`n" -ForegroundColor Yellow




