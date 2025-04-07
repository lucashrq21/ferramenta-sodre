# CATALOGADOR V1 - Escalável

## Visão Geral

CATALOGADOR V1 é uma aplicação web para análise e catalogação gráfica da "Estratégia da Minoria" com Martingale em operações de trading. A aplicação foi refatorada para suportar múltiplos usuários simultâneos (até ~1000), com cada usuário tendo sua própria sessão isolada com a API Polarium.

## Características

- **Multi-usuário**: Suporta até ~1000 usuários simultâneos
- **Arquitetura Assíncrona**: Implementada com Flask + ASGI (Uvicorn) para não bloquear o loop de eventos
- **Gerenciamento de Sessão**: Sessões individuais para cada usuário usando Flask-Session e Redis
- **Cache**: Implementado com Redis para reduzir a carga na API
- **Isolamento de Estado**: Cada usuário tem sua própria instância da API Polarium
- **Robustez**: Recuperação automática de erros e manipulação adequada de exceções
- **Escalabilidade**: Facilmente escalável através da configuração do Nginx e Gunicorn

## Pré-requisitos

- Python 3.7 ou superior
- Redis (para produção)
- Nginx (para produção)
- Conta na plataforma Polarium
- Sistema operacional: Linux, macOS ou Windows

## Instalação

### Desenvolvimento Local

1. Clone o repositório:
   ```bash
   git clone <url-do-repositorio>
   cd CATALOGADOR_V1
   ```

2. Crie e ative um ambiente virtual:
   ```bash
   python -m venv venv
   
   # No Windows
   venv\Scripts\activate
   
   # No Linux/macOS
   source venv/bin/activate
   ```

3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

4. Copie o arquivo `.env.example` (se existir) para `.env` e ajuste as configurações conforme necessário:
   ```bash
   cp .env.example .env
   ```
   Se não existir o arquivo de exemplo, crie o `.env` com as seguintes configurações:
   ```
   SECRET_KEY=sua_chave_secreta
   FLASK_APP=main.py
   FLASK_ENV=development
   REDIS_URL=redis://localhost:6379/0
   SESSION_TYPE=filesystem  # Altere para 'redis' em produção
   CACHE_TYPE=filesystem    # Altere para 'redis' em produção
   CACHE_REDIS_URL=redis://localhost:6379/1
   MAX_WORKERS=20
   MAX_CONNECTIONS=1000
   DEBUG=True               # Altere para 'False' em produção
   ```

5. Execute a aplicação em modo de desenvolvimento:
   ```bash
   python main.py
   ```

6. Acesse a aplicação em `http://localhost:5000` no seu navegador.

### Produção (VPS)

1. Configure um servidor (recomendado: VPS na Hostinger com pelo menos 8 vCPU e 16 GB RAM):
   ```bash
   apt update && apt upgrade -y
   apt install -y python3-pip python3-venv redis-server nginx git
   ```

2. Clone o repositório:
   ```bash
   git clone <url-do-repositorio> /var/www/catalogador_v1
   cd /var/www/catalogador_v1
   ```

