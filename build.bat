@echo off
setlocal EnableDelayedExpansion
:: ==============================================================================
:: Script de Build para o Silent Guardian (Gerenciador de Projetos)
:: Evita locks de arquivo do Dropbox compilando em uma pasta temporária externa.
:: ==============================================================================

set "PROJECT_NAME=Silent_Guardian"
set "SOURCE_FILE=gerenciador_projetos_backup.py"
set "ICON_FILE=icon.ico"

set "WORKSPACE_DIR=%CD%"
set "TEMP_BUILD_DIR=%TEMP%\%PROJECT_NAME%_Build"

echo [INFO] Iniciando processo de compilacao segura (Fora do Dropbox)...

:: 1. Preparar Pasta Temporária
if exist "%TEMP_BUILD_DIR%" (
    echo Limpando pasta temporaria anterior...
    rmdir /s /q "%TEMP_BUILD_DIR%"
)
mkdir "%TEMP_BUILD_DIR%"

:: 2. Copiar arquivos para a pasta temporária
echo Copiando arquivos fonte para %TEMP_BUILD_DIR%...
copy /y "%WORKSPACE_DIR%\%SOURCE_FILE%" "%TEMP_BUILD_DIR%\" >nul

set HAS_ICON=0
if exist "%WORKSPACE_DIR%\%ICON_FILE%" (
    copy /y "%WORKSPACE_DIR%\%ICON_FILE%" "%TEMP_BUILD_DIR%\" >nul
    set HAS_ICON=1
    echo [OK] Icone encontrado e copiado.
) else (
    echo [AVISO] Arquivo icon.ico nao encontrado na pasta raiz. O executavel usara o icone padrao.
)

:: 3. Executar PyInstaller
echo [INFO] Iniciando PyInstaller...
cd /d "%TEMP_BUILD_DIR%"

set "PYINSTALLER_ARGS=--noconfirm --onefile --windowed --name=%PROJECT_NAME%"

if !HAS_ICON! == 1 (
    set "PYINSTALLER_ARGS=%PYINSTALLER_ARGS% --icon=%ICON_FILE% --add-data=%ICON_FILE%;."
)

:: Chama o PyInstaller
python -m PyInstaller %PYINSTALLER_ARGS% "%SOURCE_FILE%"
if %ERRORLEVEL% neq 0 (
    echo [ERRO] Ocorreu uma falha durante o build com PyInstaller.
    cd /d "%WORKSPACE_DIR%"
    exit /b %ERRORLEVEL%
)

:: 4. Retornar executável para o Dropbox
echo [INFO] Movendo executavel gerado de volta para o workspace...
cd /d "%WORKSPACE_DIR%"

if not exist "%WORKSPACE_DIR%\dist" mkdir "%WORKSPACE_DIR%\dist"

if exist "%TEMP_BUILD_DIR%\dist\%PROJECT_NAME%.exe" (
    copy /y "%TEMP_BUILD_DIR%\dist\%PROJECT_NAME%.exe" "%WORKSPACE_DIR%\dist\" >nul
    echo [SUCESSO] Executavel gerado: %WORKSPACE_DIR%\dist\%PROJECT_NAME%.exe
) else (
    echo [ERRO] O executavel nao foi encontrado na pasta dist.
)

:: 5. Limpeza
echo Limpando diretorio temporario...
rmdir /s /q "%TEMP_BUILD_DIR%"
echo [INFO] Build finalizado.
pause
