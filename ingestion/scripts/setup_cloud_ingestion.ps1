Write-Host "Setting up cloud ingestion..."

# Load environment variables from azd
$envValues = azd env get-values
foreach ($line in $envValues) {
    if ($line -match "^([^=]+)=(.*)$") {
        $name = $matches[1]
        $value = $matches[2].Trim('"')
        [Environment]::SetEnvironmentVariable($name, $value, "Process")
    }
}

# Run the cloud ingestion setup script
python "$PSScriptRoot/setup_cloud_ingestion.py"

Write-Host "Cloud ingestion setup complete."
