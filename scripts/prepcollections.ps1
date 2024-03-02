	
$ErrorActionPreference = [System.Management.Automation.ActionPreference]::Stop

$outputDataDir = "..\data\collections"

Get-ChildItem "data-collections" -Filter *.urls |
ForEach-Object {
    $fileName = $_.FullName
    $collectionName = $_.BaseName
    
    $outputPath = "$($outputDataDir)\$($collectionName)"

    Write-Host ""
    Write-Host "Fetching collection: $($collectionName)"

    if (-not ($(Test-Path -Path $outputPath -PathType Container))) {
       New-Item -Path $outputDataDir -Name $collectionName  -ItemType "directory" | Out-Null
    }

    $downloadUrls = (Get-Content -Path $fileName | Select-String -Pattern '^http://','^https://').Line
            
    ForEach ($downloadUrl in $downloadUrls) {
        $uri = [System.Uri]$downloadUrl
        $fileName = $uri.Segments | Select-Object -Last 1
        $outFile = "$($outputDataDir)\$($fileName)"

        if(-not ($(Test-Path -Path $outFile -PathType Leaf))) {
            try {
                Write-Host "Downloading $($fileName) from $($uri.Authority)"
                $Response = Invoke-WebRequest -Uri $downloadUrl -OutFile $outFile -ErrorAction Continue
                # 2 second delay between requests
                Start-Sleep -Seconds 2
            } catch {
                Write-Error "Failed to download $($fileName)!" -ErrorAction Continue
            }
        } else {
            # Resume not supported
        }        
    }
}
