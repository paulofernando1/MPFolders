# 📂 MPFolders (v1.1.0)

> **Workflow & Projetos** — Ferramenta portátil integrada para automação, organização estrutural, comparação, mapeamento de rede e backup seguro.

---

## 🌟 Visão Geral

O **MPFolders** é uma ferramenta de produtividade desenvolvida em Python e Tkinter para otimizar o fluxo de trabalho diário de profissionais e empresas que lidam com múltiplos projetos estruturados. A ferramenta consolida sete grandes rotinas em abas funcionais dinâmicas:

1. 🏗️ **Pastas**: Criação automatizada de árvores estruturadas de pastas com suporte a modelos reutilizáveis (templates).
2. 🧹 **Limpar Pastas**: Identificação e exclusão segura de arquivos temporários inúteis e pastas vazias recursivamente.
3. 🛡️ **Backup**: Motor robusto de sincronização que utiliza o comando nativo **Windows Robocopy** para backups rápidos de alteração única.
4. 🏷️ **Renomeador**: Renomeação sequencial inteligente em lote por tipo/extensão, com continuação automática a partir do último arquivo existente na pasta e simulação segura (Dry-Run).
5. 🎴 **Copia do Cartão**: Extração e ingestão recursiva com flattening de árvores de gravação e câmeras com filtro de datas e resolução de conflitos.
6. 🔍 **Comparar Pastas (Diff) & Sincronização**: Varredura entre duas pastas com metadados configuráveis (**nome do arquivo/caixa**, tamanho, data de modificação, data de criação), barra de ferramentas responsiva com quebra automática de linhas (`FlowFrame`), **cópia direta com 1 clique de arquivos faltantes (A ➜ B ou B ➜ A)** com preservação de diretórios, análise de arquivos modificados com deltas de tempo e tamanho, **suporte inteligente a Cloud Folders (Dropbox, OneDrive, Google Drive) e NAS de Rede (UNC e drives mapeados)** com detecção de placeholders online-only, tratamento resiliente de travas de sincronização/rede e **exportação de relatório estruturado em Markdown (.md)**.
7. 🌐 **Unidades de Rede no Windows**: Mapeamento de pastas como unidades de rede (letras A-Z) via UNC / `net use` ou unidade virtual `subst`, **definição de rótulo/nome amigável e ícone personalizado no Windows Explorer** (com modal de diálogo interativo `DriveCustomizeDialog`, seleção de `.ico`, `.exe`, `.dll` e presets rápidos), barra de ferramentas responsiva com botões auto-ajustáveis ao texto (`FlowFrame`), opções de desconexão e **remapeamento automático no logon**.

---

## ✨ Recursos & Diferenciais

- 🎨 **Interface Premium Dark Mode**: Design refinado construído sobre o tema `clam` do Tkinter, com botões de cantos arredondados, contrastes balanceados e ícones simplificados (`+` e `X`).
- ↔️ **Responsividade Dinâmica com Divisores Físicos**: Uso de `tk.PanedWindow` com delimitadores visuais cinzas e botões físicos de arraste (sash handles).
- 📜 **Painéis com Scrollbar Vertical (ScrollablePanel)**: Painéis de parâmetros em todas as 7 abas com suporte universal a mousewheel e trackpad para resoluções compactas (720p/768p).
- 💾 **Persistência de Sessão Avançada**: A ferramenta salva automaticamente no arquivo `config_gerenciador.json`:
  - A última geometria de janela utilizada (dimensões e posição na tela).
  - A posição exata de cada divisor de painel em todas as abas (`sash_creator`, `sash_cleaner`, `sash_backup`, `sash_renamer`, `sash_card_copy`, `sash_diff`, `sash_netdrive`).
  - O último modelo de pastas (template) ativo.
- ⚙️ **Campos Inteligentes**: A estrutura de pastas pode ser gerada dinamicamente informando o Ano/Mês/Dia, Cliente e Nome do Projeto, ou criada diretamente na raiz de destino se os campos de identificação forem deixados em branco.
- 🔄 **Integração Dropbox Safe**: Rotinas de build configuradas para compilar em diretórios temporários externos, contornando travas de sincronização de arquivos.
- 📏 **Resiliência a Limites de Sistema de Arquivos (Caminhos Longos e Nomes)**:
  - **Namespace Estendido Unicode (\\?\ e \\?\UNC\)**: Elimina o limite de 260 caracteres (MAX_PATH) no Windows, permitindo copiar, comparar e ler hashes em caminhos de até 32.767 caracteres.
  - **Truncamento Seguro Preservando Extensão (	runcate_filename_safe)**: Respeita o limite físico de 255 caracteres por componente no NTFS, FAT32 e exFAT, truncando apenas o stem e mantendo rigorosamente a extensão (.ext).
  - **Previsão Antecipada de Erros de Cópia**: Alerta prévio em modais de confirmação e simulações Dry-Run sobre arquivos com caminhos longos, limites de tamanho de nome e restrições de discos FAT32.

---

## 🛠️ Instalação e Execução

### Pré-requisitos

- **Python 3.10** ou superior
- Bibliotecas nativas do Python (`tkinter`, `shutil`, `json`, `subprocess`, etc.)

### Execução em Desenvolvimento

```bash
python gerenciador_projetos_backup.py
```

### Compilação Local (Gerar Executável Portátil)

O projeto inclui scripts automatizados de build direcionados à pasta temporária local para evitar travas do Dropbox, gerando a saída final na pasta `dist/`:

- **Windows (PowerShell)**:
  ```powershell
  ./build.ps1
  ```
- **Windows (Prompt/Batch)**:
  ```cmd
  build.bat
  ```
- **Linux/Git Bash (Shell Script)**:
  ```bash
  chmod +x build.sh
  ./build.sh
  ```

---

## 🚀 Integração Contínua (GitHub Actions)

O repositório inclui suporte pronto para compilação na nuvem:

- 💻 **Build macOS**: O arquivo `.github/workflows/build-mac.yml` roda em agentes `macos-latest` para gerar e assinar automaticamente o aplicativo empacotado `MPFolders.app` (ZIP) via PyInstaller a cada nova modificação na branch principal (`main`/`master`).

---

## ⚙️ Estrutura do Arquivo de Configuração

O arquivo `config_gerenciador.json` é gerado na primeira execução na mesma pasta do executável:

```json
{
    "templates": {
        "Padrão": [
            "Cliente A/Administrativo",
            "Cliente A/Contabil",
            "Cliente A/Projetos"
        ]
    },
    "active_template": "Padrão",
    "window_geometry": "1024x768+150+100",
    "sash_creator": 410,
    "sash_cleaner": 370,
    "sash_backup": 380
}
```

---

*Paulo Fernando de M. E. @ Gandget S&P © Todos os direitos reservados.*
