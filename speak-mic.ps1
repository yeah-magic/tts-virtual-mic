# -*- coding: utf-8 -*-
"""speak-mic.ps1 —— PowerShell 包装：自动找 Python 并调用 speak-mic.py

用法:
  .\speak-mic.ps1 -Text "你好"        # 说一句
  .\speak-mic.ps1 -Clipboard          # 读剪贴板
  .\speak-mic.ps1 -Text "你好" -Monitor
  .\speak-mic.ps1 -List               # 列出音频设备
"""
param(
    [string]$Text,
    [switch]$Clipboard,
    [switch]$Monitor,
    [switch]$List,
    [string]$Voice = "zh-CN-XiaoxiaoNeural",
    [string]$Rate = "+0%"
)

$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path

function Find-Python {
    $cands = @(
        (Join-Path $here '.venv\Scripts\python.exe'),
        'python.exe',
        'python3.exe',
        "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"
    )
    foreach ($c in $cands) {
        try {
            $cmd = Get-Command $c -ErrorAction SilentlyContinue
            if ($cmd) {
                # WindowsApps 的占位符不可用，跳过
                if ($cmd.Source -like '*WindowsApps*') { continue }
                return $cmd.Source
            }
        } catch { }
    }
    throw '没有找到 python，请先安装 Python 3.9+（https://www.python.org/downloads/）'
}

$py = Find-Python
$script = Join-Path $here 'speak-mic.py'

$args = @($script)
if ($Text) { $args += @('-t', $Text) }
if ($Clipboard) { $args += '-c' }
if ($Monitor) { $args += '--monitor' }
if ($List) { $args += '--list' }
$args += @('-v', $Voice, '-r', $Rate)

& $py @args
exit $LASTEXITCODE
