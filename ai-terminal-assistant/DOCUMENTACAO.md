# AI Terminal Assistant - Documentação do Código

## Visão Geral

O **AI Terminal Assistant** é um assistente de linha de comando (CLI) seguro que utiliza inteligência artificial para realizar operações no sistema de arquivos. O sistema foi projetado para executar operações como leitura, escrita, renomeação e exclusão de arquivos de forma controlada, com múltiplos níveis de segurança e confirmação do usuário.

---

## Arquitetura do Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                        main.py                               │
│                    (Ponto de Entrada)                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      src/cli.py                              │
│            (Interface Interativa com o Usuário)              │
│         • Prompt ToolKit + Rich (UI rica e colorida)        │
│         • Comandos especiais (/help, /status, /mode)        │
│         • Exibição formatada de resultados                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     src/router.py                            │
│                 (Orquestrador Principal)                     │
│    • Gerencia fluxo entre componentes                        │
│    • Mantém histórico de conversação                         │
│    • Log de auditoria                                        │
└─────────────────────────────────────────────────────────────┘
           │                    │                    │
           ▼                    ▼                    ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  src/ai_adapter  │  │ src/security.py  │  │src/fs_executor.py│
│   (Comunicação   │  │  (Validação e    │  │ (Execução Segura │
│     com IA)      │  │   Políticas)     │  │   de Operações)  │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

---

## Estrutura de Arquivos

```
ai-terminal-assistant/
├── main.py                 # Ponto de entrada da aplicação
├── config.yaml             # Arquivo de configuração YAML
├── requirements.txt        # Dependências do projeto
├── README.md               # Documentação geral
├── src/
│   ├── __init__.py         # Pacote Python
│   ├── cli.py              # Interface de linha de comando
│   ├── config.py           # Gerenciamento de configuração
│   ├── models.py           # Modelos de dados (Pydantic)
│   ├── router.py           # Orquestrador principal
│   ├── security.py         # Motor de segurança
│   ├── fs_executor.py      # Executor de operações de arquivo
│   └── ai_adapter.py       # Adaptadores para provedores de IA
├── workspace/              # Diretório padrão para operações
│   └── test_hello.py
└── logs/                   # Logs de auditoria (gerado automaticamente)
```

---

## Módulos e Componentes

### 1. `main.py` - Ponto de Entrada

**Responsabilidade:** Inicializar e executar a aplicação.

**Funcionalidades:**
- Adiciona o diretório `src` ao path de imports
- Executa o loop assíncrono principal
- Captura exceções globais (KeyboardInterrupt, Exception)

**Código Chave:**
```python
if __name__ == '__main__':
    asyncio.run(main())
```

---

### 2. `src/config.py` - Gerenciamento de Configuração

**Responsabilidade:** Carregar e validar configurações do sistema.

**Classes Principais:**

#### `ModelConfig`
Configuração do modelo de IA:
- `provider`: Provedor (ollama, openai, anthropic)
- `name`: Nome do modelo
- `api_base`: URL base da API
- `temperature`: Criatividade das respostas (0-2)
- `max_tokens`: Limite de tokens na resposta

#### `SecurityConfig`
Políticas de segurança:
- `mode`: Modo de operação (dry_run, interactive, scoped_auto)
- `allowed_root`: Diretório raiz permitido para operações
- `max_file_size_mb`: Tamanho máximo de arquivo (MB)
- `blocked_paths`: Diretórios bloqueados (.git, .venv, etc.)
- `allowed_extensions`: Extensões permitidas (opcional)

#### `UIConfig`
Configuração da interface:
- `theme`: Tema (dark/light)
- `show_diffs`: Mostrar diferenças antes de aplicar mudanças
- `history_path`: Caminho do histórico de comandos
- `syntax_highlighting`: Habilitar highlighting de sintaxe

#### `LoggingConfig`
Configuração de logs:
- `level`: Nível de logging (INFO, DEBUG, etc.)
- `audit_path`: Caminho do log de auditoria (JSONL)
- `structured`: Usar logging estruturado

#### `Config` (Classe Principal)
- Validação automática com Pydantic
- Carregamento de arquivo YAML
- Override por variáveis de ambiente
- Método `get_api_key()`: Recupera chave API do ambiente

