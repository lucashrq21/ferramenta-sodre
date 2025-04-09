# CATALOGADOR V2 - Documentação Técnica

## Visão Geral

O CATALOGADOR V2 é uma aplicação web para análise e catalogação gráfica da "Estratégia da Minoria" com Martingale em operações de trading. A aplicação foi projetada para ser escalável, suportando múltiplos usuários simultâneos (até ~1000), com cada usuário tendo sua própria sessão isolada com a API Polarium.

## Características Principais

- **Multi-usuário**: Suporta até aproximadamente 1000 usuários simultâneos
- **Arquitetura Assíncrona**: Implementada com Flask + ASGI (Uvicorn) para não bloquear o loop de eventos
- **Gerenciamento de Sessão**: Sessões individuais para cada usuário usando Flask-Session e Redis
- **Cache**: Implementado com Redis para reduzir a carga na API
- **Isolamento de Estado**: Cada usuário tem sua própria instância da API Polarium
- **Robustez**: Recuperação automática de erros e manipulação adequada de exceções
- **Escalabilidade**: Facilmente escalável através da configuração do Nginx e Gunicorn
- **Interface Responsiva**: Versão V2 com suporte para diferentes tamanhos de tela

## Arquitetura do Sistema

A aplicação utiliza a seguinte arquitetura:

1. **Nginx**: Proxy reverso, terminação SSL, balanceamento de carga
2. **Gunicorn**: Gerenciador de processos para a aplicação Flask
3. **Uvicorn**: Servidor ASGI para execução da aplicação Flask de forma assíncrona
4. **Flask**: Framework web para a aplicação
5. **Redis**: Armazenamento para sessões e cache
6. **API Polarium**: API externa para obtenção de dados de mercado

### Fluxo de Requisições

```
Cliente Web → Nginx → Gunicorn → Uvicorn → Flask → API Polarium
```

## Estrutura do Projeto

```
CATALOGADOR_V2/
├── main.py                    # Arquivo principal de entrada da aplicação
├── estrategia_minoria.py      # Implementação principal da aplicação (catalogação e análise)
├── routes.py                  # Rotas da API e páginas web
├── connection_manager.py      # Gerenciador de conexões de usuários
├── async_utils.py             # Utilitários para operações assíncronas
├── cache_utils.py             # Utilitários para cache
├── requirements.txt           # Dependências do projeto
├── .env                       # Variáveis de ambiente (configuração)
├── .env.example               # Exemplo de configuração de variáveis de ambiente
├── nginx.conf                 # Configuração de exemplo para Nginx
├── catalogador.service        # Configuração de serviço Systemd
├── gunicorn_conf.py           # Configuração para Gunicorn
├── docs/                      # Documentação
│   └── catalogador_documentacao.md # Esta documentação
├── logs/                      # Diretório de logs
├── templates/                 # Templates HTML
│   ├── index.html             # Página principal (login e análise)
│   └── top_ativos.html        # Página de Top 5 ativos
└── polariumapi/               # Módulo da API Polarium
    ├── stable_api.py          # API estável para comunicação com Polarium
    ├── constants.py           # Constantes utilizadas pela API
    ├── global_value.py        # Valores globais
    ├── expiration.py          # Cálculos de expiração
    └── ws/                    # Componentes de WebSocket
```

## Componentes Principais

### 1. Gerenciador de Conexões (`connection_manager.py`)

Responsável por gerenciar as conexões dos usuários com a API Polarium, provendo:

- **Isolamento de conexões**: Cada usuário tem sua própria instância da API
- **Controle de concorrência**: Locks específicos para cada usuário
- **Limpeza automática**: Remoção de conexões inativas após um período configurável
- **Monitoramento de estado**: Rastreamento do estado de cada usuário (análises, resultados, progresso)

### 2. Gerenciador de Cache (`cache_utils.py`)

Implementa um sistema de cache flexível com:

