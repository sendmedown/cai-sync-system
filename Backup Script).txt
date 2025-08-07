# Adjust these paths before running
$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$sourcePath = "C:\Users\richa\OneDrive\Documents"
$destinationZip = "C:\Backup\Documents_Trimmed_$timestamp.7z"
$sevenZip = "C:\Program Files\7-Zip\7z.exe"
$excludeFile = "C:\Backup\exclude.txt"
$logFile = "C:\Backup\Documents_Backup_Log_$timestamp.txt"
$errorLogFile = "C:\Backup\Documents_Backup_Errors_$timestamp.txt"

# Step 1: Write exclusions to file
@"
*.mp4
*.mov
*.wav
*.png
*.jpg
*.zip
*.7z
*.exe
"@ | Out-File -Encoding ASCII $excludeFile -Force

# Step 2: Run 7-Zip with full logging and capture errors separately
try {
    & $sevenZip a -t7z $destinationZip "$sourcePath\*" -r -mx9 -xr@"$excludeFile" 2>&1 | Tee-Object -FilePath $logFile -Encoding UTF8
    Write-Host "`n✅ Archive completed. Check size at: $destinationZip"
    Write-Host "📄 Log saved to: $logFile"
} catch {
    $_ | Out-File -FilePath $errorLogFile -Encoding UTF8 -Append
    Write-Host "❌ Errors occurred. See: $errorLogFile"
}
