# Tasks - MPFolders

## Concluídas
- [x] Implementação da aba Criador de Projetos com suporte a templates e Datepicker.
- [x] Implementação da aba Limpador Seguro com simulação e bypass de proteção.
- [x] Implementação da aba Backup Incremental com motor Robocopy.
- [x] Implementação da aba Renomeador Incremental:
  - [x] Seleção de pasta e filtro por tipo de arquivo (Imagens, Vídeos, Áudios, Documentos e personalizadas).
  - [x] Lógica incremental automática continuada a partir do último arquivo existente na pasta com a mesma nomenclatura.
  - [x] Algoritmo em duas fases para evitar colisão e sobrescrita de arquivos.
  - [x] Tratamento de erros para permissões/arquivos bloqueados (`PermissionError`).
  - [x] Modo de simulação (Dry-Run) e terminal de logs thread-safe.
  - [x] Persistência do divisor de tela (`sash_renamer`) no `config_gerenciador.json`.
  - [x] **Escrita Atômica de Configuração**: Implementada gravação resiliente em `save_config` usando arquivo temporário `.tmp` e `os.replace` para evitar truncamento ou corrupção do `config_gerenciador.json` pelo Dropbox.