- **Camada de abstração**: Funciona com Redis ou cache em memória
- **TTL configurável**: Suporte a tempos de expiração por item
- **Decorador funcional**: Permite cache fácil de funções
- **Serialização automática**: Manipula objetos Python complexos

### 3. Utilitários Assíncronos (`async_utils.py`)

Fornece funções para executar código bloqueante em threads separadas:

- **Execução em threads**: Permite operações bloqueantes sem interromper o loop de eventos
- **Timeouts configuráveis**: Evita bloqueios indefinidos
- **Gestão de recursos**: Limita o número de threads simultâneas

### 4. Estratégia da Minoria (`estrategia_minoria.py`)

Implementa a lógica principal da aplicação:

- **Análise de candles**: Processa dados de velas para identificar padrões
- **Estratégia da Minoria**: Identifica oportunidades de operação baseadas no princípio da minoria
- **Martingale**: Implementa estratégia de recuperação com Martingale até G2
- **Visualização**: Gera gráficos interativos com Plotly

### 5. Rotas da Aplicação (`routes.py`)

Define todas as rotas HTTP e WebSocket:

- **Autenticação**: Login na API Polarium com suporte a 2FA
- **Análise de ativos**: Endpoints para análise individual ou em lote
- **Ranking de ativos**: Identifica os melhores ativos para a estratégia
- **Atualização em tempo real**: Monitoramento de progresso de análises

## Tecnologias Utilizadas

### Backend
- **Python 3.7+**: Linguagem principal
- **Flask 2.2.0**: Framework web
- **Uvicorn 0.22.0**: Servidor ASGI
- **Gunicorn 20.1.0**: Servidor WSGI para produção
- **Redis 4.5.1**: Cache e gerenciamento de sessões
- **Pandas 1.4.0**: Manipulação de dados
- **Plotly 5.5.0**: Geração de gráficos

### Frontend
- **HTML5/CSS3**: Estrutura e estilo das páginas
- **JavaScript**: Interatividade do lado do cliente
- **Bootstrap**: Framework CSS responsivo
- **jQuery**: Manipulação do DOM e requisições AJAX
- **Plotly.js**: Renderização de gráficos no cliente

## Funcionalidades Principais

### 1. Autenticação

- **Login com email/senha**: Autenticação na API Polarium
- **Suporte a 2FA**: Autenticação de dois fatores quando ativada na conta
- **Sessões persistentes**: Mantém usuários logados por até 12 horas

### 2. Análise de Ativos

- **Análise individual**: Análise detalhada de ativos específicos
- **Análise em lote**: Processamento de múltiplos ativos para encontrar os melhores
- **Filtros por tipo**: Forex, criptomoedas, ações, índices, commodities

### 3. Estratégia da Minoria

- **Blocos de 5 velas**: Análise de blocos de 5 velas para identificar padrões
- **Sinal de entrada**: Identificação da direção minoritária para entrada
- **Martingale**: Até 2 níveis de martingale para recuperação
- **Resultados históricos**: Rastreamento de desempenho por ativo

### 4. Visualização de Dados

- **Gráfico de candles**: Visualização de velas com marcadores de blocos
- **Indicadores visuais**: Sinais de entrada e resultados destacados no gráfico
- **Estatísticas em tempo real**: Taxa de assertividade, wins/losses, martingales

### 5. Ranking de Ativos

- **Top 5 ativos**: Lista dos melhores ativos para a estratégia
- **Métricas detalhadas**: Taxa de assertividade, entradas diretas, martingales
- **Análise automática**: Atualização periódica do ranking

## Configuração do Ambiente

### Requisitos de Sistema
- **Sistema Operacional**: Linux, macOS ou Windows
- **Python**: 3.7 ou superior
- **Redis**: Para produção
- **Nginx**: Para produção
- **Memória**: Mínimo 4GB RAM (recomendado 16GB para 1000 usuários)
- **CPU**: Mínimo 2 cores (recomendado 8+ cores para 1000 usuários)

