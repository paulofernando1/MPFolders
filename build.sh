#!/bin/bash
# ==============================================================================
# Script de Build para o MPFolders (Gerenciador de Projetos)
# Evita locks de arquivo do Dropbox compilando em uma pasta temporária externa.
# ==============================================================================

PROJECT_NAME="MPFolders"
SOURCE_FILE="gerenciador_projetos_backup.py"
ICON_FILE="icon.ico"

WORKSPACE_DIR=$(pwd)
# Define o diretório temporário padrão do sistema
TEMP_BUILD_DIR="${TMPDIR:-/tmp}/${PROJECT_NAME}_Build"

echo -e "\e[36mIniciando processo de compilação segura (Fora do Dropbox)...\e[0m"

# 1. Preparar Pasta Temporária
if [ -d "$TEMP_BUILD_DIR" ]; then
    rm -rf "$TEMP_BUILD_DIR"
fi
mkdir -p "$TEMP_BUILD_DIR"

# 2. Copiar arquivos para a pasta temporária
echo "Copiando arquivos fonte para $TEMP_BUILD_DIR..."
cp "$WORKSPACE_DIR/$SOURCE_FILE" "$TEMP_BUILD_DIR/"

HAS_ICON=false
if [ -f "$WORKSPACE_DIR/$ICON_FILE" ]; then
    cp "$WORKSPACE_DIR/$ICON_FILE" "$TEMP_BUILD_DIR/"
    HAS_ICON=true
    echo "Ícone encontrado e copiado."
else
    echo -e "\e[33mAVISO: Arquivo icon.ico não encontrado na pasta raiz. O executável usará o ícone padrão.\e[0m"
fi

# 3. Executar PyInstaller
echo -e "\e[36mIniciando PyInstaller...\e[0m"
cd "$TEMP_BUILD_DIR" || exit 1

PYINSTALLER_ARGS=(
    "--noconfirm"
    "--onefile"
    "--windowed"
    "--name=$PROJECT_NAME"
    "--collect-all=tkinter"
)

if [ "$HAS_ICON" = true ]; then
    PYINSTALLER_ARGS+=("--icon=$ICON_FILE")
    # Adiciona o ícone dentro do executável para ser acessível via sys._MEIPASS
    if [[ "$OSTYPE" == "msys"* ]] || [[ "$OSTYPE" == "cygwin"* ]]; then
        # Git bash no Windows
        PYINSTALLER_ARGS+=("--add-data=$ICON_FILE;.")
    else
        # Bash no Linux real/macOS
        PYINSTALLER_ARGS+=("--add-data=$ICON_FILE:.")
    fi
fi

# Determina comando python/python3
if command -v python3 &>/dev/null; then
    PY_CMD="python3"
else
    PY_CMD="python"
fi

# Chama o PyInstaller
$PY_CMD -m PyInstaller "${PYINSTALLER_ARGS[@]}" "$SOURCE_FILE"
PYI_EXIT=$?

if [ $PYI_EXIT -ne 0 ]; then
    echo -e "\e[31mERRO: Falha durante a execução do PyInstaller (Código: $PYI_EXIT)\e[0m"
    cd "$WORKSPACE_DIR" || exit 1
    rm -rf "$TEMP_BUILD_DIR"
    exit $PYI_EXIT
fi

# 4. Retornar executável e pacotes gerados para o workspace
echo -e "\e[36mMovendo executável/app gerado de volta para o workspace...\e[0m"
cd "$WORKSPACE_DIR" || exit 1
mkdir -p "$WORKSPACE_DIR/dist"

FOUND_ANY=false

# 4.1. macOS App Bundle (.app)
if [ -d "$TEMP_BUILD_DIR/dist/${PROJECT_NAME}.app" ]; then
    echo "App Bundle (.app) detectado. Copiando..."
    cp -R "$TEMP_BUILD_DIR/dist/${PROJECT_NAME}.app" "$WORKSPACE_DIR/dist/MPFolders.app"
    
    # Assinatura ad-hoc no macOS para evitar bloqueio do Gatekeeper
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "Aplicando assinatura ad-hoc codesign no macOS..."
        codesign --force --deep --sign - "$WORKSPACE_DIR/dist/MPFolders.app" 2>/dev/null || true
    fi
    echo -e "\e[32mSucesso! App Bundle gerado: $WORKSPACE_DIR/dist/MPFolders.app\e[0m"
    FOUND_ANY=true
fi

# 4.2. Windows Executável (.exe)
if [ -f "$TEMP_BUILD_DIR/dist/${PROJECT_NAME}.exe" ]; then
    cp -f "$TEMP_BUILD_DIR/dist/${PROJECT_NAME}.exe" "$WORKSPACE_DIR/dist/MPFolders.exe"
    echo -e "\e[32mSucesso! Executável gerado: $WORKSPACE_DIR/dist/MPFolders.exe\e[0m"
    FOUND_ANY=true
fi

# 4.3. Binário Standalone Unix/Linux/macOS
if [ -f "$TEMP_BUILD_DIR/dist/${PROJECT_NAME}" ]; then
    cp -f "$TEMP_BUILD_DIR/dist/${PROJECT_NAME}" "$WORKSPACE_DIR/dist/MPFolders"
    chmod +x "$WORKSPACE_DIR/dist/MPFolders"
    echo -e "\e[32mSucesso! Binário gerado: $WORKSPACE_DIR/dist/MPFolders\e[0m"
    FOUND_ANY=true
fi

if [ "$FOUND_ANY" = false ]; then
    echo -e "\e[31mERRO: Nenhum executável ou pacote .app foi encontrado em $TEMP_BUILD_DIR/dist. Falha no PyInstaller.\e[0m"
    rm -rf "$TEMP_BUILD_DIR"
    exit 1
fi

# 5. Limpeza
echo "Limpando diretório temporário..."
rm -rf "$TEMP_BUILD_DIR"
echo -e "\e[36mBuild finalizado com sucesso.\e[0m"
