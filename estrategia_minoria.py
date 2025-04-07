import asyncio
import os
import time
import json
import math
import gc
import uuid
import logging
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_session import Session
from dotenv import load_dotenv
from polariumapi.stable_api import Polarium
from polariumapi.constants import ACTIVES

from connection_manager import ConnectionManager
from async_utils import run_blocking_func, run_with_timeout, cleanup as async_cleanup
from cache_utils import cache_manager

# Carregar variáveis de ambiente
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/estrategia_minoria.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("estrategia_minoria")

# Inicializar aplicação Flask
app = Flask(__name__)

# Configurações da aplicação
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'chave_secreta_padrao')
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SESSION_TYPE'] = os.getenv('SESSION_TYPE', 'filesystem')
app.config['SESSION_PERMANENT'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=12)

# Configurar Redis para sessões se disponível
if app.config['SESSION_TYPE'] == 'redis':
    import redis
    app.config['SESSION_REDIS'] = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379/0'))

# Inicializar extensão de sessão
Session(app)

# Inicializar gerenciador de conexões
connection_manager = ConnectionManager()

# Inicializar cache com a aplicação Flask
cache_manager.init_app(app)

# Lista de ativos recomendados
ativos_recomendados = [
    # Criptomoedas
    "BTCUSD", "ETHUSD", "LTCUSD", "XRPUSD", 
    
    # Forex
    "EURUSD", "EURUSD-OTC", "GBPUSD", "GBPUSD-OTC", "USDJPY", "USDJPY-OTC", 
    "AUDUSD", "AUDUSD-OTC", "EURJPY", "EURJPY-OTC", "EURGBP", "EURGBP-OTC",
    "EURCHF", "GBPJPY", "USDCHF", "AUDCAD", "NZDUSD", "USDCAD",
    
    # Índices
    "US500", "USTEC", "US30", "AUS200", "PUT/CALL", "HK50", "DE30",
    
    # Ações
    "AMAZON", "GOOGLE", "FACEBOOK", "APPLE", "NETFLIX", "TESLA", "ALIBABA",
    "MICROSOFT", "AMZN/ALIBABA", "NVIDIA", "ARB/USD", "SPY/GOLD", "META",
    
    # Commodities
    "GOLD", "SILVER", "OIL"
]

# Filtro para formatar timestamps
@app.template_filter('strftime')
def _jinja2_filter_datetime(timestamp, fmt=None):
    date = datetime.fromtimestamp(timestamp)
    if fmt:
        return date.strftime(fmt)
    return date.strftime('%H:%M:%S')

# Utilitário para gerar IDs de usuário
def generate_user_id():
    """Gera um ID único para um usuário."""
    return str(uuid.uuid4())

# Função para conectar à API Polarium (versão assíncrona)
async def connect_to_polarium(email, password):
    """Conecta à API Polarium de forma assíncrona."""
    logger.info(f"Tentando conectar com email: {email}")
    
    try:
        # Criar nova instância Polarium (operação bloqueante executada em thread)
        new_api = await run_blocking_func(lambda: Polarium(email, password))
        logger.info("Instância Polarium criada")
        
        # Chamar método de conexão (operação bloqueante)
        check, reason = await run_blocking_func(new_api.connect)
        logger.info(f"new_api.connect() retornou: check={check}, reason={reason}")
        
        if check:
            # Alterar o tipo de conta para practice
            await run_blocking_func(new_api.change_balance, 'PRACTICE')
            logger.info("Balance alterado para PRACTICE")
            
            # Conectado com sucesso
            return True, "Conectado com sucesso!", new_api, reason
        else:
            if reason == "2FA":
                logger.info("2FA requerido")
                return False, "2FA", new_api, reason
            else:
                logger.error(f"Falha na autenticação inicial: {reason}")
                return False, f"Erro na conexão: {reason}", None, reason
    
    except Exception as e:
        logger.exception(f"Exceção não esperada: {str(e)}")
        return False, f"Erro crítico ao conectar: {str(e)}", None, "error"

# Função auxiliar para verificar blocos de 5 minutos
def get_time_block(timestamp):
    """Determina o início do bloco de 5 minutos para um timestamp."""
    dt = datetime.fromtimestamp(timestamp)
    minutes = dt.minute - (dt.minute % 5)
    block_start = datetime(dt.year, dt.month, dt.day, dt.hour, minutes, 0)
    return int(block_start.timestamp())