**Variáveis de Ambiente Suportadas:**
- `AI_MODEL_PROVIDER`
- `AI_MODEL_NAME`
- `AI_API_BASE`
- `AI_SECURITY_MODE`
- `AI_ALLOWED_ROOT`

---

### 3. `src/models.py` - Modelos de Dados

**Responsabilidade:** Definir estruturas de dados validadas com Pydantic.

#### `ActionType` (Enum)
Tipos de operações suportadas:
- `READ_FILE`: Ler conteúdo de arquivo
- `WRITE_FILE`: Criar ou sobrescrever arquivo
- `APPEND_FILE`: Adicionar conteúdo ao final
- `RENAME_FILE`: Renomear/mover arquivo
- `DELETE_FILE`: Excluir arquivo
- `LIST_DIR`: Listar conteúdo de diretório

#### `Action`
Representa uma operação proposta pela IA:
```python
{
    "type": ActionType,
    "path": str,              # Relativo ao workspace
    "content": Optional[str], # Para write/append
    "reason": Optional[str],  # Explicação da ação
    "new_path": Optional[str],# Para rename
    "max_depth": Optional[int]# Para list_dir
}
```

**Validações:**
- Previne path traversal (`..`)
- Bloqueia paths absolutos
- Valida `new_path` para operações de renomeação

#### `AIResponse`
Resposta estruturada da IA:
```python
{
    "thought": str,           # Raciocínio da IA
    "actions": List[Action]   # Lista de ações propostas
}
```

#### `SecurityMode` (Enum)
- `DRY_RUN`: Mostra o que aconteceria sem executar
- `INTERACTIVE`: Requer confirmação para cada ação
- `SCOPED_AUTO`: Auto-executa leituras, confirma escritas/exclusões

#### `OperationResult`
Resultado de uma operação:
```python
{
    "success": bool,
    "action_type": ActionType,
    "path": str,
    "message": str,
    "content": Optional[str],      # Conteúdo lido
    "backup_path": Optional[str],  # Caminho do backup
    "error": Optional[str]
}
```

#### `AuditLogEntry`
Entrada para log de auditoria:
```python
{
    "timestamp": str,
    "session_id": str,
    "prompt_hash": str,
    "action_type": Optional[ActionType],
    "path": Optional[str],
    "status": Literal["pending", "approved", "denied", "executed", "failed"],
    "message": str,
    "metadata": dict
}
```

---

### 4. `src/security.py` - Motor de Segurança

**Responsabilidade:** Validar ações e aplicar políticas de segurança.

#### Métodos Principais:

##### `resolve_path(relative_path: str) -> Path`
- Resolve caminho relativo para absoluto
- Previne ataques de path traversal
- Verifica se o caminho resolvido está dentro do `allowed_root`

##### `validate_action(action: Action) -> Tuple[bool, str]`
Validações realizadas:
1. ✅ Path traversal no caminho base
2. ✅ Diretórios bloqueados (.git, .venv, etc.)
3. ✅ Extensão de arquivo (se allowlist configurada)
4. ✅ Path traversal no destino (para rename)
5. ✅ Tamanho do conteúdo (para write/append)
6. ✅ Existência do arquivo (para read, delete, rename)

##### `check_mode_permission(action: Action) -> bool`
Verifica se a ação é permitida no modo atual:
- **DRY_RUN**: Todas permitidas (não executa)
- **INTERACTIVE**: Todas permitidas (requer confirmação)
- **SCOPED_AUTO**: Apenas leitura é automática

##### `requires_confirmation(action: Action) -> bool`
Determina necessidade de confirmação:
- **DRY_RUN**: ❌ Não requer
- **INTERACTIVE**: ✅ Sempre requer
- **SCOPED_AUTO**: ✅ Requer para não-leituras

##### `generate_backup_path(file_path: Path) -> Path`
Gera caminho de backup com timestamp:
```
arquivo.txt → arquivo.txt.bak.20240115_143022
```

---

### 5. `src/fs_executor.py` - Executor de Sistema de Arquivos

