# Configura o Telegram do bot:
#  1. pede o token do @BotFather (digitado escondido)
#  2. descobre o seu chat_id (mande um "oi" para o bot antes)
#  3. grava TELEGRAM_TOKEN e TELEGRAM_CHAT_ID nos Secrets do GitHub e nas variáveis do Windows
#  4. manda uma mensagem de teste
$ErrorActionPreference = "Stop"
$gh = "C:\Program Files\GitHub CLI\gh.exe"
Set-Location (Split-Path -Parent $PSScriptRoot)

$seguro = Read-Host "Cole o token do @BotFather e aperte Enter (nao aparece na tela)" -AsSecureString
$token = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($seguro)).Trim()

try { $eu = Invoke-RestMethod "https://api.telegram.org/bot$token/getMe" }
catch { Write-Host "Token invalido. Confira e rode de novo." -ForegroundColor Red; exit 1 }
Write-Host "Token OK: bot @$($eu.result.username)" -ForegroundColor Green

$upd = Invoke-RestMethod "https://api.telegram.org/bot$token/getUpdates"
$chat = ($upd.result | ForEach-Object { $_.message.chat.id } | Where-Object { $_ } | Select-Object -Last 1)
if (-not $chat) {
    Write-Host "Nao achei mensagens. Abra o Telegram, mande 'oi' para @$($eu.result.username) e rode de novo." -ForegroundColor Yellow
    exit 1
}
Write-Host "chat_id encontrado." -ForegroundColor Green

$token | & $gh secret set TELEGRAM_TOKEN
"$chat" | & $gh secret set TELEGRAM_CHAT_ID
[Environment]::SetEnvironmentVariable("TELEGRAM_TOKEN", $token, "User")
[Environment]::SetEnvironmentVariable("TELEGRAM_CHAT_ID", "$chat", "User")
Write-Host "Secrets do GitHub e variaveis do Windows gravados." -ForegroundColor Green

$texto = "✅ Bot de vagas de IA configurado! Voce vai receber o Top 10 todo dia as 17h."
Invoke-RestMethod "https://api.telegram.org/bot$token/sendMessage" -Method Post -Body @{ chat_id = $chat; text = $texto } | Out-Null
Write-Host "Mensagem de teste enviada. Confira o Telegram. Pode fechar esta aba." -ForegroundColor Green
