# Data Model e Lógica de Negócios - MPFolders

## Visão Geral
Gerenciador de backup e projetos focado em sistema de arquivos.

## Esquema de Dados
- **Configuração (JSON)**: `config_gerenciador.json` armazena caminhos de origem, destino e regras de exclusão/inclusão de arquivos.

## Regras de Permissões
- Permissões locais do Sistema Operacional. O script requer leitura na origem e escrita no destino.

## Fluxo de Usuário
1. O usuário define as pastas de projetos no arquivo de configuração.
2. Executa a aplicação/script.
3. O sistema analisa as diferenças e realiza o backup/sincronização.
