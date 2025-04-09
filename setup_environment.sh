#!/bin/bash
# Script para configurar o ambiente do CATALOGADOR_V2

# Criar diretórios necessários
mkdir -p logs
mkdir -p flask_session
mkdir -p __pycache__

# Configurar permissões
chmod -R 755 logs
chmod -R 755 flask_session

# Instalar dependências
pip install -r requirements.txt

# Verificar Redis
if command -v redis-cli > /dev/null 2>&1; then
    echo "Verificando conexão com Redis..."
    redis-ping=$(redis-cli ping 2>/dev/null)
    if [ "$redis-ping" == "PONG" ]; then
        echo "✅ Redis está rodando corretamente"
    else
        echo "⚠️  Redis não está respondendo. Configure-o para melhor performance."
    fi
else
    echo "⚠️  Redis não encontrado. Considere instalar para melhor performance."
fi

echo "Ambiente configurado com sucesso! Execute 'python main.py' para iniciar a aplicação." 