# Função para obter a posição da linha 30 segundos antes do início do bloco
def get_line_position(block_time):
    """Determina a posição da linha 30 segundos antes do início do bloco."""
    return block_time - 30

# Função para verificar se um candle pertence ao bloco entre as linhas
def candle_in_block(candle_time, block_start):
    """Verifica se o candle está entre as linhas do bloco."""
    block_line_start = get_line_position(block_start)
    block_line_end = get_line_position(block_start + 300)  # +300 segundos (5 minutos)
    return block_line_start <= candle_time < block_line_end

# Função para obter e analisar candles (refatorada para receber api_instance)
async def analyze_candles(api_instance, active, timeframe=60, num_blocks=10):
    """Analisa candles para um ativo específico, usando a instância da API do usuário."""
    if api_instance is None:
        return {"error": "API não conectada"}
    
    try:
        num_blocks = min(int(num_blocks), 100)
        current_time = int(time.time())
        logger.info(f"Analisando {active}, tempo atual: {datetime.fromtimestamp(current_time).strftime('%Y-%m-%d %H:%M:%S')}")
        current_block = get_time_block(current_time)
        
        # Determinar número de candles a obter
        total_candles = num_blocks * 5 + 20
        candles_to_request = total_candles + 30
        
        # Tentar obter do cache primeiro
        cache_key = f"candles:{active}:{timeframe}:{candles_to_request}:{current_time//60}"
        cache_hit, cached_candles = cache_manager.get(cache_key)
        
        if cache_hit:
            logger.info(f"Cache hit para candles de {active}")
            candles = cached_candles
        else:
            # Obter candles da API (operação bloqueante)
            logger.info(f"Solicitando {candles_to_request} candles para {active}")
            candles = await run_blocking_func(
                api_instance.get_candles, 
                active, 
                timeframe, 
                candles_to_request, 
                current_time
            )
            
            # Armazenar no cache se obtido com sucesso (TTL de 30 segundos)
            if candles:
                cache_manager.set(cache_key, candles, ttl=30)
        
        if not candles:
            logger.error(f"API não retornou candles para {active}")
            return {"error": "API não retornou candles."}
            
        # Log do candle mais recente
        latest_candle_time = max(c['from'] for c in candles)
        logger.info(f"Candle mais recente: {datetime.fromtimestamp(latest_candle_time).strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Verificar idade do candle mais recente
        candle_age = current_time - latest_candle_time
        logger.info(f"Último candle tem {candle_age} segundos de idade")
        
        if candle_age > 120:  # Mais de 2 minutos
            logger.warning(f"Candle muito antigo para {active}, tentando novamente")
            candles = await run_blocking_func(
                api_instance.get_candles, 
                active, 
                timeframe, 
                candles_to_request, 
                current_time
            )
        
        # Organizar candles em blocos
        blocks = {}
        results = []
        
        # Criar blocos formais primeiro
        for i in range(num_blocks):
            block_time = current_block - (i * 300)
            blocks[block_time] = []
        
        # Distribuir candles nos blocos
        for candle in candles:
            for block_time in blocks.keys():
                if candle_in_block(candle['from'], block_time):
                    if len(blocks[block_time]) < 5:  # Limitar a 5 velas por bloco
                        is_doji = candle['open'] == candle['close']
                        direction = "doji" if is_doji else "verde" if candle['open'] < candle['close'] else "vermelha"
                        blocks[block_time].append({
                            "time": candle['from'],
                            "direction": direction,
                            "open": candle['open'],
                            "close": candle['close'],
                            "high": candle['max'],
                            "low": candle['min']
                        })
                    break
        
        # Ordenar blocos por tempo
        sorted_blocks = sorted(blocks.items(), key=lambda x: x[0])
        
        # Analisar cada bloco
        for block_time, candles_block in sorted_blocks:
            if len(candles_block) == 5:  # Só considerar blocos completos
                # Calcular contagens de velas verdes e vermelhas
                verde_count = sum(1 for c in candles_block if c['direction'] == "verde")
                vermelha_count = sum(1 for c in candles_block if c['direction'] == "vermelha")
                
                # Verificar se há doji no bloco
                has_doji = any(c['direction'] == "doji" for c in candles_block)
                
                if has_doji:
                    signal = "NULO"
                else:
                    # Determinar minoria
                    if verde_count < vermelha_count:
                        signal = "CALL"
                    elif vermelha_count < verde_count:
                        signal = "PUT"
                    else:
                        signal = "DOJI"  # Igual número de verdes e vermelhas
                
                # Verificar resultado para blocos já finalizados
                next_block_time = block_time + (5 * 60)
                result_data = None
                
                if signal != "NULO":
                    result_data = await check_result(api_instance, active, block_time, next_block_time, signal)
                else:
                    result_data = {"result": "NULO", "martingale": "NULO"}
                
                # Adicionar ao resultado
                block_data = {
                    "block_time": block_time,
                    "time_str": datetime.fromtimestamp(block_time).strftime("%H:%M"),
                    "verde_count": verde_count,
                    "vermelha_count": vermelha_count,
                    "signal": signal,
                    "candles": candles_block,
                    "result": result_data["result"] if result_data else None,
                    "martingale": result_data["martingale"] if result_data else None
                }
                
                results.append(block_data)
        
        # Ordenar resultados cronologicamente
        results = sorted(results, key=lambda x: x["block_time"])
        
        return {"success": True, "data": results}
    
    except Exception as e:
        logger.exception(f"Erro ao analisar candles de {active}: {str(e)}")
        return {"error": f"Erro ao analisar candles: {str(e)}"}

# Verificar resultado da operação (refatorada para receber api_instance)
async def check_result(api_instance, active, block_time, next_block_time, signal):
    """Verifica o resultado de uma operação usando a instância da API do usuário."""
    try:
        # Verificar o tempo atual
        current_time = int(time.time())
        line_end_time = get_line_position(next_block_time)
        
        # Tempo para primeiro candle completo (1 minuto após o final do bloco)
        required_time_for_first = line_end_time + 60
        
        if current_time < required_time_for_first:
            logger.info(f"Bloco {datetime.fromtimestamp(block_time).strftime('%H:%M')} ainda não tem candle completo")
            return None
        
        # Calcular quantos candles completos devemos ter
        minutes_passed = min(3, max(1, (current_time - line_end_time) // 60))
        logger.info(f"{minutes_passed} minutos desde o final do bloco {datetime.fromtimestamp(block_time).strftime('%H:%M')}")
        
        # Buscar os candles disponíveis
        candles = await run_blocking_func(
            api_instance.get_candles,
            active,
            60,
            minutes_passed,
            line_end_time + (minutes_passed * 60)
        )
        
        if len(candles) < 1:
            logger.info(f"Sem candles para verificar resultado do bloco {datetime.fromtimestamp(block_time).strftime('%H:%M')}")
            return None
        
        logger.info(f"Analisando {len(candles)} candles para o bloco {datetime.fromtimestamp(block_time).strftime('%H:%M')}")
        
        # Verificar candles sequencialmente
        for i, candle in enumerate(candles):
            candle_direction = "DOJI" if candle['open'] == candle['close'] else "CALL" if candle['open'] < candle['close'] else "PUT"
            win = (signal == candle_direction)
            
            if win:
                logger.info(f"WIN no candle {i+1} para o bloco {datetime.fromtimestamp(block_time).strftime('%H:%M')}")
                return {"result": "WIN", "martingale": i}
            
            # Se estamos no último candle disponível e ainda não ganhou
            if i == len(candles) - 1:
                # Se já verificamos todos os 3 candles, é loss
                if i == 2 or minutes_passed >= 3:
                    logger.info(f"LOSS confirmado para o bloco {datetime.fromtimestamp(block_time).strftime('%H:%M')}")
                    return {"result": "LOSS", "martingale": 2}
                # Caso contrário, ainda não temos resultado definitivo
                logger.info(f"Sem resultado definitivo para o bloco {datetime.fromtimestamp(block_time).strftime('%H:%M')}")
                return None
                
        return None  # Ainda não temos resultado
    
    except Exception as e:
        logger.exception(f"Erro ao verificar resultado: {str(e)}")
        return None

# Gerar gráfico com Plotly (refatorada para ser assíncrona)
async def generate_chart(api_instance, active, data):
    """Gera um gráfico para o ativo usando a instância da API do usuário."""
    if not data:
        return None
    
    # Função interna para processamento bloqueante do gráfico
    def process_chart():
        try:
            # Verificar se precisamos buscar mais candles recentes para o gráfico
            current_time = int(time.time())
            
            # Preparar dados para o gráfico de candles
            candles_data = []
            for block in data:
                for candle in block["candles"]:
                    candles_data.append(candle)
            
            # Buscar candles adicionais
            if len(candles_data) > 0:
                latest_candle_time = max(candle["time"] for candle in candles_data)
                
                logger.info(f"Buscando candles adicionais para o gráfico. Último: {datetime.fromtimestamp(latest_candle_time).strftime('%H:%M:%S')}")
                
                # Buscar pelo menos os últimos 10 candles
                extra_candles_count = max(10, int((current_time - latest_candle_time) / 60) + 3)
                
                try:
                    # Buscar candles mais recentes
                    extra_candles = api_instance.get_candles(active, 60, extra_candles_count, current_time)
                    
                    for candle in extra_candles:
                        # Só adicionar candles que já não estão no dataset
                        if not any(c["time"] == candle["from"] for c in candles_data):
                            is_doji = candle['open'] == candle['close']
                            direction = "doji" if is_doji else "verde" if candle['open'] < candle['close'] else "vermelha"
                            candles_data.append({
                                "time": candle["from"],
                                "direction": direction,
                                "open": candle["open"],
                                "close": candle["close"],
                                "high": candle["max"],
                                "low": candle["min"]
                            })
                    
                    logger.info(f"Adicionados {len(extra_candles)} candles extras ao gráfico")
                except Exception as e:
                    logger.error(f"Erro ao buscar candles adicionais: {str(e)}")
            
            # Ordenar por tempo
            candles_data.sort(key=lambda x: x["time"])
            
            # Obter o intervalo de tempo para ajustar o eixo X
            if len(candles_data) > 0:
                min_time = min(candle["time"] for candle in candles_data)
                max_time = max(candle["time"] for candle in candles_data)
                time_buffer = (max_time - min_time) * 0.05  # 5% de buffer
                x_range = [
                    datetime.fromtimestamp(min_time - time_buffer),
                    datetime.fromtimestamp(max_time + time_buffer)
                ]
                
                # Calcular o intervalo do eixo Y
                all_highs = [candle["high"] for candle in candles_data]
                all_lows = [candle["low"] for candle in candles_data]
                y_min = min(all_lows)
                y_max = max(all_highs)
                y_buffer = (y_max - y_min) * 0.1  # 10% de buffer
                y_range = [y_min - y_buffer, y_max + y_buffer]
            else:
                x_range = None
                y_range = None
            
            # Criar figura do gráfico
            fig = go.Figure(data=[go.Candlestick(
                x=[datetime.fromtimestamp(candle["time"]) for candle in candles_data],
                open=[candle["open"] for candle in candles_data],
                high=[candle["high"] for candle in candles_data],
                low=[candle["low"] for candle in candles_data],
                close=[candle["close"] for candle in candles_data],
                increasing_line_color='#26a69a',  # Verde mais suave
                decreasing_line_color='#ef5350',  # Vermelho mais suave
                increasing_fillcolor='#26a69a',   
                decreasing_fillcolor='#ef5350',
                line=dict(width=1.5),             # Linhas mais grossas
                opacity=0.8                       # Leve transparência
            )])
            
            # Coletar posições das linhas
            grid_positions = []
            
            # Adicionar linhas verticais para delimitar blocos
            for i, block in enumerate(data):
                # Posição da linha 30 segundos antes do FINAL do bloco
                line_time = get_line_position(block["block_time"] + 300)
                line_position = datetime.fromtimestamp(line_time)
                
                # Adicionar à lista de posições
                grid_positions.append(line_position)
                
                # Adicionar linhas coloridas para blocos com resultados
                if block["result"] is not None:
                    # Definir cor da linha baseado no resultado
                    if block["result"] == "WIN" and block["martingale"] == 0:
                        color = "#00c853"  # Verde vibrante
                        width = 2
                    elif block["result"] == "WIN" and block["martingale"] == 1:
                        color = "#2979ff"  # Azul vibrante
                        width = 2
                    elif block["result"] == "WIN" and block["martingale"] == 2:
                        color = "#ffd600"  # Amarelo vibrante
                        width = 2
                    elif block["result"] == "LOSS":
                        color = "#f44336"  # Vermelho vibrante
                        width = 2
                    elif block["result"] == "NULO":
                        color = "#ffffff"  # Branco para blocos com doji
                        width = 2
                    else:
                        continue  # Pular blocos sem resultado definido
                    
                    # Adicionar linha vertical
                    fig.add_shape(
                        type="line",
                        x0=line_position,
                        y0=0,
                        x1=line_position,
                        y1=1,
                        yref="paper",
                        line=dict(
                            color=color,
                            width=width,
                            dash="solid"
                        )
                    )
                else:
                    # Linhas cinza para blocos sem resultado
                    fig.add_shape(
                        type="line",
                        x0=line_position,
                        y0=0,
                        x1=line_position,
                        y1=1,
                        yref="paper",
                        line=dict(
                            color="#555555",  # Cinza
                            width=1,
                            dash="solid"
                        )
                    )
            
            # Configurar layout
            fig.update_layout(
                title={
                    'text': f'Gráfico de {active} - Catalogação Estratégia Sodré',
                    'font': {'size': 24, 'color': '#ffffff'},
                    'y': 0.97,
                    'x': 0.5,
                    'xanchor': 'center',
                    'yanchor': 'top'
                },
                xaxis={
                    'title': 'Horário',
                    'title_font': {'size': 16},
                    'tickfont': {'size': 14},
                    'showgrid': False,
                    'gridcolor': '#333333',
                    'range': x_range,
                    'zeroline': False,
                    'autorange': True,
                },
                yaxis={
                    'title': 'Preço',
                    'title_font': {'size': 16},
                    'tickfont': {'size': 14},
                    'showgrid': True,
                    'gridcolor': '#333333',
                    'zeroline': False,
                    'range': y_range,
                    'autorange': True,
                },
                template='plotly_dark',
                plot_bgcolor='rgba(25, 25, 25, 0.8)',
                paper_bgcolor='rgba(25, 25, 25, 0.8)',
                height=700,
                autosize=True,
                margin=dict(l=50, r=50, t=70, b=50),
                hovermode='x',
                legend_orientation='h',
                legend=dict(
                    x=0.5,
                    y=1.02,
                    xanchor='center',
                    font=dict(size=14)
                ),
                showlegend=False
            )
            
            # Adicionar linhas de grid
            fig.update_xaxes(
                showline=True,
                linewidth=1,
                linecolor='#555555',
                mirror=True,
                rangeslider=dict(visible=False),
                autorange=True
            )
            
            fig.update_yaxes(
                showline=True,
                linewidth=1,
                linecolor='#555555',
                mirror=True,
                autorange=True
            )
            
            return fig.to_json()
        except Exception as e:
            logger.exception(f"Erro ao gerar gráfico: {str(e)}")
            return None
    
    # Executar o processamento do gráfico em um thread separado
    return await run_blocking_func(process_chart)

# Função para verificar se um ativo é do tipo binary
def is_binary_active(active_name):
    """Verifica se um ativo é do tipo binary."""
    logger.info(f"Verificando se o ativo '{active_name}' é do tipo binary")
    return True  # Aceitar todos os ativos disponíveis

# Função para obter ativos disponíveis (refatorada para receber api_instance)
async def get_available_actives(api_instance):
    """Obtém a lista de ativos disponíveis usando a instância da API do usuário."""
    if api_instance is None:
        logger.error("API não conectada ou None em get_available_actives")
        return []
    
    try:
        # Tentar obter do cache primeiro
        cache_key = "available_actives"
        cache_hit, cached_actives = cache_manager.get(cache_key)
        
        if cache_hit:
            logger.info("Cache hit para lista de ativos disponíveis")
            return cached_actives
        
        # Verificar conexão da API
        try:
            check_connection = await run_blocking_func(api_instance.check_connect)
            logger.info(f"Resultado de check_connect: {check_connection}")
            if not check_connection:
                logger.error("API não conectada (check_connect falhou)")
                return []
        except Exception as e:
            logger.error(f"Erro ao chamar check_connect: {str(e)}")
            return []
        
        # Obter payouts
        logger.info("Tentando obter payouts para todos os ativos...")
        all_profits = await run_blocking_func(api_instance.get_profit_all)
        
        binary_actives = []
        
        # Verificar se retornou um dicionário com chave 'binary'
        if isinstance(all_profits, dict) and 'binary' in all_profits:
            binary_data = all_profits['binary']
            
            if isinstance(binary_data, dict):
                # Iterar sobre ativos 'binary'
                for asset_name, asset_info in binary_data.items():
                    if isinstance(asset_info, dict) and 'payout' in asset_info:
                        payout = asset_info['payout']
                        if isinstance(payout, (int, float)) and payout > 0:
                            logger.info(f"Ativo Binary Válido: {asset_name}, Payout: {payout}")
                            binary_actives.append(asset_name)
            else:
                logger.error(f"Formato inesperado para dados de 'binary': {type(binary_data)}")
        else:
            logger.error(f"Chave 'binary' não encontrada ou formato inesperado: {type(all_profits)}")
        
        # Armazenar no cache por 5 minutos
        if binary_actives:
            cache_manager.set(cache_key, sorted(binary_actives), ttl=300)
        
        logger.info(f"{len(binary_actives)} ativos 'binary' disponíveis")
        return sorted(binary_actives)
    
    except Exception as e:
        logger.exception(f"Erro geral em get_available_actives: {str(e)}")
        return []

# Função para atualizar estatísticas de um ativo (refatorada para usar connection_manager)
def update_asset_stats(user_id, active, data):
    """Atualiza estatísticas de um ativo para um usuário específico."""
    if not data or "data" not in data or not data["data"]:
        logger.warning(f"Sem dados para atualizar estatísticas de {active}")
        return False
    
    try:
        # Obter dados do usuário
        user_data = connection_manager.get_user_data(user_id)
        if not user_data:
            logger.error(f"Usuário {user_id} não encontrado para atualizar estatísticas")
            return False
        
        # Inicializar estatísticas para este ativo se não existirem
        if "stats" not in user_data or active not in user_data["stats"]:
            user_data["stats"][active] = {
                "wins": 0,
                "losses": 0,
                "win_rate": 0,
                "martingale1_wins": 0,
                "martingale2_wins": 0,
                "direct_wins": 0,
                "analyzed_blocks": 0,
                "last_update": int(time.time())
            }
        
        stats = user_data["stats"][active]
        
        # Contar blocos com resultados definidos
        wins = 0
        losses = 0
        direct_wins = 0
        martingale1_wins = 0
        martingale2_wins = 0
        total_blocks = 0
        
        for block in data["data"]:
            if block["result"] is not None and block["result"] != "NULO":
                total_blocks += 1
                
                if block["result"] == "WIN":
                    wins += 1
                    if block["martingale"] == 0:
                        direct_wins += 1
                    elif block["martingale"] == 1:
                        martingale1_wins += 1
                    elif block["martingale"] == 2:
                        martingale2_wins += 1
                elif block["result"] == "LOSS":
                    losses += 1
        
        # Atualizar estatísticas
        stats["wins"] = wins
        stats["losses"] = losses
        stats["direct_wins"] = direct_wins
        stats["martingale1_wins"] = martingale1_wins
        stats["martingale2_wins"] = martingale2_wins
        stats["analyzed_blocks"] = total_blocks
        stats["win_rate"] = round((wins / total_blocks * 100) if total_blocks > 0 else 0, 2)
        stats["last_update"] = int(time.time())
        
        # Atualizar no connection_manager
        connection_manager.update_user_state(user_id, "stats", user_data["stats"])
        logger.info(f"Estatísticas de {active} atualizadas para usuário {user_id}")
        
        return True
    
    except Exception as e:
        logger.exception(f"Erro ao atualizar estatísticas de {active}: {str(e)}")
        return False

# Função para formatar nome de ativo
def format_asset_name(asset_name):
    """Formata nome de ativo para exibição."""
    # Remover sufixo '-OTC' e adicionar ' (OTC)' no final para ativos OTC
    if asset_name.endswith('-OTC'):
        return asset_name[:-4] + ' (OTC)'
    # Remover sufixo '-OTC-L' e adicionar ' (OTC)' no final
    elif asset_name.endswith('-OTC-L'):
        return asset_name[:-6] + ' (OTC)'
    # Remover sufixo '-op' e adicionar ' (Mercado Aberto)' no final
    elif asset_name.endswith('-op'):
        return asset_name[:-3] + ' (Mercado Aberto)'
    return asset_name 