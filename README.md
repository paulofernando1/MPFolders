# 📂 MPFolders (v1.0)
> **Workflow & Projetos** — Ferramenta portátil integrada para automação, organização estrutural e backup seguro.

---

## 🌟 Visão Geral

O **MPFolders** é uma ferramenta de produtividade desenvolvida em Python e Tkinter para otimizar o fluxo de trabalho diário de profissionais e empresas que lidam com múltiplos projetos estruturados. A ferramenta consolida três grandes rotinas em abas funcionais dinâmicas:

1. 🏗️ **Criador de Projetos**: Criação automatizada de árvores estruturadas de pastas com suporte a modelos reutilizáveis (templates).
2. 🧹 **Limpador Seguro**: Identificação e exclusão segura de arquivos temporários inúteis e pastas vazias recursivamente.
3. 🛡️ **Backup Incremental**: Motor robusto de sincronização que utiliza o comando nativo **Windows Robocopy** para backups rápidos de alteração única.

---

## ✨ Recursos & Diferenciais

- 🎨 **Interface Premium Dark Mode**: Design refinado construído sobre o tema `clam` do Tkinter, com botões de cantos arredondados, contrastes balanceados e ícones simplificados (`+` e `X`).
- ↔️ **Responsividade Dinâmica com Divisores Físicos**: Uso de `tk.PanedWindow` com delimitadores visuais cinzas e botões físicos de arraste (sash handles).
- 💾 **Persistência de Sessão Avançada**: A ferramenta salva automaticamente no arquivo `config_gerenciador.json`:
  - A última geometria de janela utilizada (dimensões e posição na tela).
  - A posição exata de cada divisor de painel em todas as abas.
  - O último modelo de pastas (template) ativo.
- ⚙️ **Campos Inteligentes**: A estrutura de pastas pode ser gerada dinamicamente informando o Ano/Mês/Dia, Cliente e Nome do Projeto, ou criada diretamente na raiz de destino se os campos de identificação forem deixados em branco.
- 🔄 **Integração Dropbox Safe**: Rotinas de build configuradas para compilar em diretórios temporários externos, contornando travas de sincronização de arquivos.

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
- 💻 **Build macOS**: O arquivo `.github/workflows/build-mac.yml` roda em agentes `macos-latest` para gerar e assinar automaticamente o aplicativo empacotado `Silent_Guardian.app` (ZIP) via PyInstaller a cada nova modificação na branch principal (`main`/`master`).

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
