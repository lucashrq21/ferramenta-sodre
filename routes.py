import time
import json
import logging
from datetime import datetime
from functools import wraps
import random

from flask import (
    render_template, 
    request, 
    jsonify, 
    session, 
    redirect, 
    url_for
)

from estrategia_minoria import (
    app, 
    generate_user_id, 
    format_asset_name, 
    is_binary_active, 
    update_asset_stats, 
    connection_manager, 
    ativos_recomendados,
    connect_to_polarium,
    analyze_candles,
    generate_chart,
    get_available_actives
)
# Importar async_utils diretamente
import async_utils

logger = logging.getLogger("routes")

# Decorador para verificar se o usuário está autenticado
def login_required(f):
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('index'))
        
        # Verificar se a conexão ainda existe
        user_data = connection_manager.get_user_data(user_id)
        if not user_data or not user_data.get('connected', False):
            # Se a conexão foi perdida, limpar a sessão
            session.clear()
            return redirect(url_for('index'))
        
        return await f(*args, **kwargs)
    return decorated_function

# Página inicial / login
@app.route('/')
async def index():
    """Página inicial com formulário de login ou interface principal se autenticado."""
    user_id = session.get('user_id')
    
    # Se já estiver logado
    if user_id:
        user_data = connection_manager.get_user_data(user_id)
        if user_data and user_data.get('connected', False):
            try:
                # Obter lista de ativos disponíveis
                api_instance = user_data['api']
                raw_active_list = await get_available_actives(api_instance)
                active_list = [(asset, format_asset_name(asset)) for asset in raw_active_list]
                logger.info(f"Renderizando index.html com {len(active_list)} ativos para usuário {user_id}")
                return render_template('index.html', actives=active_list, connected=True)
            except Exception as e:
                logger.exception(f"Erro ao obter ativos para usuário {user_id}: {str(e)}")
    
    # Se não estiver logado ou ocorreu erro
    logger.info("Renderizando index.html sem login")
    return render_template('index.html', actives=[], connected=False)

# Rota de conexão
@app.route('/connect', methods=['POST'])
async def connect():
    """Conecta à API Polarium."""
    email = request.form.get('email')
    password = request.form.get('password')
    
    logger.info(f"Tentando conectar com email: {email}")
    success, message, api_instance, reason = await connect_to_polarium(email, password)
    
    if success:
        # Gerar ID de usuário e armazenar na sessão
        user_id = generate_user_id()
        session['user_id'] = user_id
        
        # Adicionar conexão ao gerenciador
        connection_manager.add_connection(user_id, api_instance)
        logger.info(f"Conexão bem-sucedida para usuário {user_id}")
        
        # Tentar obter informações básicas para verificar a conexão
        try:
            balance = await async_utils.run_blocking_func(api_instance.get_balance)
            logger.info(f"Saldo após conexão para usuário {user_id}: {balance}")
        except Exception as e:
            logger.error(f"Erro ao obter saldo para usuário {user_id}: {str(e)}")
        
        return jsonify({"success": True, "message": message})
    elif reason == "2FA":
        # Armazenar API temporária na sessão para verificação 2FA
        session['temp_api'] = api_instance
        logger.info("2FA requerido")
        return jsonify({"success": False, "message": "2FA requerido", "require_2fa": True})
    else:
        logger.error(f"Falha na conexão: {message}")
        return jsonify({"success": False, "message": message})

