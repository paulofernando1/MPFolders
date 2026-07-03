#!/bin/bash
# ==============================================================================
# Script de Build para o Silent Guardian (Gerenciador de Projetos)
# Evita locks de arquivo do Dropbox compilando em uma pasta temporária externa.
# ==============================================================================

PROJECT_NAME="Silent_Guardian"
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
)

if [ "$HAS_ICON" = true ]; then
    PYINSTALLER_ARGS+=("--icon=$ICON_FILE")
    # Adiciona o ícone dentro do executável para ser acessível via sys._MEIPASS
    PYINSTALLER_ARGS+=("--add-data=$ICON_FILE:.") # No Linux/Bash usa dois pontos (:) como separador de path ou ponto-e-vírgula (;) no Windows, mas como é bash no windows (Git bash), pyinstaller converte. O ideal cross-platform é detectar o OS, mas o pyinstaller prefere ; no windows e : no linux. Vamos usar o padrão baseado no OS hospedeiro: se for MSYS/Cygwin (Git Bash), ainda é Windows. 
    # Para garantir compatibilidade com PyInstaller rodando no Python de Windows via Git Bash, usamos o separador da plataforma:
    
    if [[ "$OSTYPE" == "msys"* ]] || [[ "$OSTYPE" == "cygwin"* ]]; then
        # Git bash no Windows
        PYINSTALLER_ARGS+=("--add-data=$ICON_FILE;.")
    else
        # Bash no Linux real/macOS
        PYINSTALLER_ARGS+=("--add-data=$ICON_FILE:.")
    fi
fi

# Chama o PyInstaller
python -m PyInstaller "${PYINSTALLER_ARGS[@]}" "$SOURCE_FILE"

# 4. Retornar executável para o Dropbox
echo -e "\e[36mMovendo executável gerado de volta para o workspace...\e[0m"
cd "$WORKSPACE_DIR" || exit 1

# O executável no Windows terá extensão .exe, no Linux não terá extensão.
if [ -f "$TEMP_BUILD_DIR/dist/${PROJECT_NAME}.exe" ]; then
    EXE_FILE="${PROJECT_NAME}.exe"
elif [ -f "$TEMP_BUILD_DIR/dist/${PROJECT_NAME}" ]; then
    EXE_FILE="${PROJECT_NAME}"
else
    EXE_FILE=""
fi

if [ -n "$EXE_FILE" ]; then
    mkdir -p "$WORKSPACE_DIR/dist"
    cp -f "$TEMP_BUILD_DIR/dist/$EXE_FILE" "$WORKSPACE_DIR/dist/"
    echo -e "\e[32mSucesso! Executável gerado: $WORKSPACE_DIR/dist/$EXE_FILE\e[0m"
else
    echo -e "\e[31mERRO: O executável não foi encontrado. Falha no PyInstaller.\e[0m"
fi

# 5. Limpeza
echo "Limpando diretório temporário..."
rm -rf "$TEMP_BUILD_DIR"
echo -e "\e[36mBuild finalizado.\e[0m"
