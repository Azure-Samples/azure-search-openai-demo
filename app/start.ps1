# From a list o variables and values, set them as environment variables
$list_var = azd env get-values --output json
# From JSON variable, get the list of variables
$list_var = $list_var | ConvertFrom-Json -AsHashtable
# $list_var is a Orderedhashtable with the variables and values
# For each variable, set it as environment variable in the current session


# Check if list_var is empty
if ($list_var.Count -eq 0) {
    Write-Output "No variables to set"
    exit 1
} else {
    Write-Output "Setting variables"
}
foreach ($key in $list_var.Keys) {
    Write-Output "$key = $($list_var[$key])"
    Set-Item -Path "Env:$key" -Value $($list_var[$key])
}

Write-Output "Handle python dependencies"
cd backend
pip install -r requirements.txt

Write-Output "Handle node dependencies"
cd ../frontend
npm install

# Start the app
Write-Output "Start the app"
cd ..
python3 backend/app.py
