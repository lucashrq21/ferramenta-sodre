# CATALOGADOR V1

Um sistema avançado para análise de ativos financeiros com foco na Estratégia da Minoria.

## Descrição

CATALOGADOR V1 é uma aplicação web desenvolvida em Python/Flask que permite analisar padrões de mercado em diversos ativos financeiros. O sistema utiliza a API Polarium para obter dados de mercado em tempo real e aplicar estratégias de análise.

## Principais Funcionalidades

- **Análise de Padrões de Minoria**: Identificação de padrões onde a minoria dos movimentos tende a prevalecer nos próximos períodos
- **Top 5 Ativos**: Sistema inteligente para identificar os 5 melhores ativos com base em taxas de acerto
- **Interface Intuitiva**: Dashboard completo com análises gráficas e estatísticas
- **Cache Multinível**: Sistema otimizado para alta performance
- **Operação Assíncrona**: Processamento assíncrono para melhor experiência do usuário

## Tecnologias Utilizadas

- Python 3.8+
- Flask
- Plotly (visualização de dados)
- jQuery/Bootstrap
- Polarium API
- Sistema de cache avançado

## Requisitos

- Python 3.8 ou superior
- Conta na plataforma Polarium
- Dependências listadas em `requirements.txt`

## Instalação

1. Clone este repositório
2. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```
3. Configure as variáveis de ambiente (crie um arquivo `.env` baseado no `.env.example`)
4. Execute a aplicação:
   ```
   python app.py
   ```

## Estratégia da Minoria

O sistema se baseia na premissa de que o mercado frequentemente vai contra a tendência majoritária em determinados períodos. A análise identifica padrões onde a minoria dos movimentos (velas verdes ou vermelhas) tende a prevalecer nos próximos períodos, oferecendo oportunidades para operações com maior probabilidade de sucesso.

## Licença

Este projeto é licenciado sob a licença MIT - veja o arquivo LICENSE para mais detalhes. 