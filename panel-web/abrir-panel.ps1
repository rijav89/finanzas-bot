# Abre un túnel SSH cifrado al panel y lanza el navegador.
# Uso: clic derecho -> "Ejecutar con PowerShell", o desde una terminal:
#   powershell -ExecutionPolicy Bypass -File panel-web\abrir-panel.ps1
# Ctrl+C en esta ventana cierra el túnel.

$key = "E:\Proyectos\Finanzas Bot\Keys\ssh-key-2026-08-02-backend.key"
$servidor = "ubuntu@150.136.170.92"
$puertoLocal = 8080

Write-Host "Abriendo tunel SSH a $servidor ..." -ForegroundColor Cyan
Write-Host "Panel disponible en: http://localhost:$puertoLocal" -ForegroundColor Green
Write-Host "(Ctrl+C aqui para cerrar el tunel)" -ForegroundColor DarkGray

Start-Sleep -Seconds 2
Start-Process "http://localhost:$puertoLocal"

ssh -i $key -N -L "${puertoLocal}:127.0.0.1:80" $servidor
