function Check-MicrosoftStore {
    Write-Host "[4/5] Checking Microsoft Store Apps..." -ForegroundColor Yellow
    try {
        Write-Host "  ℹ Opening Microsoft Store to check for updates..." -ForegroundColor Cyan
        Write-Host "    Please check manually: MS Store > Library > Get Updates" -ForegroundColor Gray
        Start-Process "ms-windows-store://downloadsandupdates"
    } catch {
        Write-Host "  ✗ Error opening Microsoft Store: $($_.Exception.Message)" -ForegroundColor Red
    }
    Write-Host ""
}

function Get-OutdatedDrivers {
    Write-Host "[5/5] Listing Installed Drivers..." -ForegroundColor Yellow
    try {
        $drivers = Get-WmiObject Win32_PnPSignedDriver | 
            Where-Object { $_.DeviceName -ne $null } |
            Select-Object DeviceName, DriverVersion, DriverDate, Manufacturer |
            Sort-Object DeviceName
        
        Write-Host "  ℹ Total drivers found: $($drivers.Count)" -ForegroundColor Cyan
        Write-Host "  ℹ Check manufacturer websites for latest versions" -ForegroundColor Gray
        
        $oldDrivers = $drivers | Where-Object { 
            $_.DriverDate -and ([DateTime]$_.DriverDate).Year -lt (Get-Date).Year - 1 
        }
        
        if ($oldDrivers.Count -gt 0) {
            Write-Host "  ! $($oldDrivers.Count) driver(s) older than 1 year:" -ForegroundColor Yellow
            $oldDrivers | Select-Object -First 10 | ForEach-Object {
                Write-Host "    - $($_.DeviceName) ($(([DateTime]$_.DriverDate).ToString('yyyy-MM-dd')))" -ForegroundColor Gray
            }
        }
    } catch {
        Write-Host "  ✗ Error listing drivers: $($_.Exception.Message)" -ForegroundColor Red
    }
    Write-Host ""
}

Check-WindowsUpdates
Check-Drivers
Check-Winget
Check-MicrosoftStore
Get-OutdatedDrivers

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Scan Complete!" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Recommendations:" -ForegroundColor Yellow
Write-Host "1. Install Windows updates from Settings > Windows Update" -ForegroundColor White
Write-Host "2. Update drivers using Device Manager or manufacturer tools" -ForegroundColor White
Write-Host "3. Run 'winget upgrade --all' to update apps" -ForegroundColor White
Write-Host "4. Visit manufacturer websites for critical drivers (GPU, chipset)" -ForegroundColor White
Write-Host ""
Read-Host "Press Enter to exit"