# Rota de verificação 2FA
@app.route('/verify_2fa', methods=['POST'])
async def verify_2fa():
    """Verifica código de autenticação de dois fatores."""
    code = request.form.get('code')
    temp_api = session.get('temp_api')
    
    if not temp_api:
        logger.error("Tentativa de verificar 2FA sem API temporária")
        return jsonify({"success": False, "message": "API não inicializada"})
    
    try:
        logger.info(f"Tentando autenticar com código 2FA")
        success, reason = await async_utils.run_blocking_func(temp_api.connect, code)
        
        if success:
            logger.info("Autenticação 2FA bem-sucedida")
            # Alterar para conta de prática
            await async_utils.run_blocking_func(temp_api.change_balance, 'PRACTICE')
            
            # Verificar conexão
            if not await async_utils.run_blocking_func(temp_api.check_connect):
                logger.error("Falha no check_connect após 2FA bem-sucedido")
                return jsonify({"success": False, "message": "Falha ao estabelecer conexão estável após 2FA"})
            
            # Verificar acesso aos dados fundamentais
            try:
                balance = await async_utils.run_blocking_func(temp_api.get_balance)
                logger.info(f"Saldo obtido após 2FA: {balance}")
            except Exception as e:
                logger.error(f"Erro ao verificar dados após 2FA: {str(e)}")
                return jsonify({"success": False, "message": f"Erro ao estabelecer conexão após 2FA: {str(e)}"})
            
            # Gerar ID de usuário e armazenar na sessão
            user_id = generate_user_id()
            session['user_id'] = user_id
            
            # Adicionar conexão ao gerenciador
            connection_manager.add_connection(user_id, temp_api)
            
            # Limpar API temporária da sessão
            session.pop('temp_api', None)
            
            logger.info(f"Conexão 2FA verificada para usuário {user_id}")
            return jsonify({"success": True, "message": "Conectado com sucesso!"})
        else:
            logger.error(f"Falha na autenticação 2FA: {reason}")
            return jsonify({"success": False, "message": f"Erro na verificação 2FA: {reason}"})
    except Exception as e:
        logger.exception(f"Exceção durante autenticação 2FA: {str(e)}")
        return jsonify({"success": False, "message": f"Erro ao verificar 2FA: {str(e)}"})

# Rota para atualizar lista de ativos
@app.route('/refresh_actives', methods=['POST'])
@login_required
async def refresh_actives():
    """Atualiza a lista de ativos disponíveis."""
    user_id = session['user_id']
    user_data = connection_manager.get_user_data(user_id)
    api_instance = user_data['api']
    
    try:
        # Verificar conexão
        check = await async_utils.run_blocking_func(api_instance.check_connect)
        if not check:
            logger.error(f"API não conectada para usuário {user_id} em refresh_actives")
            connection_manager.update_connection_status(user_id, False)
            return jsonify({"success": False, "message": "API desconectada, faça login novamente"})
        
        # Obter lista de ativos
        raw_active_list = await get_available_actives(api_instance)
        if not raw_active_list:
            logger.error(f"Nenhum ativo retornado para usuário {user_id}")
            return jsonify({"success": False, "message": "Nenhum ativo disponível no momento"})
        
        # Formatar lista de ativos
        formatted_list = []
        for asset in raw_active_list:
            if is_binary_active(asset):
                formatted_list.append({
                    "id": asset,
                    "name": format_asset_name(asset)
                })
        
        logger.info(f"{len(formatted_list)} ativos formatados para usuário {user_id}")
        return jsonify({"success": True, "actives": formatted_list})
    
    except Exception as e:
        logger.exception(f"Erro ao atualizar ativos para usuário {user_id}: {str(e)}")
        return jsonify({"success": False, "message": f"Erro ao atualizar ativos: {str(e)}"})

# Rota para verificar conexão
@app.route('/check_connection', methods=['POST'])
@login_required
async def check_connection():
    """Verifica se a conexão com a API ainda está ativa."""
    user_id = session['user_id']
    user_data = connection_manager.get_user_data(user_id)
    api_instance = user_data['api']
    
    try:
        # Verificar conexão
        check = await async_utils.run_blocking_func(api_instance.check_connect)
        if check:
            logger.info(f"Conexão verificada para usuário {user_id}")
            connection_manager.update_connection_status(user_id, True)
            return jsonify({"connected": True})
        else:
            logger.warning(f"Conexão perdida para usuário {user_id}")
            connection_manager.update_connection_status(user_id, False)
            return jsonify({"connected": False})
    except Exception as e:
        logger.exception(f"Erro ao verificar conexão para usuário {user_id}: {str(e)}")
        connection_manager.update_connection_status(user_id, False)
        return jsonify({"connected": False, "error": str(e)})

