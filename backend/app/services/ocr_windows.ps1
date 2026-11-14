# Lee el texto de una imagen con el OCR que trae Windows 10/11 (Windows.Media.Ocr), en el
# idioma del sistema (español). No usa internet ni programas extra. Uso:
#   powershell -NoProfile -ExecutionPolicy Bypass -File ocr_windows.ps1 <ruta de la imagen>
# Escribe el texto en UTF-8, una línea por renglón de la imagen.
param([Parameter(Mandatory = $true)][string]$Ruta)
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType = WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]

# PowerShell no sabe esperar operaciones asíncronas de WinRT: se convierten en Task.
$comoTarea = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq "AsTask" -and $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq "IAsyncOperation``1"
} | Select-Object -First 1
function Esperar($operacion, [Type]$tipo) {
    $tarea = $comoTarea.MakeGenericMethod($tipo).Invoke($null, @($operacion))
    $tarea.Wait() | Out-Null
    $tarea.Result
}

$motor = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
if ($null -eq $motor) { exit 2 }  # Windows sin idioma de OCR instalado

$archivo = Esperar ([Windows.Storage.StorageFile]::GetFileFromPathAsync((Resolve-Path $Ruta).Path)) ([Windows.Storage.StorageFile])
$flujo = Esperar ($archivo.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
try {
    $decodificador = Esperar ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($flujo)) ([Windows.Graphics.Imaging.BitmapDecoder])
    $imagen = Esperar ($decodificador.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
    # El OCR de Windows no acepta imágenes más grandes que MaxImageDimension: se reducen.
    $maximo = [Windows.Media.Ocr.OcrEngine]::MaxImageDimension
    if ($imagen.PixelWidth -gt $maximo -or $imagen.PixelHeight -gt $maximo) {
        $escala = [Math]::Min($maximo / $imagen.PixelWidth, $maximo / $imagen.PixelHeight)
        $transformacion = New-Object Windows.Graphics.Imaging.BitmapTransform
        $transformacion.ScaledWidth = [uint32][Math]::Floor($imagen.PixelWidth * $escala)
        $transformacion.ScaledHeight = [uint32][Math]::Floor($imagen.PixelHeight * $escala)
        $imagen = Esperar ($decodificador.GetSoftwareBitmapAsync(
            [Windows.Graphics.Imaging.BitmapPixelFormat]::Bgra8, [Windows.Graphics.Imaging.BitmapAlphaMode]::Premultiplied,
            $transformacion, [Windows.Graphics.Imaging.ExifOrientationMode]::RespectExifOrientation,
            [Windows.Graphics.Imaging.ColorManagementMode]::DoNotColorManage)) ([Windows.Graphics.Imaging.SoftwareBitmap])
    }
    $resultado = Esperar ($motor.RecognizeAsync($imagen)) ([Windows.Media.Ocr.OcrResult])
    foreach ($linea in $resultado.Lines) { [Console]::Out.WriteLine($linea.Text) }
} finally {
    $flujo.Dispose()
}