### Variáveis de Ambiente

O arquivo `.env` ou `.env.example` contém as seguintes configurações:

```
# Configurações gerais da aplicação
SECRET_KEY=chave_secreta_da_aplicacao
FLASK_APP=main.py
FLASK_ENV=development|production
DEBUG=True|False

# Configurações de Redis
REDIS_URL=redis://localhost:6379/0
SESSION_TYPE=filesystem|redis
CACHE_TYPE=filesystem|redis
CACHE_REDIS_URL=redis://localhost:6379/1

# Configurações de recursos
MAX_WORKERS=20
MAX_CONNECTIONS=1000

# Configurações de servidor
HOST=0.0.0.0
PORT=5000

# Configurações do Gunicorn (para produção)
GUNICORN_WORKERS=1
GUNICORN_BIND=127.0.0.1:5000
GUNICORN_TIMEOUT=120
```

## Fluxo de Processo da "Estratégia da Minoria"

1. **Coleta de dados**: Obtenção de candles em intervalos de 1 minuto
2. **Formação de blocos**: Agrupamento em blocos de 5 candles consecutivos
3. **Análise de padrões**: Identificação da predominância (velas verdes vs. vermelhas)
4. **Sinal de entrada**: Entrada na direção minoritária ao final do bloco
5. **Acompanhamento**: Monitoramento de até 3 velas após o sinal
6. **Resultado**: WIN se direção correta em qualquer das 3 velas; LOSS caso contrário

### Níveis de Martingale
- **Entrada direta**: WIN na primeira vela após o sinal
- **Martingale 1**: WIN na segunda vela se a primeira falhou
- **Martingale 2**: WIN na terceira vela se as duas primeiras falharam

## Instalação e Execução

### Desenvolvimento Local

1. **Clone o repositório**:
   ```bash
   git clone <url-do-repositorio>
   cd CATALOGADOR_V2
   ```