# Rota para analisar um ativo
@app.route('/analyze', methods=['POST'])
@login_required
async def analyze():
    """Analisa um ativo específico."""
    user_id = session['user_id']
    user_data = connection_manager.get_user_data(user_id)
    api_instance = user_data['api']
    user_lock = user_data['lock']
    
    active = request.form.get('active')
    num_blocks = int(request.form.get('num_blocks', 10))
    
    logger.info(f"Analisando {active} com {num_blocks} blocos para usuário {user_id}")
    
    with user_lock:  # Usar lock específico do usuário
        try:
            # Verificar conexão
            check = await async_utils.run_blocking_func(api_instance.check_connect)
            if not check:
                logger.error(f"API não conectada para usuário {user_id} em analyze")
                connection_manager.update_connection_status(user_id, False)
                return jsonify({"success": False, "message": "API desconectada, faça login novamente"})
            
            # Analisar candles
            results = await analyze_candles(api_instance, active, 60, num_blocks)
            
            if "error" in results:
                logger.error(f"Erro na análise para usuário {user_id}: {results['error']}")
                return jsonify({"success": False, "message": results["error"]})
            
            # Atualizar estatísticas
            update_asset_stats(user_id, active, results)
            
            # Armazenar resultados para uso posterior
            user_data = connection_manager.get_user_data(user_id)
            if "last_results" not in user_data:
                user_data["last_results"] = {}
            user_data["last_results"][active] = results
            connection_manager.update_user_state(user_id, "last_results", user_data["last_results"])
            
            # Gerar gráfico
            chart_json = await generate_chart(api_instance, active, results["data"])
            
            if not chart_json:
                logger.error(f"Falha ao gerar gráfico para usuário {user_id}")
                return jsonify({"success": False, "message": "Falha ao gerar gráfico"})
            
            # Atualizar ranking de top 5 após análise individual
            user_data = connection_manager.get_user_data(user_id)
            if "stats" in user_data:
                # Simplificar a lógica - verificar apenas a flag de ranking limpo
                # Se a flag for False ou não existir, permitir atualização do ranking
                if not user_data.get('ranking_cleared', False):
                    asset_stats = user_data["stats"]
                    
                    # Ordenar ativos por taxa de sucesso e depois por vitórias na primeira entrada
                    top_assets = sorted(
                        [(active_id, stats) for active_id, stats in asset_stats.items()],
                        key=lambda x: (x[1]["win_rate"], x[1]["direct_wins"]),
                        reverse=True
                    )[:5]
                    
                    # Preparar dados para o ranking
                    top5_data = [
                        {
                            "active": format_asset_name(active_id),
                            "active_id": active_id,
                            "win_rate": stats["win_rate"],
                            "wins": stats["wins"],
                            "losses": stats["losses"],
                            "analyzed_blocks": stats["analyzed_blocks"],
                            "direct_wins": stats["direct_wins"],
                            "martingale1_wins": stats["martingale1_wins"],
                            "martingale2_wins": stats["martingale2_wins"],
                            "total_operations": stats["wins"] + stats["losses"],
                            "win_first": stats["direct_wins"],
                            "win_g1": stats["martingale1_wins"],
                            "win_g2": stats["martingale2_wins"],
                            "loss": stats["losses"],
                            "name": format_asset_name(active_id),
                            "last_update": int(time.time())
                        }
                        for active_id, stats in top_assets
                    ]
                    
                    # Salvar no user_data
                    connection_manager.update_user_state(user_id, "top5_ativos", top5_data)
                    
                    # Atualizar diretamente o objeto user_data também
                    user_data['top5_ativos'] = top5_data
                    
                    logger.info(f"Ranking atualizado após análise de {active} para usuário {user_id}")
                else:
                    logger.info(f"Ranking não atualizado após análise de {active} porque foi limpo pelo usuário {user_id}")
            
            logger.info(f"Análise de {active} concluída para usuário {user_id}")
            return jsonify({"success": True, "results": results, "chart": chart_json, "active": active})
        
        except Exception as e:
            logger.exception(f"Erro ao analisar {active} para usuário {user_id}: {str(e)}")
            return jsonify({"success": False, "message": f"Erro na análise: {str(e)}"})