**Responsabilidade:** Executar operações de arquivo com segurança.

#### Métodos de Execução:

##### `_read_file(path, relative_path)`
- Verifica tamanho do arquivo
- Tenta múltiplas codificações (utf-8, latin-1, cp1252)
- Retorna conteúdo completo

##### `_write_file(path, content, relative_path)`
- **Cria backup automático** se arquivo existir
- Cria diretórios pais se necessário
- Rollback em caso de falha (restaura backup)

##### `_append_file(path, content, relative_path)`
- Cria backup antes de modificar
- Abre em modo append ('a')

##### `_delete_file(path, relative_path)`
- **Nunca exclui permanentemente**
- Cria backup antes de deletar
- Backup serve como "lixeira"

##### `_rename_file(path, new_path_str, relative_path)`
- Move arquivo usando `shutil.move`
- Cria diretórios pais se necessário

##### `_list_dir(path, relative_path, max_depth)`
- Listagem recursiva com profundidade controlada
- Formatação hierárquica com indentação
- Mostra tipo (DIR/FILE) e tamanho

#### Tratamento de Erros:
- Validação prévia da ação
- Try-catch em todas as operações
- Rollback automático quando possível
- Mensagens de erro descritivas

---

### 6. `src/ai_adapter.py` - Adaptadores de IA

**Responsabilidade:** Abstrair comunicação com diferentes provedores de IA.

#### Arquitetura:

```
BaseAIAdapter (Abstract Base Class)
    ├── OllamaAdapter
    ├── OpenAIAdapter
    └── AnthropicAdapter
```

#### `BaseAIAdapter`
Classe abstrata com:
- `chat(messages, system_prompt)`: Método abstrato
- `parse_response(response_text)`: Parser JSON comum

**Parser Inteligente:**
- Extrai JSON mesmo com texto adicional
- Fallback para resposta vazia em caso de erro
- Usa Pydantic para validação

#### `OllamaAdapter`
Para modelos locais Ollama:
- Endpoint: `/api/chat` (novo) ou `/api/generate` (legado)
- Modelo padrão: `qwen2.5:1.5b`
- Timeout: 120 segundos
- Detecta automaticamente versão da API

**Payload Exemplo:**
```json
{
    "model": "qwen2.5:1.5b",
    "messages": [
        {"role": "system", "content": "..."},
        {"role": "user", "content": "..."}
    ],
    "stream": false,
    "options": {
        "temperature": 0.7
    }
}
```

#### `OpenAIAdapter`
Para OpenAI e APIs compatíveis:
- Endpoint: `/v1/chat/completions`
- Modelo padrão: `gpt-3.5-turbo`
- Header: `Authorization: Bearer <API_KEY>`

#### `AnthropicAdapter`
Para Claude (Anthropic):
- Endpoint: `/v1/messages`
- Modelo padrão: `claude-3-sonnet-20240229`
- Formato específico de mensagens
- System prompt separado

#### `create_adapter(provider, **kwargs)`
Factory function que retorna o adapter apropriado.

---

### 7. `src/router.py` - Orquestrador Principal

**Responsabilidade:** Coordenar fluxo entre todos os componentes.

#### Ciclo de Processamento:

```
1. Recebe prompt do usuário
         ↓
2. Gera hash do prompt (auditoria)
         ↓
3. Registra no log de auditoria (status: pending)
         ↓
4. Adiciona ao histórico de conversação
         ↓
5. Envia para IA (via ai_adapter)
         ↓
6. Parseia resposta (AIResponse)
         ↓
7. Para cada ação:
   ├── Valida (security_engine)
   ├── Se inválida → Registra como "denied"
   └── Se válida:
       ├── Requer confirmação? → status: pending_confirmation
       └── Não requer → Executa (fs_executor)
         ↓
8. Registra resultados no log
         ↓
9. Retorna resultado para CLI
```

#### Métodos Principais:

##### `process_prompt(prompt: str) -> Dict`
Fluxo completo de processamento:
- Hash SHA256 do prompt
- Histórico limitado a 10 mensagens
- Validação e execução em lote
- Log detalhado de cada etapa

