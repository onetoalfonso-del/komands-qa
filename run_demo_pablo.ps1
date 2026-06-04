# Demo Pablo — 4 operaciones con Mocks
# Ejecutar: clic derecho → "Run with PowerShell"

Write-Host ""
Write-Host "=== Demo Komands — 4 Operaciones con Mocks ===" -ForegroundColor Cyan
Write-Host "  1. Baja de Acceso (POST /unsuscription)"
Write-Host "  2. Estado Transaccion Baja (GET /transaction/{id}/status)"
Write-Host "  3. Consulta Acceso (GET /access/{id})"
Write-Host "  4. Cambio de Equipo (POST /device-modification)"
Write-Host ""

.venv\Scripts\pytest.exe `
    tests\api\test_deactivation.py `
    tests\api\test_queries.py `
    tests\api\test_device_modification.py `
    --no-cov `
    --html=reporte_demo_pablo.html `
    --self-contained-html `
    -v

Write-Host ""
Write-Host "Reporte generado: reporte_demo_pablo.html" -ForegroundColor Green
Write-Host "Abriendo reporte..." -ForegroundColor Green
Start-Process "reporte_demo_pablo.html"