3. Prepare o ambiente Python:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   pip install gunicorn
   ```

4. Configure o Redis:
   ```bash
   systemctl enable redis-server
   systemctl start redis-server
   ```

5. Configure o arquivo `.env` com as configurações de produção:
   ```
   SECRET_KEY=sua_chave_secreta_segura
   FLASK_APP=main.py
   FLASK_ENV=production
   REDIS_URL=redis://localhost:6379/0
   SESSION_TYPE=redis
   CACHE_TYPE=redis
   CACHE_REDIS_URL=redis://localhost:6379/1
   MAX_WORKERS=20
   MAX_CONNECTIONS=1000
   DEBUG=False
   GUNICORN_WORKERS=1
   GUNICORN_BIND=127.0.0.1:5000
   GUNICORN_TIMEOUT=120
   ```

6. Configure o Nginx:
   ```bash
   cp nginx.conf /etc/nginx/sites-available/catalogador
   # Edite o arquivo para ajustar o domínio e o caminho dos certificados SSL
   ln -s /etc/nginx/sites-available/catalogador /etc/nginx/sites-enabled/
   nginx -t
   systemctl reload nginx
   ```

7. Configure o SSL com Certbot (Let's Encrypt):
   ```bash
   apt install -y certbot python3-certbot-nginx
   certbot --nginx -d seu_dominio.com
   ```

8. Configure o serviço Systemd:
   ```bash
   cp catalogador.service /etc/systemd/system/
   # Edite o arquivo para ajustar caminhos e usuário
   systemctl daemon-reload
   systemctl enable catalogador
   systemctl start catalogador
   ```

9. Verifique o status do serviço:
   ```bash
   systemctl status catalogador
   ```

10. Acesse a aplicação através do seu domínio configurado.

## Monitoramento e Manutenção

### Logs

Os logs da aplicação são armazenados nos seguintes locais:

- **Logs da aplicação**: `/var/www/catalogador_v1/logs/`
- **Logs do Gunicorn**: `/var/www/catalogador_v1/logs/gunicorn_*.log`
- **Logs do Nginx**: `/var/log/nginx/catalogador_*.log`

### Verificação de Status

Para verificar o status do serviço:
```bash
systemctl status catalogador
```

### Reiniciar Serviços

Para reiniciar a aplicação:
```bash
systemctl restart catalogador
```

Para reiniciar o Nginx:
```bash
systemctl restart nginx
```

### Monitoramento de Sistema

Monitore os recursos do sistema:
```bash
htop
```

## Arquitetura

A aplicação utiliza a seguinte arquitetura:

1. **Nginx**: Proxy reverso, terminação SSL, balanceamento de carga
2. **Gunicorn**: Gerenciador de processos para a aplicação Flask
3. **Uvicorn**: Servidor ASGI para execução da aplicação Flask de forma assíncrona
4. **Flask**: Framework web para a aplicação
5. **Redis**: Armazenamento para sessões e cache
6. **API Polarium**: API externa para obtenção de dados de mercado

## Estrutura do Projeto

```
CATALOGADOR_V1/
├── main.py                    # Arquivo principal de entrada
├── estrategia_minoria_novo.py # Implementação principal da aplicação
├── routes.py                  # Rotas da API
├── connection_manager.py      # Gerenciador de conexões de usuários
├── async_utils.py             # Utilitários para operações assíncronas
├── cache_utils.py             # Utilitários para cache
├── requirements.txt           # Dependências do projeto
├── .env                       # Variáveis de ambiente
├── nginx.conf                 # Configuração de exemplo para Nginx
├── catalogador.service        # Configuração de serviço Systemd
├── gunicorn_conf.py           # Configuração para Gunicorn
├── docs/                      # Documentação
│   └── documentacao.md        # Documentação completa
├── logs/                      # Diretório de logs
├── templates/                 # Templates HTML
│   ├── index.html             # Página principal
│   └── top_ativos.html        # Página de Top 5 ativos
└── polariumapi/               # Módulo da API Polarium
```

## Contribuição

Para contribuir com o projeto:

1. Faça um fork do repositório
2. Crie um branch para sua feature (`git checkout -b feature/nova-funcionalidade`)
3. Implemente suas alterações
4. Faça commit das alterações (`git commit -am 'Adiciona nova funcionalidade'`)
5. Envie para o branch (`git push origin feature/nova-funcionalidade`)
6. Crie um Pull Request

## Licença

Este projeto está licenciado sob termos proprietários. Todos os direitos reservados.

## Suporte

Para suporte técnico, entre em contato através de [email de suporte].

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
R: Não, o CATALOGADOR V1 é uma ferramenta de análise e catalogação, não realiza operações automaticamente. 