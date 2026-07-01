<#
.SYNOPSIS
    Ejecuta la suite de seguridad T7 contra el servidor DEV KOMANDs.
.DESCRIPTION
    Pre-requisitos:
      npm install -g newman newman-reporter-htmlextra
    Apunta a https://onf-komands.cl:9016 usando el entorno DEV.
.EXAMPLE
    cd "collection Kommand"
    .\run-security-tests.ps1
.EXAMPLE
    .\run-security-tests.ps1 -OltId "NCOR_OLT_3_1_1_3"
#>
param(
    [string]$OltId = "NCOR_OLT_3_1_1_3"
)

$ROOT = $PSScriptRoot

if (-not (Get-Command newman -ErrorAction SilentlyContinue)) {
    Write-Error "Newman no está instalado. Ejecutar: npm install -g newman newman-reporter-htmlextra"
    exit 1
}

$collection  = Join-Path $ROOT "KOMANDs Security Tests v1.0.postman_collection.json"
$environment = Join-Path $ROOT "newman-environment-dev.json"
$template    = Join-Path $ROOT "reporte-template-es.hbs"
$reportOut   = Join-Path $ROOT "reporte_seguridad_t7.html"

if (-not (Test-Path $collection)) {
    Write-Error "Colección no encontrada: $collection"; exit 1
}
if (-not (Test-Path $environment)) {
    Write-Error "Entorno no encontrado: $environment"; exit 1
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  KOMANDs Security Tests v1.0  —  T7" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  OLT de pruebas : $OltId"
Write-Host "  Servidor DEV   : https://onf-komands.cl:9016"
Write-Host "  Reporte salida : $reportOut"
Write-Host ""

$reporterArgs = @(
    "--reporters", "cli,htmlextra",
    "--reporter-htmlextra-export", $reportOut,
    "--reporter-htmlextra-title", "KOMANDs Security Tests T7",
    "--reporter-htmlextra-browserTitle", "KOMANDs Security T7"
)

if (Test-Path $template) {
    $reporterArgs += "--reporter-htmlextra-template"
    $reporterArgs += $template
}

newman run $collection `
    -e $environment `
    --env-var "test_olt_id=$OltId" `
    --insecure `
    @reporterArgs

$exitCode = $LASTEXITCODE

Write-Host ""
if ($exitCode -eq 0) {
    Write-Host "  TODAS LAS PRUEBAS PASARON" -ForegroundColor Green
} else {
    Write-Host "  EXISTEN PRUEBAS FALLIDAS — revisar reporte" -ForegroundColor Red
}
Write-Host "  Reporte HTML: $reportOut" -ForegroundColor Yellow
Write-Host ""

exit $exitCode
