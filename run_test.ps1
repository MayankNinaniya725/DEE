$packageList = @("reportlab")
foreach ($package in $packageList) {
    Write-Host "Checking for $package..."
    $installed = pip freeze | Where-Object { $_ -like "$package=*" }
    
    if (-not $installed) {
        Write-Host "Installing $package..."
        pip install $package
    } else {
        Write-Host "$package is already installed: $installed"
    }
}

Write-Host "All required packages are installed. Running test script..."
python test_extraction.py
