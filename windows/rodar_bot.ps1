# Roda o bot no Windows. Usado pelo Agendador de Tarefas (veja o README).
#   .\windows\rodar_bot.ps1            -> coleta + alertas
#   .\windows\rodar_bot.ps1 -Resumo    -> coleta + alertas + Top 10 no Telegram
param([switch]$Resumo)

$pasta = Split-Path -Parent $PSScriptRoot
Set-Location $pasta
New-Item -ItemType Directory -Force "$pasta\logs" | Out-Null

# O token e o chat_id ficam nas variáveis de ambiente do SEU usuário (veja o README).
$env:TELEGRAM_TOKEN   = [Environment]::GetEnvironmentVariable("TELEGRAM_TOKEN", "User")
$env:TELEGRAM_CHAT_ID = [Environment]::GetEnvironmentVariable("TELEGRAM_CHAT_ID", "User")

$log = "$pasta\logs\bot_$(Get-Date -Format 'yyyy-MM-dd').log"
if ($Resumo) { python main.py --resumo *>> $log } else { python main.py *>> $log }