# Rota para recarregar gráfico
@app.route('/reload_chart', methods=['POST'])
@login_required
async def reload_chart():
    """Recarrega o gráfico para um ativo específico."""
    user_id = session['user_id']
    user_data = connection_manager.get_user_data(user_id)
    api_instance = user_data['api']
    user_lock = user_data['lock']
    
    active = request.form.get('active')
    
    logger.info(f"Recarregando gráfico para {active} para usuário {user_id}")
    
    with user_lock:
        try:
            # Verificar se há resultados armazenados
            if "last_results" not in user_data or active not in user_data["last_results"]:
                logger.error(f"Nenhum resultado armazenado para {active} - usuário {user_id}")
                return jsonify({"success": False, "message": f"Nenhum resultado encontrado para {active}"})
            
            results = user_data["last_results"][active]
            
            # Gerar gráfico
            chart_json = await generate_chart(api_instance, active, results["data"])
            
            if not chart_json:
                logger.error(f"Falha ao gerar gráfico para usuário {user_id}")
                return jsonify({"success": False, "message": "Falha ao gerar gráfico"})
            
            logger.info(f"Gráfico recarregado para {active} - usuário {user_id}")
            return jsonify({"success": True, "chart": chart_json, "active": active})
        
        except Exception as e:
            logger.exception(f"Erro ao recarregar gráfico para {active} - usuário {user_id}: {str(e)}")
            return jsonify({"success": False, "message": f"Erro ao recarregar gráfico: {str(e)}"})