2. **Crie e ative um ambiente virtual**:
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Linux/macOS
   source venv/bin/activate
   ```

3. **Instale as dependências**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure o ambiente**:
   ```bash
   cp .env.example .env
   # Edite o arquivo .env conforme necessário
   ```

5. **Execute em modo de desenvolvimento**:
   ```bash
   python main.py
   ```

### Produção (Servidor VPS)

1. **Configuração do servidor**:
   ```bash
   apt update && apt upgrade -y
   apt install -y python3-pip python3-venv redis-server nginx git
   ```

2. **Clone e prepare o projeto**:
   ```bash
   git clone <url-do-repositorio> /var/www/catalogador_v2
   cd /var/www/catalogador_v2
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   pip install gunicorn
   ```

3. **Configure o Redis**:
   ```bash
   systemctl enable redis-server
   systemctl start redis-server
   ```

4. **Configure o ambiente**:
   ```bash
   cp .env.example .env
   # Edite o arquivo .env para configurações de produção
   ```

5. **Configure o Nginx**:
   ```bash
   cp nginx.conf /etc/nginx/sites-available/catalogador
   ln -s /etc/nginx/sites-available/catalogador /etc/nginx/sites-enabled/
   systemctl reload nginx
   ```

6. **Configure o serviço Systemd**:
   ```bash
   cp catalogador.service /etc/systemd/system/
   systemctl daemon-reload
   systemctl enable catalogador
   systemctl start catalogador
   ```

## Monitoramento e Logs

Os logs da aplicação são armazenados nos seguintes locais:

- **Logs da aplicação**: `/var/www/catalogador_v2/logs/`
  - `main.log`: Logs gerais da aplicação
  - `estrategia_minoria.log`: Logs específicos da análise
  - `cache.log`: Logs do gerenciador de cache
  - `connection_manager.log`: Logs do gerenciador de conexões

- **Logs do Gunicorn**: 
  - `logs/gunicorn_access.log`: Requisições HTTP
  - `logs/gunicorn_error.log`: Erros do Gunicorn

- **Logs do Nginx**: 
  - `/var/log/nginx/catalogador_access.log`: Requisições HTTP
  - `/var/log/nginx/catalogador_error.log`: Erros do Nginx

## Manutenção do Sistema

### Reiniciar Serviços

Para reiniciar a aplicação:
```bash
systemctl restart catalogador
```

Para reiniciar o Nginx:
```bash
systemctl restart nginx
```

### Atualização do Código

Para atualizar o código:
```bash
cd /var/www/catalogador_v2
git pull
source venv/bin/activate
pip install -r requirements.txt
systemctl restart catalogador
```

### Backup do Sistema

Realizar backup periódico de:
- Código fonte: `/var/www/catalogador_v2/`
- Configurações: `.env`, `nginx.conf`, `catalogador.service`
- Logs: `/var/www/catalogador_v2/logs/`

## Resolução de Problemas Comuns

### API Indisponível
- **Sintoma**: Erro "API não conectada" ou "Falha na autenticação"
- **Solução**: Verificar credenciais e status da API Polarium

### Erro de Redis
- **Sintoma**: "Erro ao conectar ao Redis"
- **Solução**: Verificar se o serviço Redis está em execução
  ```bash
  systemctl status redis-server
  ```

### Lentidão na Análise
- **Sintoma**: Análises demoram muito para completar
- **Solução**: Aumentar `MAX_WORKERS` no arquivo `.env` e reiniciar

### Erro de Memória
- **Sintoma**: Aplicação instável ou reiniciando
- **Solução**: Verificar uso de memória e aumentar se necessário
  ```bash
  free -m
  ```

## FAQ

**P: A aplicação funciona sem conexão com a internet?**
R: Não, a aplicação requer conexão ativa com a internet para se comunicar com a API da Polarium.

**P: Quanto recurso de servidor é necessário para 1000 usuários simultâneos?**
R: Recomendamos um servidor com pelo menos 8 vCPU, 16 GB RAM para suportar até 1000 usuários simultâneos. O consumo pode variar conforme a utilização.

**P: É possível implantar em serviços de hospedagem compartilhada?**
R: Não recomendamos. Para o funcionamento adequado, é necessário um ambiente que permita configuração de Nginx, Gunicorn, Redis e execução contínua do aplicativo (VPS ou servidor dedicado).

**P: Posso usar a aplicação com múltiplas contas da Polarium?**
R: Sim, diferentes usuários podem fazer login com contas diferentes, e o sistema mantém uma instância da API separada para cada usuário.

**P: O sistema faz operações automáticas?**
R: Não, o CATALOGADOR V2 é uma ferramenta de análise e catalogação, não realiza operações automaticamente.

**P: A versão V2 tem melhorias em relação à V1?**
R: Sim, a versão V2 adiciona responsividade para diferentes dispositivos, melhorias na interface do usuário e otimizações de desempenho.

## Contribuição e Desenvolvimento

Para contribuir com o projeto:

1. Faça um fork do repositório
2. Crie um branch para sua feature:
   ```bash
   git checkout -b feature/nova-funcionalidade
   ```
3. Implemente suas alterações
4. Envie para o branch:
   ```bash
   git push origin feature/nova-funcionalidade
   ```
5. Crie um Pull Request

### Boas Práticas de Desenvolvimento

- Mantenha a compatibilidade com Python 3.7+
- Adicione logs adequados para facilitar o debugging
- Escreva código assíncrono quando interagir com APIs externas
- Mantenha o isolamento de estado entre usuários
- Utilize o sistema de cache para operações repetitivas

## Licença

Este projeto está licenciado sob termos proprietários. Todos os direitos reservados.

## Suporte

Para suporte técnico, entre em contato através do e-mail de suporte da equipe.

---

*Documentação v1.0 - Gerada em: 08/04/2024* 