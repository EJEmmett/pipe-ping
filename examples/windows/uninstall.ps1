$ErrorActionPreference = "Stop"

Stop-ScheduledTask -TaskName "Pipe-Ping" -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName "Pipe-Ping" -Confirm:$false
Write-Host "Removed the Pipe-Ping background task."
