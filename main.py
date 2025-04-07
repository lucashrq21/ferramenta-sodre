import os
import logging
import atexit
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
        logging.FileHandler("logs/main.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("main")

# Importar módulos da aplicação
from estrategia_minoria import app
from cache_utils import cache_manager
from async_utils import cleanup as async_cleanup
import routes  # Importar as rotas para registrá-las

# Registrar função de limpeza para execução na saída
def cleanup():
    """Limpa recursos ao encerrar a aplicação."""
    logger.info("Encerrando aplicação...")
    
    # Limpar cache
    cache_manager.cleanup()
    
    # Limpar recursos assíncronos
    async_cleanup()
    
    logger.info("Aplicação encerrada com sucesso")

atexit.register(cleanup)

# Ponto de entrada da aplicação
if __name__ == "__main__":
    debug = os.getenv("DEBUG", "False").lower() == "true"
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5000"))
    
    logger.info(f"Iniciando CATALOGADOR V1 em {host}:{port} (debug={debug})")
    
    if debug:
        # Modo de desenvolvimento com Flask
        app.run(debug=True, host=host, port=port)
    else:
        # Modo de produção com Uvicorn
        import uvicorn
        uvicorn.run("main:app", host=host, port=port, log_level="info") 