# Rota para analisar os 5 melhores ativos
@app.route('/analyze_top5', methods=['POST'])
@login_required
async def analyze_top5():
    """Analisa os 5 melhores ativos de todos os disponíveis."""
    user_id = session['user_id']
    user_data = connection_manager.get_user_data(user_id)
    api_instance = user_data['api']
    user_lock = user_data['lock']
    
    num_blocks = int(request.form.get('num_blocks', 10))
    
    logger.info(f"Iniciando análise de todos os ativos disponíveis para usuário {user_id}")
    
    # Resetar a flag de ranking limpo ao iniciar uma análise completa
    if user_data.get('ranking_cleared', False):
        user_data['ranking_cleared'] = False
        connection_manager.update_user_state(user_id, "ranking_cleared", False)
        logger.info(f"Flag de ranking limpo resetada para usuário {user_id} durante análise completa")
    
    # Inicializar progresso da análise
    analysis_progress = {
        "in_progress": True,
        "total_assets": 0,  # Será atualizado após obter a lista de ativos
        "analyzed_assets": 0,
        "current_asset": "",
        "percent_complete": 0,
        "success_count": 0,
        "start_time": int(time.time())
    }
    connection_manager.update_user_state(user_id, "analysis_progress", analysis_progress)
    
    with user_lock:
        try:
            # Verificar conexão
            check = await async_utils.run_blocking_func(api_instance.check_connect)
            if not check:
                logger.error(f"API não conectada para usuário {user_id} em analyze_top5")
                connection_manager.update_connection_status(user_id, False)
                return jsonify({"success": False, "message": "API desconectada, faça login novamente"})
                
            # Obter lista de ativos disponíveis
            logger.info(f"Obtendo lista de ativos disponíveis para usuário {user_id}")
            available_actives = await get_available_actives(api_instance)
            
            if not available_actives:
                logger.error(f"Nenhum ativo disponível para usuário {user_id}")
                # Atualizar progresso para finalizado
                analysis_progress["in_progress"] = False
                connection_manager.update_user_state(user_id, "analysis_progress", analysis_progress)
                return jsonify({"success": False, "message": "Nenhum ativo disponível para análise"})
                
            # Filtrar apenas ativos binary e limitar aos primeiros 50
            selected_actives = [active for active in available_actives if is_binary_active(active)][:50]
            logger.info(f"Selecionados {len(selected_actives)} ativos binary para análise (limitado a 50)")
            
            # Atualizar total de ativos no progresso
            analysis_progress["total_assets"] = len(selected_actives)
            connection_manager.update_user_state(user_id, "analysis_progress", analysis_progress)
            
            logger.info(f"Iniciando análise de {len(selected_actives)} ativos binary disponíveis")
            
            # Inicializar resultados
            all_results = {}
            asset_stats = {}
            analysis_results = {}  # Dicionário para rastrear resultados de cada ativo
            
            # Analisar cada ativo selecionado
            for i, active in enumerate(selected_actives):
                # Verificar se a análise foi cancelada
                if not user_data.get("analysis_progress", {}).get("in_progress", True):
                    logger.info(f"Análise cancelada pelo usuário {user_id} após analisar {i} ativos")
                    analysis_results["canceled"] = True
                    break
                    
                try:
                    # Atualizar progresso
                    analysis_progress["current_asset"] = active
                    analysis_progress["analyzed_assets"] = i
                    analysis_progress["percent_complete"] = round((i / len(selected_actives)) * 100)
                    connection_manager.update_user_state(user_id, "analysis_progress", analysis_progress)
                    
                    logger.info(f"Analisando ativo {i+1}/{len(selected_actives)}: {active} para usuário {user_id}")
                    
                    # Analisar candles com o mesmo método usado na análise individual
                    results = await analyze_candles(api_instance, active, 60, num_blocks)
                    
                    if "error" not in results:
                        # Armazenar resultados
                        all_results[active] = results
                        analysis_results[active] = "Sucesso"
                        
                        # Atualizar estatísticas
                        update_asset_stats(user_id, active, results)
                        
                        # Obter estatísticas atualizadas
                        user_data = connection_manager.get_user_data(user_id)
                        if "stats" in user_data and active in user_data["stats"]:
                            asset_stats[active] = user_data["stats"][active]
                            analysis_progress["success_count"] += 1
                    else:
                        analysis_results[active] = f"Erro: {results['error']}"
                        logger.error(f"Erro ao analisar {active} para usuário {user_id}: {results['error']}")
                except Exception as e:
                    analysis_results[active] = f"Erro: {str(e)}"
                    logger.exception(f"Erro ao analisar {active} para usuário {user_id}: {str(e)}")
            
            # Finalizar progresso
            analysis_progress["in_progress"] = False
            analysis_progress["analyzed_assets"] = len(selected_actives)
            analysis_progress["percent_complete"] = 100
            connection_manager.update_user_state(user_id, "analysis_progress", analysis_progress)
            
            # Se a análise foi cancelada pelo usuário, usar os resultados parciais
            canceled = False
            if analysis_results.get("canceled", False):
                canceled = True
                logger.info(f"Finalizando análise cancelada para usuário {user_id} - Usando resultados parciais")
                
            # Ordenar ativos por taxa de sucesso e depois por vitórias na primeira entrada
            top_assets = sorted(
                [(active, stats) for active, stats in asset_stats.items()],
                key=lambda x: (x[1]["win_rate"], x[1]["direct_wins"]),
                reverse=True
            )[:5]
            
            # Preparar dados para retorno
            top5_data = [
                {
                    "active": format_asset_name(active),
                    "active_id": active,
                    "win_rate": stats["win_rate"],
                    "wins": stats["wins"],
                    "losses": stats["losses"],
                    "analyzed_blocks": stats["analyzed_blocks"],
                    "direct_wins": stats["direct_wins"],
                    "martingale1_wins": stats["martingale1_wins"],
                    "martingale2_wins": stats["martingale2_wins"],
                    "total_operations": stats["wins"] + stats["losses"],
                    "win_first": stats["direct_wins"],
                    "win_g1": stats["martingale1_wins"],
                    "win_g2": stats["martingale2_wins"],
                    "loss": stats["losses"],
                    "name": format_asset_name(active),
                    "last_update": int(time.time())
                }
                for active, stats in top_assets
            ]
            
            # Salvar top5_data na chave 'top5_ativos' do user_data
            connection_manager.update_user_state(user_id, "top5_ativos", top5_data)
            
            # Atualizar também o objeto user_data atual
            user_data = connection_manager.get_user_data(user_id)
            user_data['top5_ativos'] = top5_data
            
            logger.info(f"Análise top 5 concluída para usuário {user_id} - Analisados {len(selected_actives)} ativos")
            return jsonify({
                "success": True, 
                "top5": top5_data,
                "results": analysis_results,  # Incluir resultados da análise na resposta
                "total_analyzed": len(selected_actives),
                "successful_analysis": analysis_progress["success_count"],
                "canceled": canceled
            })
        
        except Exception as e:
            # Finalizar progresso em caso de erro
            analysis_progress = user_data["analysis_progress"]
            analysis_progress["in_progress"] = False
            connection_manager.update_user_state(user_id, "analysis_progress", analysis_progress)
            
            logger.exception(f"Erro na análise top 5 para usuário {user_id}: {str(e)}")
            return jsonify({"success": False, "message": f"Erro na análise top 5: {str(e)}"})

