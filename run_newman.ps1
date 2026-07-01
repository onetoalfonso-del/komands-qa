<#
.SYNOPSIS
    Ejecuta Newman para Entel (VNO 03) y ClaroVTR (VNO 02) en paralelo.
.DESCRIPTION
    Pre-requisitos:
      npm install -g newman newman-reporter-htmlextra
    Los archivos de ambiente (.postman_environment.json) deben existir localmente
    en "collection Blueplanet/" — no están en el repositorio por contener credenciales.
.EXAMPLE
    .\run_newman.ps1
.EXAMPLE
    .\run_newman.ps1 -AccessIdEntel "03-TESTPREPROD-DIR02873675-9" -SerialEntel "SCOM13032002"
.EXAMPLE
    .\run_newman.ps1 `
        -AccessIdEntel "03-TESTPREPROD-DIR02873675-9" -SerialEntel "SCOM13032002" -SpeedEntel "940/940" `
        -AccessIdCVTR  "02-TESTPREPROD-DIR02803674-002" -SerialCVTR  "SCOM13022002" -SpeedCVTR  "600/600"
#>
param(
    [string]$AccessIdEntel = "03-TESTPREPROD-DIR02873675-8",
    [string]$SerialEntel   = "SCOM13032001",
    [string]$SpeedEntel    = "940/940",

    [string]$AccessIdCVTR  = "02-TESTPREPROD-DIR02803674-001",
    [string]$SerialCVTR    = "SCOM13022001",
    [string]$SpeedCVTR     = "600/600"
)

$ROOT = $PSScriptRoot

# Verificar pre-requisitos
if (-not (Get-Command newman -ErrorAction SilentlyContinue)) {
    Write-Error "Newman no está instalado. Ejecutar: npm install -g newman newman-reporter-htmlextra"
    exit 1
}

$envEntel = Join-Path $ROOT "collection Blueplanet\VnoB1_vnoid03 PRE.postman_environment.json"
$envCVTR  = Join-Path $ROOT "collection Blueplanet\VnoB1_vnoid02 PRE ClaroVTR.postman_environment.json"

if (-not (Test-Path $envEntel)) {
    Write-Error "No se encontró el archivo de ambiente Entel: $envEntel"
    exit 1
}
if (-not (Test-Path $envCVTR)) {
    Write-Error "No se encontró el archivo de ambiente ClaroVTR: $envCVTR"
    exit 1
}

Write-Host ""
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "  NEWMAN — Ejecucion paralela APIM PRE" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Entel    accessId : $AccessIdEntel"
Write-Host "           serial   : $SerialEntel"
Write-Host "           speed    : $SpeedEntel"
Write-Host ""
Write-Host "  ClaroVTR accessId : $AccessIdCVTR"
Write-Host "           serial   : $SerialCVTR"
Write-Host "           speed    : $SpeedCVTR"
Write-Host ""
Write-Host "  Iniciando jobs en paralelo..." -ForegroundColor Yellow
Write-Host ""

$j1 = Start-Job -ArgumentList $ROOT, $AccessIdEntel, $SerialEntel, $SpeedEntel -ScriptBlock {
    param($root, $aid, $ser, $spd)
    Set-Location $root
    newman run "collection Blueplanet/Komands — APIM PRE VNOs 02-03 Claro-Entel (Auto-Token).postman_collection.json" -e "collection Blueplanet/VnoB1_vnoid03 PRE.postman_environment.json" --env-var "accessId=$aid" --env-var "serial=$ser" --env-var "speedPlan=$spd" --insecure --reporters "cli,htmlextra" --reporter-htmlextra-export "reporte_entel_extra.html"
}

$j2 = Start-Job -ArgumentList $ROOT, $AccessIdCVTR, $SerialCVTR, $SpeedCVTR -ScriptBlock {
    param($root, $aid, $ser, $spd)
    Set-Location $root
    newman run "collection Blueplanet/Komands — APIM PRE VNOs 02-03 Claro-Entel (Auto-Token).postman_collection.json" -e "collection Blueplanet/VnoB1_vnoid02 PRE ClaroVTR.postman_environment.json" --env-var "accessId=$aid" --env-var "serial=$ser" --env-var "speedPlan=$spd" --insecure --reporters "cli,htmlextra" --reporter-htmlextra-export "reporte_clarovtr_extra.html"
}

Wait-Job $j1, $j2 | Out-Null
Receive-Job $j1, $j2
Remove-Job $j1, $j2

Write-Host ""
Write-Host "=======================================" -ForegroundColor Green
Write-Host "  Ejecucion completada." -ForegroundColor Green
Write-Host "=======================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Reportes generados en:" -ForegroundColor Green
Write-Host "    $(Join-Path $ROOT 'reporte_entel_extra.html')"
Write-Host "    $(Join-Path $ROOT 'reporte_clarovtr_extra.html')"
Write-Host ""
