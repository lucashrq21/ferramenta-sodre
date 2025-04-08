#!/bin/bash
# Script de implantação do CATALOGADOR_V2 em ambiente de produção
# Domínio: sodretradersystem.pro

set -e  # Interrompe o script em caso de erro

echo "=== Iniciando implantação do CATALOGADOR_V2 ==="
echo "Domínio: sodretradersystem.pro"

# Verificar permissões de root
if [ "$(id -u)" -ne 0 ]; then
    echo "Este script deve ser executado como root ou com sudo."
    exit 1
fi

# Atualizar sistema
echo "=== Atualizando sistema ==="
apt update && apt upgrade -y

# Instalar dependências
echo "=== Instalando dependências ==="
apt install -y python3-pip python3-venv redis-server nginx git certbot python3-certbot-nginx

# Criar diretório de aplicação
echo "=== Configurando diretórios ==="
mkdir -p /var/www/catalogador_v2
chown www-data:www-data /var/www/catalogador_v2

# Clonar repositório
echo "=== Clonando repositório ==="
git clone https://github.com/lucashrq21/sistema-sodre.git /var/www/catalogador_v2
cd /var/www/catalogador_v2

# Criar ambiente virtual e instalar dependências
echo "=== Configurando ambiente Python ==="
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn

# Configurar logs
echo "=== Configurando diretório de logs ==="
mkdir -p logs
chown -R www-data:www-data logs

# Configurar serviço systemd
echo "=== Configurando serviço systemd ==="
cp catalogador.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable catalogador

# Configurar Nginx
echo "=== Configurando Nginx ==="
cp nginx.conf /etc/nginx/sites-available/catalogador
ln -sf /etc/nginx/sites-available/catalogador /etc/nginx/sites-enabled/
nginx -t

# Configurar Let's Encrypt
echo "=== Configurando certificados SSL ==="
certbot --nginx -d sodretradersystem.pro -d www.sodretradersystem.pro --non-interactive --agree-tos --email seu-email@example.com

# Iniciar serviços
echo "=== Iniciando serviços ==="
systemctl start redis-server
systemctl start catalogador
systemctl restart nginx

# Verificar status
echo "=== Verificando status dos serviços ==="
systemctl status redis-server --no-pager
systemctl status catalogador --no-pager
systemctl status nginx --no-pager

echo ""
echo "=== Implantação concluída! ==="
echo "Aplicação disponível em: https://sodretradersystem.pro"
echo ""
echo "Para verificar logs:"
echo "- Aplicação: tail -f /var/www/catalogador_v2/logs/*.log"
echo "- Nginx: tail -f /var/log/nginx/catalogador_*.log"
echo ""
echo "Lembre-se de alterar a senha do Redis e atualizar as configurações de segurança necessárias!" 