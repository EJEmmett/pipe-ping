$ErrorActionPreference = "Stop"

$command = Get-Command pipe-ping -ErrorAction SilentlyContinue
if (-not $command) {
    throw "pipe-ping was not found on PATH. Install it first with 'uv tool install pipe-ping'."
}

$action = New-ScheduledTaskAction -Execute "conhost.exe" -Argument "--headless `"$($command.Source)`" daemon"
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

Register-ScheduledTask `
    -TaskName "Pipe-Ping" `
    -Description "Pipe-Ping GitHub Actions monitor" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Force | Out-Null

Start-ScheduledTask -TaskName "Pipe-Ping"
Write-Host "Registered the Pipe-Ping task. Pipe-Ping is now running and will start each time you log in."