##### `confirm_action(action_data: Dict, confirmed: bool) -> Dict`
Processa confirmação do usuário:
- Se negado: registra como "denied"
- Se aprovado: executa e registra como "executed"

##### `get_context_summary() -> Dict`
Retorna resumo da sessão:
- Session ID
- Contagem de mensagens
- Configurações de segurança

##### `clear_history()`
Limpa histórico de conversação e registra no log.

#### System Prompt
Prompt especial enviado à IA definindo:
- Regras de comportamento
- Formato de resposta esperado (JSON)
- Tipos de ações disponíveis
- Restrições de path
- Diretrizes de idioma (responde no idioma do usuário)

---

### 8. `src/cli.py` - Interface de Linha de Comando

**Responsabilidade:** Interface interativa com o usuário.

#### Tecnologias:
- **Prompt Toolkit**: Input avançado com histórico e auto-complete
- **Rich**: Formatação rica (cores, painéis, tabelas, markdown)

#### `CLIInterface`

##### Componentes:
- `router`: Instância do Router
- `console`: Console Rich
- `session`: Sessão Prompt Toolkit
- `style`: Estilo customizado (cores para prompts, erros, sucesso)

##### Comandos Especiais:
| Comando | Descrição |
|---------|-----------|
| `/help` | Mostra ajuda |
| `/status` | Status da sessão |
| `/mode <mode>` | Muda modo de segurança |
| `/clear` | Limpa histórico |
| `/quit`, `/exit`, `/q` | Sai da aplicação |

##### Métodos de Exibição:

###### `print_header()`
Cabeçalho com:
- Nome da aplicação
- Modo de segurança atual
- Diretório raiz permitido

###### `print_thought(thought: str)`
Exibe raciocínio da IA em painel amarelo.

###### `print_action_result(result: Dict)`
Exibe resultado com:
- Ícone baseado no tipo de ação
- Cor baseada no status (verde=executado, vermelho=negado)
- Preview de conteúdo (para leitura)
- Informações de backup

###### `print_confirmation_prompt(result: Dict) -> bool`
Solicita confirmação:
- Mostra tipo e path da ação
- Preview do conteúdo (para escrita)
- Opções: `y/n/dry-run`

###### `print_status()`
Tabela com:
- Session ID
- Contagem de mensagens
- Modo de segurança
- Raiz permitida
- Tamanho máximo de arquivo

##### Key Bindings:
- `Ctrl+C`: Interrompe
- `Ctrl+D`: Toggle dry-run

##### Loop Principal (`run()`):
```python
while self.running:
    user_input = await session.prompt_async()
    await process_user_input(user_input)
```

---

## Fluxos de Trabalho

### Fluxo 1: Operação de Leitura (Modo Interactive)

```
Usuário: "Leia o arquivo config.yaml"
    ↓
CLI: Envia para Router
    ↓
Router: Envia para IA
    ↓
IA: Responde com action: READ_FILE config.yaml
    ↓
Router: Valida ação (✅ válida)
    ↓
Security: requires_confirmation? → SIM (modo interactive)
    ↓
CLI: Mostra prompt de confirmação
    ↓
Usuário: "y"
    ↓
Router: confirm_action() → fs_executor.execute()
    ↓
FS_Executor: Lê arquivo
    ↓
CLI: Exibe conteúdo formatado
```

### Fluxo 2: Operação de Escrita (Modo Scoped_Auto)

```
Usuário: "Crie um arquivo utils.py"
    ↓
IA: Propõe WRITE_FILE utils.py
    ↓
Security: requires_confirmation? → SIM (write não é auto)
    ↓
CLI: Solicita confirmação com preview
    ↓
Usuário: "y"
    ↓
FS_Executor: 
    1. Cria backup (se existir)
    2. Cria diretórios pais
    3. Escreve conteúdo
    ↓
CLI: Exibe resultado + caminho do backup
```

### Fluxo 3: Operação Negada por Segurança

```
Usuário: "Delete ../secret.txt"
    ↓
IA: Propõe DELETE_FILE ../secret.txt
    ↓
Security: validate_action()
    ❌ Path traversal detectado
    ↓
Router: Registra como "denied"
    ↓
CLI: Exibe erro: "Path traversal detected"
```

