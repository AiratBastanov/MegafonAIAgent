[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$task06Windows = @(Get-Process | Where-Object {
    $_.MainWindowTitle -like '*MegafonAIAgent*' -or $_.MainWindowTitle -like '*TASK06*'
} | Select-Object ProcessName,Id,MainWindowTitle,MainWindowHandle)
ConvertTo-Json -InputObject $task06Windows -Depth 3
