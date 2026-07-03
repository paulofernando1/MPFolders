<#
.SYNOPSIS
Script de Build para o Silent Guardian (Gerenciador de Projetos)
Evita locks de arquivo do Dropbox compilando em uma pasta temporária externa.
#>

$projectName = "Silent_Guardian"
$sourceFile = "gerenciador_projetos_backup.py"
$iconFile = "icon.ico"

# Diretórios
$workspaceDir = Get-Location
$tempBuildDir = Join-Path $env:TEMP "$projectName`_Build"

Write-Host "Iniciando processo de compilação segura (Fora do Dropbox)..." -ForegroundColor Cyan

# 1. Preparar Pasta Temporária
if (Test-Path $tempBuildDir) {
    Remove-Item -Path $tempBuildDir -Recurse -Force
}
New-Item -ItemType Directory -Path $tempBuildDir | Out-Null

# 2. Copiar arquivos para a pasta temporária
Write-Host "Copiando arquivos fonte para $tempBuildDir..."
Copy-Item -Path (Join-Path $workspaceDir $sourceFile) -Destination $tempBuildDir

if (Test-Path (Join-Path $workspaceDir $iconFile)) {
    Copy-Item -Path (Join-Path $workspaceDir $iconFile) -Destination $tempBuildDir
    $hasIcon = $true
    Write-Host "Ícone encontrado e copiado."
} else {
    $hasIcon = $false
    Write-Host "AVISO: Arquivo icon.ico não encontrado na pasta raiz. O executável usará o ícone padrão." -ForegroundColor Yellow
}

# 3. Executar PyInstaller
Write-Host "Iniciando PyInstaller..." -ForegroundColor Cyan
Set-Location $tempBuildDir

$pyinstallerArgs = @(
    "--noconfirm",
    "--onefile",
    "--windowed",
    "--name=$projectName"
)

if ($hasIcon) {
    $pyinstallerArgs += "--icon=$iconFile"
    # Adiciona o ícone dentro do executável para ser acessível via sys._MEIPASS em tempo de execução
    $pyinstallerArgs += "--add-data=$iconFile;."
}

# Chama o PyInstaller
python -m PyInstaller $pyinstallerArgs $sourceFile

# 4. Retornar executável para o Dropbox
Write-Host "Movendo executável gerado de volta para o workspace..." -ForegroundColor Cyan
Set-Location $workspaceDir

$distDir = Join-Path $workspaceDir "dist"
if (-not (Test-Path $distDir)) {
    New-Item -ItemType Directory -Path $distDir | Out-Null
}

$exePath = Join-Path $tempBuildDir "dist\$projectName.exe"
if (Test-Path $exePath) {
    Copy-Item -Path $exePath -Destination $distDir -Force
    Write-Host "Sucesso! Executável gerado: $(Join-Path $distDir "$projectName.exe")" -ForegroundColor Green
} else {
    Write-Host "ERRO: O executável não foi encontrado. Falha no PyInstaller." -ForegroundColor Red
}

# 5. Limpeza
Write-Host "Limpando diretório temporário..."
Remove-Item -Path $tempBuildDir -Recurse -Force
Write-Host "Build finalizado." -ForegroundColor Cyan