---

## Modos de Segurança

### 1. Dry Run (`dry_run`)
- **Objetivo:** Testar sem risco
- **Confirmação:** Não requer
- **Execução:** Nenhuma ação é executada
- **Uso:** Desenvolvimento, testes, demonstração

### 2. Interactive (`interactive`) - **Padrão**
- **Objetivo:** Controle total
- **Confirmação:** Sempre requer
- **Execução:** Apenas após confirmação explícita
- **Uso:** Produção, operações críticas

### 3. Scoped Auto (`scoped_auto`)
- **Objetivo:** Equilíbrio entre segurança e produtividade
- **Confirmação:**
  - ✅ Leituras: Automáticas
  - ❌ Escritas/Exclusões: Requerem confirmação
- **Execução:** Parcialmente automática
- **Uso:** Desenvolvimento diário

---

## Sistema de Auditoria

### Log Format (JSONL)
Cada linha é um JSON válido:

```json
{
  "timestamp": "2024-01-15T14:30:22.123456",
  "session_id": "20240115_143022",
  "prompt_hash": "abc123...",
  "action_type": "write_file",
  "path": "src/utils.py",
  "status": "executed",
  "message": "Successfully wrote file (256 bytes)",
  "metadata": {
    "type": "write_file",
    "path": "src/utils.py",
    "content": "...",
    "backup_path": "/backup/path"
  }
}
```

### Eventos Auditados:
1. Prompt recebido (pending)
2. Ação validada (approved/denied)
3. Ação executada (executed/failed)
4. Confirmação do usuário
5. Histórico limpo

---

## Recursos de Segurança

### 1. Prevenção de Path Traversal
```python
# Bloqueado:
"../secret.txt"
"/etc/passwd"
"../../.env"

# Permitido:
"src/utils.py"
"config.yaml"
"data/test.json"
```

### 2. Diretórios Bloqueados
Por padrão:
- `.git` - Repositório git
- `.venv` - Ambiente virtual
- `__pycache__` - Cache Python
- `node_modules` - Dependências Node

### 3. Limite de Tamanho
- Padrão: 50 MB
- Configurável via `max_file_size_mb`

### 4. Backups Automáticos
- Antes de qualquer modificação
- Timestamp no nome do backup
- Rollback em caso de falha

### 5. Validação de Extensão (Opcional)
```yaml
security:
  allowed_extensions:
    - ".py"
    - ".txt"
    - ".md"
    - ".yaml"
    - ".json"
```

---

## Dependências

### Principais:
| Pacote | Versão | Finalidade |
|--------|--------|------------|
| pydantic | ≥2.0.0 | Validação de dados |
| python-dotenv | ≥1.0.0 | Variáveis de ambiente |
| pyyaml | ≥6.0 | Parse YAML |
| httpx | ≥0.25.0 | Cliente HTTP assíncrono |
| rich | ≥13.0.0 | UI rica no terminal |
| prompt_toolkit | ≥3.0.0 | Interface interativa |

### Opcionais (comentados):
- `gitpython`: Integração Git para backups
- `structlog`/`loguru`: Logging avançado

---

## Exemplos de Uso

### 1. Iniciar Aplicação
```bash
python main.py
```

### 2. Comandos Básicos
```
🤖 Olá!
💭 Thought: O usuário está me saudando. Vou responder educadamente.

🤖 Leia o arquivo README.md
✓ [read_file] README.md → executed
   Successfully read file (1024 bytes)
┌─────────────────────────────────┐
│ Content                         │
│ ... conteúdo do arquivo ...     │
└─────────────────────────────────┘

🤖 Crie um arquivo teste.py
⚠️ Action requires confirmation:
   Type: write_file
   Path: teste.py
┌─────────────────────────────────┐
│ Preview                         │
│ def hello():                    │
│     print("Hello")              │
└─────────────────────────────────┘
Confirm? [y/n/dry-run]: y
   ✓ Confirmation: Successfully wrote file (32 bytes)
```

