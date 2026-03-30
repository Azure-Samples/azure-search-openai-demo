$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
  $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue
}
if (-not $pythonCmd) {
  Write-Error "Python not found, please install python."
  exit 1
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Start-Process -FilePath ($pythonCmd).Source -ArgumentList "$scriptDir/copy_prepdocslib.py" -Wait -NoNewWindow
