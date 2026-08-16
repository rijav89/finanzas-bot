# Abre un túnel SSH cifrado al panel y lanza el navegador.
#
# Uso normal (solo esta PC):
#   powershell -ExecutionPolicy Bypass -File panel-web\abrir-panel.ps1
#
# Para entrar también desde el celular u otro equipo de la red:
#   powershell -ExecutionPolicy Bypass -File panel-web\abrir-panel.ps1 -Lan
#   (requiere haber creado una vez la regla de firewall; el script la indica)
#
# Ctrl+C en esta ventana cierra el túnel.

param([switch]$Lan)

$key = "E:\Proyectos\Finanzas Bot\Keys\ssh-key-2026-08-02-backend.key"
$servidor = "ubuntu@150.136.170.92"
$puertoLocal = 8080

# En modo LAN el túnel escucha en todas las interfaces; si no, solo en loopback.
$bind = if ($Lan) { "0.0.0.0:${puertoLocal}" } else { "${puertoLocal}" }

Write-Host "Abriendo tunel SSH a $servidor ..." -ForegroundColor Cyan
Write-Host "Panel disponible en: http://localhost:$puertoLocal" -ForegroundColor Green

if ($Lan) {
    $ip = (Get-NetIPAddress -AddressFamily IPv4 |
        Where-Object { $_.IPAddress -notmatch '^(127\.|169\.254\.)' } |
        Select-Object -First 1).IPAddress
    Write-Host "Desde otros equipos de la red: http://${ip}:$puertoLocal" -ForegroundColor Green

    $regla = Get-NetFirewallRule -DisplayName "FinanzasBot Panel (LAN 8080)" -ErrorAction SilentlyContinue
    if (-not $regla) {
        Write-Host ""
        Write-Host "FALTA la regla de firewall. Abre PowerShell COMO ADMINISTRADOR y ejecuta:" -ForegroundColor Yellow
        Write-Host '  New-NetFirewallRule -DisplayName "FinanzasBot Panel (LAN 8080)" -Direction Inbound -LocalPort 8080 -Protocol TCP -Action Allow -Profile Any -RemoteAddress LocalSubnet' -ForegroundColor DarkYellow
        Write-Host ""
    }
    Write-Host "OJO: el tramo equipo->PC va en HTTP plano (sin cifrar)." -ForegroundColor DarkYellow
    Write-Host "Usalo solo en una red de confianza; con dominio y HTTPS (F6) deja de hacer falta." -ForegroundColor DarkYellow
}

Write-Host "(Ctrl+C aqui para cerrar el tunel)" -ForegroundColor DarkGray

Start-Sleep -Seconds 2
Start-Process "http://localhost:$puertoLocal"

ssh -i $key -N -L "${bind}:127.0.0.1:80" -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 $servidor
