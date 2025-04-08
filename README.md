# CATALOGADOR V2

Sistema para análise e catalogação gráfica da "Estratégia da Minoria" com Martingale em operações de trading.

## Sobre o Projeto

O CATALOGADOR V2 é uma aplicação web escalável que permite a análise de padrões de mercado utilizando a "Estratégia da Minoria". A aplicação foi projetada para suportar múltiplos usuários simultâneos, com cada usuário tendo sua própria sessão isolada com a API Polarium.

### Principais Características

- **Multi-usuário**: Suporta até ~1000 usuários simultâneos
- **Arquitetura Assíncrona**: Implementada com Flask + ASGI (Uvicorn)
- **Cache Eficiente**: Implementado com Redis para reduzir a carga na API
- **Interface Responsiva**: Design adaptado para diferentes tamanhos de tela
- **Análise de Dados**: Processamento e visualização de padrões de mercado
- **Estratégia da Minoria**: Implementação completa com suporte para Martingale
- **Ranking de Ativos**: Identificação automática dos melhores ativos para a estratégia

## Tecnologias Utilizadas

### Backend
- Python 3.7+
- Flask 2.2.0
- Uvicorn 0.22.0
- Gunicorn 20.1.0
- Redis 4.5.1
- Pandas 1.4.0
- Plotly 5.5.0

### Frontend
- HTML5/CSS3
- JavaScript
- Bootstrap
- jQuery
- Plotly.js

## Instalação

### Requisitos

- Python 3.7 ou superior
- Redis (para produção)
- Nginx (para produção)
- Conta na plataforma Polarium

### Desenvolvimento Local

1. Clone o repositório:
   ```bash
   git clone https://github.com/seu-usuario/CATALOGADOR_V2.git
   cd CATALOGADOR_V2
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

4. Configure o ambiente:
   ```bash
   cp .env.example .env
   # Edite o arquivo .env conforme necessário
   ```

5. Execute em modo de desenvolvimento:
   ```bash
   python main.py
   ```

Para instruções detalhadas sobre implantação em produção, consulte a [documentação completa](docs/catalogador_documentacao.md).

## Documentação

A documentação completa do projeto está disponível na pasta `docs`:

- [Documentação Técnica](docs/catalogador_documentacao.md)

## Licença

Este projeto está licenciado sob termos proprietários. Todos os direitos reservados.

## Contato

Para suporte técnico, entre em contato através do e-mail de suporte da equipe. 