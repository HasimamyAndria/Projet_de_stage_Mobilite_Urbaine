# Backup PostGIS minimal (Docker Compose) — PowerShell
# Usage :
#   .\scripts\backup_postgis.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$OutDir = Join-Path $Root "backups"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$Stamp = Get-Date -Format "yyyyMMdd_HHmm"
$Out = Join-Path $OutDir "mobilite_$Stamp.dump"
$DbName = if ($env:DB_NAME) { $env:DB_NAME } else { "mobilite" }
$DbUser = if ($env:DB_USER) { $env:DB_USER } else { "mobilite" }
$Compose = Join-Path $Root "docker-compose.yml"

Write-Host "Backup -> $Out"
docker compose -f $Compose exec -T db `
  pg_dump -U $DbUser -d $DbName -Fc -f /tmp/mobilite_backup.dump
docker compose -f $Compose cp "db:/tmp/mobilite_backup.dump" $Out

Write-Host "OK : $Out"
