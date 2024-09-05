$projectRoot = Split-Path -Parent $PSScriptRoot

& $projectRoot/scripts/load_azd_env.ps1

& $projectRoot/scripts/load_python_env.ps1