# Rota para obter progresso da análise top 5
@app.route('/get_analysis_progress', methods=['POST', 'GET'])
@login_required
async def get_analysis_progress():
    """Retorna o progresso atual da análise top 5."""
    user_id = session['user_id']
    user_data = connection_manager.get_user_data(user_id)
    
    # Inicializar resposta com valores padrão
    response = {"in_progress": False}
    
    # Adicionar status da flag de ranking
    response["ranking_cleared"] = user_data.get('ranking_cleared', False)
    
    # Adicionar informações de progresso se disponíveis
    if "analysis_progress" in user_data:
        progress = user_data["analysis_progress"]
        response.update(progress)
        
        # Adicionar informações de tempo estimado
        if progress["in_progress"] and progress["analyzed_assets"] > 0:
            elapsed_time = int(time.time()) - progress["start_time"]
            assets_remaining = progress["total_assets"] - progress["analyzed_assets"]
            time_per_asset = elapsed_time / progress["analyzed_assets"]
            estimated_time_remaining = int(assets_remaining * time_per_asset)
            response["estimated_time_remaining"] = estimated_time_remaining
            response["elapsed_time"] = elapsed_time
    
    return jsonify(response)

# Rota para fazer logout
@app.route('/logout', methods=['POST'])
async def logout():
    """Encerra a sessão do usuário e remove sua conexão."""
    user_id = session.get('user_id')
    if user_id:
        # Remover conexão do gerenciador
        connection_manager.remove_connection(user_id)
        logger.info(f"Conexão removida para usuário {user_id}")
    
    # Limpar sessão
    session.clear()
    
    return jsonify({"success": True})

# Rota para a página de Top 5 ativos
@app.route('/top_ativos')
@login_required
async def top_ativos():
    """Página de exibição dos 5 melhores ativos."""
    user_id = session['user_id']
    user_data = connection_manager.get_user_data(user_id)
    
    # Verificar se existe ranking computado
    if 'top5_ativos' in user_data:
        top5 = user_data['top5_ativos']
        for ativo in top5:
            if 'last_update' not in ativo:
                ativo['last_update'] = time.time()
        logger.info(f"Retornando top 5 ativos para usuário {user_id}")
        return render_template('top_ativos.html', top5=top5, connected=True)
    else:
        logger.info(f"Nenhum ativo analisado ainda para usuário {user_id}")
        return render_template('top_ativos.html', top5=[], connected=True)

