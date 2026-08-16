# Script personalizado para reanudar Claude Code en Windows (Sin confirmaciones)
Clear-Host
Write-Host "=== PROGRAMADOR DE CLAUDE CODE PARA WINDOWS ===" -ForegroundColor Cyan

# Definir la hora exacta de inicio (Hoy a las 02:02 AM)
$HoraDeInicio = (Get-Date).Date.AddHours(2).AddMinutes(2)
Write-Host "Esperando en segundo plano hasta las: $HoraDeInicio" -ForegroundColor Yellow

# Bucle de espera
while ((Get-Date) -lt $HoraDeInicio) {
    $TiempoRestante = $HoraDeInicio - (Get-Date)
    Write-Progress -Activity "Esperando renovación de límite de Claude Pro" -Status "Faltan: $($TiempoRestante.ToString('mm\:ss'))"
    Start-Sleep -Seconds 10
}

Write-Host "`n[!] Límite renovado. Iniciando Claude Code..." -ForegroundColor Green

# 1. Lee tus instrucciones del archivo txt
$Prompt = Get-Content -Path ".\instrucciones.txt" -Raw

# 2. Ejecuta Claude inyectando la respuesta "Y" (Yes) automáticamente mediante tubería 
# y usando la bandera --yes para forzar la auto-aprobación de lectura/escritura de archivos.
"y" | claude -p $Prompt --yes

Write-Host "`n=== Tarea completada con éxito ===" -ForegroundColor Green
