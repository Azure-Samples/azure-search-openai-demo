## Set the preference to stop on the first error
$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "Loading azd .env file from current environment"
Write-Host ""

$output = azd env get-values

foreach ($line in $output) {
  if (!$line.Contains('=')) {
    continue
  }

  $name, $value = $line.Split("=")
  $value = $value -replace '^\"|\"$'
  [Environment]::SetEnvironmentVariable($name, $value)
}

Write-Host "Environment variables set."

if ([string]::IsNullOrEmpty($env:AZURE_ADLS_GEN2_STORAGE_ACCOUNT)) {
    Write-Error "AZURE_ADLS_GEN2_STORAGE_ACCOUNT must be set in order to continue"
    exit 1
}

# Create default Security Groups

# az ad group create creates security enabled groups. It's possible the account used doesn't have permission to do this, and the group creation will fail.
# To work around this, you can follow the steps here https://learn.microsoft.com/azure/active-directory/fundamentals/how-to-manage-groups#create-a-basic-group-and-add-members
# Create groups with the names GPTKB_AdminTest, GPTKB_EmployeeTest, GPTKB_HRTest with the Microsoft 365 group type.
# Re-run this script and the existing groups will be used instead.
function Ensure-SecurityGroupExists {
  param (
    [string]$groupName
  )

  $result = az ad group show --group $groupName | ConvertFrom-Json
  if (-not $result) {
    Write-Host "Creating group $groupName"
    $output = az ad group create --display-name $groupName --mail-nickname $groupName 2>&1
    if ($?) {
      $result = $output | ConvertFrom-Json
    }

    throw $output
  }

  return $result | Select -Expand id
}
Write-Host "Ensuring Security Groups exist..."
$adminId = Ensure-SecurityGroupExists -GroupName GPTKB_AdminTest
$employeeId = Ensure-SecurityGroupExists -GroupName GPTKB_EmployeeTest
$hrId = Ensure-SecurityGroupExists -GroupName GPTKB_HRTest
Write-Host "Admin ID: $adminId"
Write-Host "Employee ID: $employeeId"
Write-Host "HR ID: $hrId"

# Create default ADLS Gen2 Container
Write-Host "Ensuring ADLS Gen2 filesystem exists..."
$result = az storage fs exists -n gptkbcontainer --account-name $env:AZURE_ADLS_GEN2_STORAGE_ACCOUNT --auth-mode login | ConvertFrom-Json
if (-not $result.exists) {
  Write-Host "Creating ADLS Gen2 filesystem..."
  $result = az storage fs create -n gptkbcontainer --account-name $env:AZURE_ADLS_GEN2_STORAGE_ACCOUNT --auth-mode login
}

# Create ADLS Gen2 Container directories
function Ensure-DirectoryExists {
  param (
    [string]$directoryName,
    [string]$filesystemName
  )

  $result = az storage fs directory exists --file-system $filesystemName --name $directoryName --account-name $env:AZURE_ADLS_GEN2_ACCOUNT --auth-mode login | ConvertFrom-Json
  if (-not $result.exists) {
    Write-Host "Creating directory $directoryName"
    $result = az storage fs directory create --file-system $filesystemName --name $directoryName --account-name $env:AZURE_ADLS_GEN2_ACCOUNT --auth-mode login
  }

}
Write-Host "Ensuring directories exist..."
Ensure-DirectoryExists -DirectoryName benefitinfo -FilesystemName gptkbcontainer
Ensure-DirectoryExists -DirectoryName employeeinfo -FilesystemName gptkbcontainer

# Upload PDFs to the correct folders
Write-Host "Uploading PDFs..."
$result = az storage fs file upload --file-system gptkbcontainer --path benefitinfo/Benefit_Options.pdf --source "../data/Benefit_Options.pdf" --account-name $env:AZURE_ADLS_GEN2_ACCOUNT --auth-mode login
$result = az storage fs file upload --file-system gptkbcontainer --path benefitinfo/Northwind_Health_Plus_Benefits_Details.pdf --source "../data/Northwind_Health_Plus_Benefits_Details.pdf" --overwrite --account-name $env:AZURE_ADLS_GEN2_ACCOUNT --auth-mode login
$result = az storage fs file upload --file-system gptkbcontainer --path benefitinfo/Northwind_Standard_Benefits_Details.pdf --source "../data/Northwind_Standard_Benefits_Details.pdf" --overwrite --account-name $env:AZURE_ADLS_GEN2_ACCOUNT --auth-mode login
$result = az storage fs file upload --file-system gptkbcontainer --path benefitinfo/PerksPlus.pdf --source "../data/PerksPlus.pdf" --overwrite --account-name $env:AZURE_ADLS_GEN2_ACCOUNT --auth-mode login
$result = az storage fs file upload --file-system gptkbcontainer --path employeeinfo/employee_handbook.pdf --source "../data/employee_handbook.pdf" --overwrite --account-name $env:AZURE_ADLS_GEN2_ACCOUNT --auth-mode login
$result = az storage fs file upload --file-system gptkbcontainer --path employeeinfo/role_library.pdf --source "../data/role_library.pdf" --overwrite --account-name $env:AZURE_ADLS_GEN2_ACCOUNT --auth-mode login

# Setup ADLS Gen2 Access Control List on filesystem and directory
Write-Host "Setting permissions"

# Every group needs Execute permissions on the root folder of the container for ACLs to work on files.
# Explicitly set this ACL on the root directory for employee and hr groups
# For more information please see https://learn.microsoft.com/azure/storage/blobs/data-lake-storage-access-control#levels-of-permission
$result = az storage fs access set --acl "group:${employeeId}:r-x,group:${hrId}:r-x" --path . --file-system gptkbcontainer --account-name $env:AZURE_ADLS_GEN2_ACCOUNT --auth-mode login
# Admins can read all files
$result = az storage fs access update-recursive --acl "group:${adminId}:r-x" --path . --file-system gptkbcontainer --account-name $env:AZURE_ADLS_GEN2_ACCOUNT --auth-mode login

# Employees group can access benefit info
$result = az storage fs access update-recursive --acl "group:${employeeId}:r-x" --path benefitinfo --file-system gptkbcontainer --account-name $env:AZURE_ADLS_GEN2_ACCOUNT --auth-mode login

# HR group can access benefit info and employee info
$result = az storage fs access update-recursive --acl "group:${hrId}:r-x" --path benefitinfo --file-system gptkbcontainer --account-name $env:AZURE_ADLS_GEN2_ACCOUNT --auth-mode login
$result = az storage fs access update-recursive --acl "group:${hrId}:r-x" --path employeeinfo --file-system gptkbcontainer --account-name $env:AZURE_ADLS_GEN2_ACCOUNT --auth-mode login