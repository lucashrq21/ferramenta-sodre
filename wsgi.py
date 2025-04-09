# wsgi.py - Ponto de entrada para o servidor WSGI
import os
import logging
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configurar o diretório de logs
logs_dir = "logs"
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/wsgi.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("wsgi")

# Configurar diretórios adicionais
flask_session_dir = "flask_session"
if not os.path.exists(flask_session_dir):
    os.makedirs(flask_session_dir)

# Importar a aplicação e suas dependências
from estrategia_minoria import app
import routes  # Importar rotas explicitamente

# Exportar a aplicação para o servidor WSGI
application = app 