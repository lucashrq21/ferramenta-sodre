# CATALOGADOR V1 - Documentação Completa

## Índice

1. [Visão Geral](#visão-geral)
2. [Funcionalidades](#funcionalidades)
3. [Arquitetura](#arquitetura)
4. [Tecnologias Utilizadas](#tecnologias-utilizadas)
5. [Estrutura do Projeto](#estrutura-do-projeto)
6. [Instalação e Configuração](#instalação-e-configuração)
   - [Ambiente de Desenvolvimento](#ambiente-de-desenvolvimento)
   - [Ambiente de Produção](#ambiente-de-produção)
7. [Configurações](#configurações)
   - [Variáveis de Ambiente](#variáveis-de-ambiente)
   - [Configuração do Nginx](#configuração-do-nginx)
   - [Configuração do Gunicorn](#configuração-do-gunicorn)
8. [Uso da Aplicação](#uso-da-aplicação)
   - [Login e Autenticação](#login-e-autenticação)
   - [Análise de Ativos](#análise-de-ativos)
   - [Visualização de Resultados](#visualização-de-resultados)
9. [Estratégia da Minoria](#estratégia-da-minoria)
10. [Gerenciamento de Conexões](#gerenciamento-de-conexões)
11. [Processamento Assíncrono](#processamento-assíncrono)
12. [Cache](#cache)
13. [Escalabilidade](#escalabilidade)
14. [Monitoramento](#monitoramento)
15. [Manutenção](#manutenção)
16. [Resolução de Problemas](#resolução-de-problemas)
17. [Atualizações](#atualizações)

## Visão Geral

O CATALOGADOR V1 é uma aplicação web desenvolvida para análise e catalogação gráfica da "Estratégia da Minoria" com Martingale em operações de trading financeiro. A aplicação se integra com a API da Polarium para obter dados de mercado em tempo real e realizar análises automatizadas.

A aplicação foi projetada para suportar múltiplos usuários simultâneos (até ~1000), com cada usuário tendo sua própria sessão isolada com a API Polarium. Utiliza arquitetura assíncrona para maximizar o desempenho e evitar bloqueios no processamento de requisições.

## Funcionalidades

### Principais Recursos

- **Autenticação Segura**: Suporte a login com e-mail/senha e autenticação de dois fatores (2FA)
- **Análise de Ativos**: Análise da Estratégia da Minoria em múltiplos ativos simultaneamente
- **Visualização Gráfica**: Gráficos interativos mostrando resultados das análises
- **Top 5 Ativos**: Classificação dos melhores ativos com base em taxa de vitória e vitórias diretas
- **Multi-usuário**: Suporte para centenas de usuários simultâneos
- **Isolamento de Sessões**: Cada usuário possui sua própria instância da API
- **Processamento Assíncrono**: Análises executadas em background sem bloquear a interface
- **Cache Inteligente**: Redução de chamadas à API com sistema de cache

## Arquitetura

A aplicação utiliza uma arquitetura moderna baseada em Flask com processamento assíncrono:

1. **Servidor Web**: Nginx funciona como proxy reverso, gerenciando SSL e balanceamento de carga
2. **Application Server**: Gunicorn/Uvicorn para processamento ASGI
3. **Framework Web**: Flask para rotas, renderização de templates e lógica da aplicação
4. **Gerenciamento de Estado**: Sistema próprio de gerenciamento de conexões por usuário
5. **Processamento Assíncrono**: Executor de threads para operações bloqueantes
6. **Armazenamento de Sessão**: Flask-Session com Redis ou sistema de arquivos
7. **Cache**: Sistema próprio de cache com suporte a Redis ou memória

### Diagrama Simplificado

```
Cliente Web <-> Nginx <-> Gunicorn <-> Flask <-> ConnectionManager <-> API Polarium
                                        ^
                                        |
                                      Cache
                                        |
                                      Redis/Filesystem
```

## Tecnologias Utilizadas

### Frontend
- HTML5, CSS3, JavaScript
- Bootstrap para interface responsiva
- Plotly.js para gráficos interativos
- jQuery para manipulação do DOM e AJAX

### Backend
- Python 3.7+
- Flask 2.2.0 (framework web)
- Werkzeug 2.2.0 (WSGI utility)
- Flask-Session (gerenciamento de sessões)
- Pandas (manipulação de dados)
- Plotly (geração de gráficos)
- Jinja2 (templates)
- Redis (opcional, para cache e sessões)

### Infraestrutura
- Nginx (proxy reverso)
- Gunicorn (servidor WSGI)
- Uvicorn (servidor ASGI)
- Systemd (gerenciamento de serviços)
- Redis (cache e sessões)

## Estrutura do Projeto

```
CATALOGADOR_V1/
├── main.py                    # Arquivo principal de entrada
├── estrategia_minoria.py      # Núcleo da aplicação
├── routes.py                  # Rotas e endpoints da aplicação
├── connection_manager.py      # Gerenciamento de conexões de usuários
├── async_utils.py             # Utilitários para operações assíncronas
├── cache_utils.py             # Sistema de cache
├── .env                       # Variáveis de ambiente
├── requirements.txt           # Dependências do projeto
├── nginx.conf                 # Configuração do Nginx
├── catalogador.service        # Configuração do serviço Systemd
├── gunicorn_conf.py           # Configuração do Gunicorn
├── docs/                      # Documentação
│   ├── projeto_completo.md    # Esta documentação
│   └── atualizacoes.md        # Registro de atualizações
├── logs/                      # Diretório de logs
├── templates/                 # Templates HTML
│   ├── index.html             # Página principal/login
│   └── top_ativos.html        # Página de Top 5 ativos
├── polariumapi/               # Módulo de integração com API Polarium
│   ├── stable_api.py          # Cliente estável da API
│   ├── constants.py           # Constantes da API
│   └── ws/                    # Módulos de WebSocket
└── venv/                      # Ambiente virtual Python
```

## Instalação e Configuração

### Ambiente de Desenvolvimento

1. **Requisitos**
   - Python 3.7 ou superior
   - Git
   - Pip (gerenciador de pacotes Python)

2. **Clone do Repositório**
   ```bash
   git clone <url-do-repositorio>
   cd CATALOGADOR_V1
   ```

3. **Ambiente Virtual**
   ```bash
   python -m venv venv
   
   # No Windows
   venv\Scripts\activate
   
   # No Linux/macOS
   source venv/bin/activate
   ```

4. **Dependências**
   ```bash
   pip install -r requirements.txt
   ```

5. **Configuração do Ambiente**
   ```bash
   cp .env.example .env
   # Edite o arquivo .env conforme necessário
   ```

6. **Execução**
   ```bash
   python main.py
   ```

7. **Acesso**
   - Abra o navegador em `http://localhost:5000`

### Ambiente de Produção

1. **Requisitos**
   - Servidor Linux (recomendado: Ubuntu 20.04 LTS)
   - Python 3.7 ou superior
   - Nginx
   - Redis (opcional, mas recomendado)
   - Certificados SSL (Let's Encrypt)

2. **Instalação de Dependências do Sistema**
   ```bash
   apt update && apt upgrade -y
   apt install -y python3-pip python3-venv redis-server nginx git certbot python3-certbot-nginx
   ```

3. **Configuração da Aplicação**
   - Siga os passos 2-5 do ambiente de desenvolvimento
   - Configure variáveis de ambiente para produção no `.env`

4. **Configuração do Nginx**
   ```bash
   cp nginx.conf /etc/nginx/sites-available/catalogador
   # Edite o arquivo para ajustar o domínio
   ln -s /etc/nginx/sites-available/catalogador /etc/nginx/sites-enabled/
   nginx -t  # Teste a configuração
   ```

5. **Configuração do SSL**
   ```bash
   certbot --nginx -d seu_dominio.com
   ```

6. **Serviço Systemd**
   ```bash
   cp catalogador.service /etc/systemd/system/
   # Edite o arquivo se necessário
   systemctl daemon-reload
   systemctl enable catalogador
   systemctl start catalogador
   ```

## Configurações

### Variáveis de Ambiente

O arquivo `.env` contém as configurações da aplicação:

```
# Configurações da aplicação
SECRET_KEY=chave_secreta_aqui
FLASK_APP=main.py
DEBUG=True  # Altere para False em produção

# Configurações de servidor
HOST=0.0.0.0
PORT=5000

# Configuração de sessão
SESSION_TYPE=filesystem  # redis ou filesystem
REDIS_URL=redis://localhost:6379/0

# Configuração de cache
CACHE_TYPE=filesystem  # redis ou filesystem
CACHE_REDIS_URL=redis://localhost:6379/1

# Configuração de threads
MAX_WORKERS=20
MAX_CONNECTIONS=1000

# Configuração do Gunicorn (apenas produção)
GUNICORN_WORKERS=1
GUNICORN_BIND=127.0.0.1:5000
GUNICORN_TIMEOUT=120
```

### Configuração do Nginx

Exemplo básico de configuração do Nginx:

```nginx
server {
    listen 80;
    server_name seu_dominio.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name seu_dominio.com;
    
    ssl_certificate /etc/letsencrypt/live/seu_dominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/seu_dominio.com/privkey.pem;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Uso da Aplicação

### Login e Autenticação

1. Acesse a página inicial da aplicação
2. Informe seu e-mail e senha da plataforma Polarium
3. Se a conta tiver 2FA habilitado, será solicitado o código de verificação
4. Após autenticação bem-sucedida, você será redirecionado para a interface principal

### Análise de Ativos

1. Selecione um ativo da lista disponível
2. Defina o número de blocos a analisar (padrão: 100)
3. Clique em "Analisar" para iniciar o processamento
4. Os resultados serão exibidos em forma de gráfico

### Visualização de Resultados

Os resultados são exibidos em diferentes formatos:

- **Gráfico de Velas**: Mostra os candles com marcações coloridas representando:
  - Verde: Vitória na primeira entrada
  - Azul: Vitória no Martingale 1
  - Amarelo: Vitória no Martingale 2
  - Vermelho: Loss em todas as tentativas

- **Tabela de Resultados**: Exibe detalhes de cada bloco analisado
- **Estatísticas Agregadas**: Mostra a taxa de vitória e outras métricas

## Estratégia da Minoria

A Estratégia da Minoria é a base da análise realizada pela aplicação:

1. A cada 5 minutos (5 candles de 1 minuto), analisa-se os 5 candles desse intervalo
2. Blocos de análise são fixos com base no tempo real (ex: 19:00:00 → 19:04:59)
3. Conta-se quantas velas são verdes (alta) e quantas são vermelhas (baixa)
4. A entrada é feita na direção da minoria
5. Se a entrada for loss, faz-se o 1º martingale e depois o 2º martingale, se necessário

### Classificação de Resultados

- **Vitória Direta**: Acerto na primeira entrada
- **Vitória G1**: Acerto no primeiro martingale
- **Vitória G2**: Acerto no segundo martingale
- **Loss Total**: Perda nas três tentativas

## Gerenciamento de Conexões

O sistema utiliza a classe `ConnectionManager` para gerenciar as conexões de cada usuário:

- Cada usuário possui sua própria instância da API Polarium
- Gerenciamento de locks para operações thread-safe
- Limpeza automática de conexões inativas
- Isolamento de estado entre usuários

## Processamento Assíncrono

O sistema utiliza processamento assíncrono para:

- Chamadas à API Polarium (operações bloqueantes)
- Análise de múltiplos ativos
- Geração de gráficos

A implementação usa:
- Biblioteca `asyncio` para programação assíncrona
- ThreadPoolExecutor para executar operações bloqueantes em threads separadas
- Timeout para evitar operações penduradas

## Cache

O sistema implementa cache em dois níveis:

1. **Cache de Candles**: Reduz chamadas à API para obtenção de dados de candles
2. **Cache de Resultados**: Armazena resultados de análises para reutilização

Opções de armazenamento:
- Redis (recomendado para produção)
- Sistema de arquivos (mais simples para desenvolvimento)
- Memória (fallback quando outras opções não estão disponíveis)

## Escalabilidade

A aplicação foi projetada para ser escalável:

- **Escalabilidade Vertical**: Ajuste o número de workers e threads
- **Escalabilidade Horizontal**: Possível com load balancer e sessões compartilhadas via Redis
- **Gerenciamento de Recursos**: Limpeza automática de conexões e recursos não utilizados

## Monitoramento

### Logs

Os logs da aplicação são armazenados em diferentes arquivos:

- `logs/main.log`: Logs principais da aplicação
- `logs/estrategia_minoria.log`: Logs específicos da estratégia
- `logs/connection_manager.log`: Logs do gerenciador de conexões
- `logs/gunicorn_*.log`: Logs do Gunicorn (produção)

### Métricas

O sistema coleta e armazena métricas de:
- Número de usuários conectados
- Taxa de sucesso de análises
- Tempo de processamento
- Uso de recursos

## Manutenção

### Backup

Recomenda-se backup regular de:
- Código-fonte
- Arquivo `.env` (sem compartilhar chaves sensíveis)
- Dados de sessão (se relevantes)

### Atualizações

As atualizações do sistema são documentadas no arquivo `docs/atualizacoes.md`.

Para atualizar o sistema:
1. Faça backup dos arquivos importantes
2. Atualize o código via Git ou upload manual
3. Instale novas dependências se necessário
4. Reinicie o serviço

## Resolução de Problemas

### Problemas Comuns

1. **Conexão com a API falha**:
   - Verifique credenciais no arquivo `.env`
   - Verifique a conectividade com os servidores da Polarium
   - Verifique logs para erros específicos

2. **Aplicação lenta**:
   - Verifique o número de usuários conectados
   - Ajuste o número de workers e threads
   - Considere adicionar mais recursos ao servidor

3. **Erros de cache**:
   - Verifique a conexão com o Redis
   - Ajuste as configurações de cache no `.env`

## Atualizações

Para informações sobre atualizações recentes, consulte o arquivo `docs/atualizacoes.md`.

---

**CATALOGADOR V1** - Desenvolvido para análise e catalogação da Estratégia da Minoria 