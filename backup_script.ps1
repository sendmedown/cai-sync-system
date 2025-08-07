# Adjust these paths before running
$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$backupFolder = "C:\Backup"
if (-Not (Test-Path $backupFolder)) {
    New-Item -Path $backupFolder -ItemType Directory | Out-Null
    Write-Host "📁 Created backup directory: $backupFolder"
}

$sourcePath = "C:\Users\richa\OneDrive\Documents"
$destinationZip = "$backupFolder\Documents_Trimmed_$timestamp.7z"
$sevenZip = "C:\Program Files\7-Zip\7z.exe"
$logFile = "$backupFolder\Documents_Backup_Log_$timestamp.txt"
$errorLogFile = "$backupFolder\Documents_Backup_Errors_$timestamp.txt"

Write-Host "📂 Source Path: $sourcePath"
Write-Host "📦 Destination ZIP: $destinationZip"
Write-Host "📄 Log File: $logFile"
Write-Host "❗ Error Log: $errorLogFile"

# Step 1: Run 7-Zip without exclusions for debugging
try {
    Write-Host "🚀 Running 7-Zip command WITHOUT exclusions for verification..."
    & $sevenZip a -t7z $destinationZip "$sourcePath\*" -r -mx9
    Write-Host "`n✅ Archive completed. Check size at: $destinationZip"
} catch {
    $_ | Out-File -FilePath $errorLogFile -Encoding UTF8 -Append
    Write-Host "❌ Errors occurred. See: $errorLogFile"
}
