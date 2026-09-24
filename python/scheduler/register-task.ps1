# =====================================================================
# 菜价雷达 · 调度进程注册为 Windows 计划任务（用户级, 无需管理员）
# 作用: 登录时自动启动采集调度进程; 异常退出按策略重试
# 用法: 在 PowerShell 中执行:
#         powershell -ExecutionPolicy Bypass -File python\scheduler\register-task.ps1
# 卸载: Unregister-ScheduledTask -TaskName "AgriPriceRadar-Scheduler"
# 立即启动: Start-ScheduledTask -TaskName "AgriPriceRadar-Scheduler"
# =====================================================================

$ErrorActionPreference = 'Stop'
$taskName = 'AgriPriceRadar-Scheduler'
$batPath = Join-Path $PSScriptRoot 'start-scheduler.bat'

if (-not (Test-Path $batPath)) {
    Write-Error "未找到启动脚本: $batPath"
    exit 1
}

# 工作目录: 项目根(python/scheduler 的上两级)
$projectDir = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path

Write-Host "[菜价雷达] 注册计划任务: $taskName" -ForegroundColor Cyan
Write-Host "  启动脚本: $batPath"
Write-Host "  工作目录: $projectDir"

$action = New-ScheduledTaskAction -Execute $batPath -WorkingDirectory $projectDir
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 5) `
    -ExecutionTimeLimit ([TimeSpan]::Zero)

Register-ScheduledTask -TaskName $taskName `
    -Action $action -Trigger $trigger -Settings $settings `
    -Description '菜价雷达采集调度进程(APScheduler): 每日08/14/20点增量采集, 21点预测预计算' `
    -Force | Out-Null

Write-Host "[菜价雷达] 注册成功。" -ForegroundColor Green
Write-Host "  查询状态: Get-ScheduledTask -TaskName '$taskName' | Get-ScheduledTaskInfo"
Write-Host "  立即启动: Start-ScheduledTask -TaskName '$taskName'"
Write-Host "  卸载任务: Unregister-ScheduledTask -TaskName '$taskName'"