### 3. Mudar Modo de Segurança
```
🤖 /mode scoped_auto
✓ Mode changed to: scoped_auto

🤖 /status
┌────────────────────────────────┐
│ Session Status                 │
├──────────────┬─────────────────┤
│ Property     │ Value           │
├──────────────┼─────────────────┤
│ Session ID   │ 20240115_143022 │
│ Messages     │ 15              │
│ Security Mode│ scoped_auto     │
│ Allowed Root │ ./workspace     │
│ Max File Size│ 50 MB           │
└──────────────┴─────────────────┘
```

---

## Configuração Personalizada

### Exemplo config.yaml Completo:
```yaml
model:
  provider: openai
  name: gpt-4
  api_key_env: OPENAI_API_KEY
  temperature: 0.5
  max_tokens: 4096

security:
  mode: interactive
  allowed_root: ./meu-projeto
  max_file_size_mb: 100
  require_git_backup: true
  allowed_extensions:
    - ".py"
    - ".js"
    - ".ts"
    - ".md"
  blocked_paths:
    - .git
    - node_modules
    - dist
    - build

ui:
  theme: dark
  show_diffs: true
  history_path: ~/.config/ai-cli/history
  syntax_highlighting: true

logging:
  level: DEBUG
  audit_path: ./logs/audit.jsonl
  structured: true
```

### Variáveis de Ambiente:
```bash
export AI_MODEL_PROVIDER=openai
export AI_MODEL_NAME=gpt-4
export OPENAI_API_KEY=sk-...
export AI_SECURITY_MODE=interactive
export AI_ALLOWED_ROOT=./workspace
```

---

## Extensibilidade

### Adicionar Novo Provedor de IA:
```python
class MeuProvedorAdapter(BaseAIAdapter):
    async def chat(self, messages, system_prompt) -> AIResponse:
        # Implementar lógica de comunicação
        response = await self.chamar_api(...)
        return self.parse_response(response)

# Registrar no factory
def create_adapter(provider, **kwargs):
    adapters["meu_provedor"] = MeuProvedorAdapter
```

### Adicionar Novo Tipo de Ação:
```python
class ActionType(str, Enum):
    COPY_FILE = "copy_file"  # Novo tipo

# Atualizar FS_Executor
def execute(self, action):
    if action.type == ActionType.COPY_FILE:
        return self._copy_file(...)
```

---

## Considerações de Performance

### Otimizações Implementadas:
1. **Histórico Limitado:** Últimas 10 mensagens apenas
2. **Leitura Lazy:** Arquivos grandes só são lidos se confirmados
3. **Backup Sob Demanda:** Apenas quando necessário
4. **Encoding Fallback:** Tenta utf-8 primeiro, depois alternativos

### Possíveis Melhorias:
- Cache de arquivos frequentemente lidos
- Compressão de logs antigos
- Rate limiting para APIs
- Parallelização de operações independentes

---

## Troubleshooting

### Problema: Cannot connect to Ollama
**Solução:**
```bash
ollama serve
```

### Problema: Path traversal detected
**Causa:** Tentativa de acessar arquivos fora do `allowed_root`
**Solução:** Use paths relativos válidos

### Problema: File extension not allowed
**Causa:** Extensão não está na lista permitida
**Solução:** Adicione extensão ao `config.yaml` ou remova `allowed_extensions`

### Problema: Failed to parse AI response
**Causa:** IA retornou formato inválido
**Solução:** Verifique system prompt e modelo utilizado

---

## Licença e Contribuição

Este projeto é open-source. Contribuições são bem-vindas!

### Áreas para Contribuição:
- [ ] Suporte a mais provedores de IA
- [ ] Integração Git completa
- [ ] Plugins para operações customizadas
- [ ] Interface web alternativa
- [ ] Testes automatizados
- [ ] Traduções

---

## Changelog

### v1.0.0 (Atual)
- ✅ Implementação inicial
- ✅ Suporte a Ollama, OpenAI, Anthropic
- ✅ 3 modos de segurança
- ✅ Sistema de auditoria completo
- ✅ Backups automáticos
- ✅ UI rica com Rich + Prompt Toolkit

---

**Documentação criada com base na análise do código fonte.**

Para mais informações, consulte o `README.md` original ou execute `/help` na aplicação.