# Rota para limpar o ranking
@app.route('/clear_ranking', methods=['POST'])
@login_required
async def clear_ranking():
    """Limpa o ranking de ativos analisados."""
    user_id = session['user_id']
    user_data = connection_manager.get_user_data(user_id)
    
    try:
        # Remover o ranking dos dados do usuário
        if 'top5_ativos' in user_data:
            del user_data['top5_ativos']
            
            # Definir flag indicando que o ranking foi explicitamente limpo pelo usuário
            user_data['ranking_cleared'] = True
            connection_manager.update_user_state(user_id, "ranking_cleared", True)
            
            logger.info(f"Ranking de ativos limpo e flag definida para usuário {user_id}")
            return jsonify({"success": True, "message": "Ranking limpo com sucesso"})
        else:
            # Definir a flag mesmo se não houver ranking para limpar
            user_data['ranking_cleared'] = True
            connection_manager.update_user_state(user_id, "ranking_cleared", True)
            
            logger.info(f"Não há ranking para limpar, mas flag definida para usuário {user_id}")
            return jsonify({"success": True, "message": "Não há ranking para limpar"})
    except Exception as e:
        logger.exception(f"Erro ao limpar ranking para usuário {user_id}: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

# Rota para cancelar a análise em andamento
@app.route('/cancel_analysis', methods=['POST'])
@login_required
async def cancel_analysis():
    """Cancela a análise de ativos em andamento."""
    user_id = session['user_id']
    user_data = connection_manager.get_user_data(user_id)
    
    try:
        # Verificar se há uma análise em andamento
        if "analysis_progress" in user_data and user_data["analysis_progress"].get("in_progress", False):
            # Marcar a análise como cancelada
            user_data["analysis_progress"]["in_progress"] = False
            user_data["analysis_progress"]["canceled"] = True
            user_data["analysis_progress"]["percent_complete"] = 100
            connection_manager.update_user_state(user_id, "analysis_progress", user_data["analysis_progress"])
            logger.info(f"Análise cancelada para usuário {user_id}")
            return jsonify({"success": True, "message": "Análise cancelada com sucesso"})
        else:
            logger.info(f"Não há análise em andamento para cancelar para usuário {user_id}")
            return jsonify({"success": True, "message": "Não há análise em andamento para cancelar"})
    except Exception as e:
        logger.exception(f"Erro ao cancelar análise para usuário {user_id}: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

# Rota para alternar comportamento do ranking
@app.route('/toggle_ranking_behavior', methods=['POST'])
@login_required
async def toggle_ranking_behavior():
    """Alterna o comportamento do ranking (manter limpo ou atualizar após análises)."""
    user_id = session['user_id']
    user_data = connection_manager.get_user_data(user_id)
    
    try:
        # Inverter o valor atual da flag
        current_value = user_data.get('ranking_cleared', False)
        new_value = not current_value
        
        # Atualizar o valor
        user_data['ranking_cleared'] = new_value
        connection_manager.update_user_state(user_id, "ranking_cleared", new_value)
        
        message = "Ranking será mantido limpo após análises individuais" if new_value else "Ranking será atualizado após análises individuais"
        logger.info(f"Comportamento do ranking alterado para usuário {user_id}: {message}")
        
        return jsonify({
            "success": True, 
            "ranking_cleared": new_value,
            "message": message
        })
    except Exception as e:
        logger.exception(f"Erro ao alternar comportamento do ranking para usuário {user_id}: {str(e)}")
        return jsonify({"success": False, "error": str(e)}) 