# Brain - MPFolders

## Visão Geral da Arquitetura
- **Aplicação**: MPFolders (v1.1)
- **Linguagem/Framework**: Python 3.10+ / Tkinter com tema customizado (Silent Guardian Theme).
- **Persistência**: `config_gerenciador.json` salva templates, posições de sash (`sash_creator`, `sash_cleaner`, `sash_backup`, `sash_renamer`) e geometria da janela.

## Módulos e Abas
1. **Criador de Projetos**: Geração de estrutura hierárquica de pastas.
2. **Limpador Seguro**: Varredura recursiva e remoção de arquivos temporários e pastas vazias com opção de bypass.
3. **Backup Incremental**: Interface Tkinter sobre Robocopy com estatísticas e verificação de espaço.
4. **Renomeador Incremental**: Renomeação sequencial em lote filtrando por extensões (Imagens, Vídeos, Áudios, Documentos e personalizadas).
   - **Continuação Automática**: Detecta arquivos existentes com a nomenclatura base (ex: `Foto_005.jpg`), identificando o maior índice existente e continuando o incremento a partir do próximo número.
   - **Tratamento de Colisões/Erros**: Operação em duas fases usando nomes temporários únicos (`uuid`) para evitar sobrescritas acidentais; tratamento gracioso de `PermissionError` (arquivos travados/em uso).
   - **Simulação (Dry-Run)**: Pré-visualização completa antes da execução no disco.
