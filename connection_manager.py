import threading
import time
from typing import Dict, Any, Optional, Tuple
import logging
from datetime import datetime

# Configurar o logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/connection_manager.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ConnectionManager")

class ConnectionManager:
    """
    Classe responsável por gerenciar as conexões dos usuários com a API da Polarium.
    Mantém o estado de cada usuário separadamente, permitindo múltiplas conexões simultâneas.
    """
    
    def __init__(self, cleanup_interval: int = 900, max_idle_time: int = 3600):
        """
        Inicializa o ConnectionManager.
        
        Args:
            cleanup_interval (int): Intervalo em segundos para verificar conexões inativas (padrão: 15 minutos)
            max_idle_time (int): Tempo máximo em segundos que uma conexão pode ficar inativa (padrão: 1 hora)
        """
        self._connections: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()  # Lock para acesso thread-safe
        self._cleanup_interval = cleanup_interval
        self._max_idle_time = max_idle_time
        
        # Iniciar thread de limpeza em background
        self._cleanup_thread = threading.Thread(target=self._cleanup_task, daemon=True)
        self._cleanup_thread.start()
        
        logger.info("ConnectionManager inicializado")
    
    def add_connection(self, user_id: str, api_instance) -> None:
        """
        Adiciona uma nova conexão para um usuário.
        
        Args:
            user_id (str): ID único do usuário
            api_instance: Instância da API Polarium
        """
        with self._lock:
            # Se já existir, atualizar a instância da API
            if user_id in self._connections:
                logger.info(f"Atualizando conexão existente para usuário {user_id}")
                # Desconectar a instância antiga se existir
                old_api = self._connections[user_id].get('api')
                if old_api is not None:
                    try:
                        old_api.close()
                    except Exception as e:
                        logger.error(f"Erro ao fechar conexão antiga para usuário {user_id}: {str(e)}")
            else:
                logger.info(f"Adicionando nova conexão para usuário {user_id}")
            
            # Criar ou atualizar o registro do usuário
            self._connections[user_id] = {
                'api': api_instance,
                'lock': threading.RLock(),
                'connected': True,
                'last_results': {},
                'stats': {},  # Estatísticas para todos os ativos analisados
                'analysis_progress': {
                    "in_progress": False,
                    "total_assets": 0,
                    "analyzed_assets": 0,
                    "current_asset": "",
                    "percent_complete": 0,
                    "success_count": 0,
                    "start_time": 0
                },
                'last_activity': time.time()
            }
    
    def get_connection(self, user_id: str) -> Tuple[Any, bool]:
        """
        Obtém a conexão para um usuário específico.
        
        Args:
            user_id (str): ID do usuário
            
        Returns:
            tuple: (api_instance, connected_status)
        """
        with self._lock:
            if user_id not in self._connections:
                return None, False
            
            # Atualizar timestamp da última atividade
            self._connections[user_id]['last_activity'] = time.time()
            return self._connections[user_id]['api'], self._connections[user_id]['connected']
    
    def get_user_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtém todos os dados associados a um usuário.
        
        Args:
            user_id (str): ID do usuário
            
        Returns:
            dict: Dados do usuário ou None se não existir
        """
        with self._lock:
            if user_id not in self._connections:
                return None
            
            # Atualizar timestamp da última atividade
            self._connections[user_id]['last_activity'] = time.time()
            return self._connections[user_id]
    
    def get_lock(self, user_id: str) -> Optional[threading.RLock]:
        """
        Obtém o lock específico de um usuário.
        
        Args:
            user_id (str): ID do usuário
            
        Returns:
            threading.RLock: Lock do usuário ou None se não existir
        """
        with self._lock:
            if user_id not in self._connections:
                return None
            
            # Não atualiza o timestamp aqui, pois isso pode ser chamado com muita frequência
            return self._connections[user_id]['lock']
    
    def update_connection_status(self, user_id: str, connected: bool) -> bool:
        """
        Atualiza o status de conexão de um usuário.
        
        Args:
            user_id (str): ID do usuário
            connected (bool): Novo status de conexão
            
        Returns:
            bool: True se atualizado com sucesso, False caso contrário
        """
        with self._lock:
            if user_id not in self._connections:
                return False
            
            self._connections[user_id]['connected'] = connected
            self._connections[user_id]['last_activity'] = time.time()
            return True
    
    def update_user_state(self, user_id: str, key: str, value: Any) -> bool:
        """
        Atualiza um item específico do estado do usuário.
        
        Args:
            user_id (str): ID do usuário
            key (str): Chave a ser atualizada
            value (Any): Novo valor
            
        Returns:
            bool: True se atualizado com sucesso, False caso contrário
        """
        with self._lock:
            if user_id not in self._connections:
                return False
            
            if key in self._connections[user_id]:
                self._connections[user_id][key] = value
                self._connections[user_id]['last_activity'] = time.time()
                return True
            return False
    
    def remove_connection(self, user_id: str) -> bool:
        """
        Remove a conexão de um usuário, fechando-a adequadamente.
        
        Args:
            user_id (str): ID do usuário
            
        Returns:
            bool: True se removido com sucesso, False caso contrário
        """
        with self._lock:
            if user_id not in self._connections:
                return False
            
            # Tentar fechar a conexão da API
            api_instance = self._connections[user_id].get('api')
            if api_instance is not None:
                try:
                    api_instance.close()
                    logger.info(f"Conexão API fechada para usuário {user_id}")
                except Exception as e:
                    logger.error(f"Erro ao fechar conexão API para usuário {user_id}: {str(e)}")
            
            # Remover do dicionário
            del self._connections[user_id]
            logger.info(f"Conexão removida para usuário {user_id}")
            return True
    
    def list_connections(self) -> Dict[str, Dict[str, Any]]:
        """
        Lista informações resumidas sobre todas as conexões.
        
        Returns:
            dict: Informações de todas as conexões ativas
        """
        with self._lock:
            result = {}
            current_time = time.time()
            
            for user_id, data in self._connections.items():
                # Criar um resumo sem a instância da API e outros objetos grandes
                idle_time = current_time - data['last_activity']
                result[user_id] = {
                    'connected': data['connected'],
                    'idle_time': idle_time,
                    'idle_time_formatted': str(datetime.utcfromtimestamp(idle_time).strftime('%H:%M:%S')),
                    'has_results': bool(data['last_results']),
                    'analysis_in_progress': data['analysis_progress']['in_progress']
                }
            
            return result
    
    def _cleanup_task(self) -> None:
        """
        Tarefa em background que limpa conexões inativas periodicamente.
        """
        while True:
            try:
                time.sleep(self._cleanup_interval)
                self._cleanup_inactive_connections()
            except Exception as e:
                logger.error(f"Erro na tarefa de limpeza: {str(e)}")
    
    def _cleanup_inactive_connections(self) -> None:
        """
        Remove conexões que estão inativas por muito tempo.
        """
        with self._lock:
            current_time = time.time()
            to_remove = []
            
            for user_id, data in self._connections.items():
                if current_time - data['last_activity'] > self._max_idle_time:
                    to_remove.append(user_id)
            
            for user_id in to_remove:
                try:
                    self.remove_connection(user_id)
                    logger.info(f"Conexão inativa removida para usuário {user_id}")
                except Exception as e:
                    logger.error(f"Erro ao remover conexão inativa para usuário {user_id}: {str(e)}")
            
            if to_remove:
                logger.info(f"Limpeza concluída, {len(to_remove)} conexões removidas")
            else:
                logger.debug("Limpeza concluída, nenhuma conexão inativa encontrada") 