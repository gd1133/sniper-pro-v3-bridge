import ccxt
import time
import os
import requests
import sys
import json
from dotenv import load_dotenv

# Importação dos módulos Master
try:
    from bot_logic import ReversalStrategy
    from scanner import get_market_movers
except ImportError as e:
    print(f"❌ Erro Crítico: Ficheiros de lógica não encontrados: {e}")
    sys.exit(1)

load_dotenv()

# --- CONFIGURAÇÕES DE AMBIENTE ---
BINANCE_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_SECRET = os.getenv("BINANCE_SECRET_KEY")
API_URL = "http://localhost:3000/api/update"

class AlphaTraderMaster5m:
    def __init__(self):
        """
        Sniper IA V3 - Versão Ultra 5.0 (AGRESSIVA)
        Foco: Alinhamento Macro + Gatilho Rápido de Volume.
        """
        self.exchange = ccxt.binanceusdm({
            'apiKey': BINANCE_KEY,
            'secret': BINANCE_SECRET,
            'enableRateLimit': True,
            'options': {
                'adjustForTimeDifference': True, # Já existe
                'recvWindow': 10000,             # Aumente para 10000 se o erro persistir
                'defaultType': 'future',
            }
        })
        
        self.strategy = ReversalStrategy(self.exchange)
        self.trade_memory = {}
        self.last_scan_time = 0 
        
        try:
            print("📡 Sincronizando mercados de Futuros (USDT-M)...")
            self.exchange.load_markets()
            print("✅ Conexão Estabelecida! Sniper Ultra 5.0 Online.")
        except Exception as e:
            print(f"❌ Falha ao conectar: {e}")
            sys.exit(1)

    def sync_ui(self, market_data, log_msg, log_type="info"):
        try:
            payload = {
                "market_data": market_data,
                "log": {
                    "type": log_type,
                    "time": time.strftime("%H:%M:%S"),
                    "message": log_msg
                }
            }
            requests.post(API_URL, json=payload, timeout=1)
        except Exception: 
            pass

    def run_engine(self):
        print("\n" + "="*50)
        print("🚀 SNIPER MASTER 5.0 - MODO AGRESSIVO ATIVADO")
        print("💰 Risco: 35% por Trade | Saída: Mudança de Direção")
        print("💡 Monitoramento: 15s | Pensamento Rápido: 1m")
        print("="*50 + "\n")

        while True:
            try:
                # 1. ATUALIZAÇÃO DE SALDO
                balance_data = self.exchange.fetch_balance()
                usdt_balance = balance_data['total'].get('USDT', 0)
                
                # 2. MONITORAMENTO ATIVO DE POSIÇÕES
                raw_positions = self.exchange.fetch_positions()
                active_pos = [p for p in raw_positions if float(p['info']['positionAmt']) != 0]
                num_pos = len(active_pos)

                for pos in active_pos:
                    sym = pos['symbol']
                    amt = float(pos['info']['positionAmt'])
                    side = 'LONG' if amt > 0 else 'SHORT'
                    entry = float(pos['entryPrice'])
                    
                    if sym not in self.trade_memory:
                        self.trade_memory[sym] = {'entry': entry, 'peak': entry, 'start_time': time.time()}
                    
                    should_exit, reason, pnl, last_price = self.strategy.monitor_trend_follow(
                        sym, side, entry, self.trade_memory[sym]['peak']
                    )
                    
                    self.trade_memory[sym]['peak'] = last_price

                    if should_exit:
                        close_side = 'sell' if side == 'LONG' else 'buy'
                        self.exchange.create_market_order(sym, close_side, abs(amt), params={'reduceOnly': True})
                        
                        self.sync_ui(
                            {"pnl": f"{pnl:.2f}%", "balance": usdt_balance, "symbol": sym}, 
                            f"💰 OPERAÇÃO ENCERRADA: {sym} | PNL: {pnl:.2f}% | Motivo: {reason}", 
                            "success"
                        )
                        print(f"✅ FECHAMENTO: {sym} | {reason} | PNL: {pnl:.2f}%")
                        self.trade_memory.pop(sym, None)
                    else:
                        self.sync_ui(
                            {"symbol": sym, "pnl": f"{pnl:+.2f}%", "balance": usdt_balance, "price": last_price}, 
                            f"🏄 Surfando onda em {sym}...", 
                            "info"
                        )

                # 3. SCANNER DE ENTRADA (Ajustado para 60 segundos - 1 minuto)
                current_time = time.time()
                if num_pos < 3 and (current_time - self.last_scan_time) >= 60:
                    print(f"🔍 [IA AGRESSIVA] Varrendo mercado por oportunidades rápidas...")
                    trending_list = get_market_movers(self.exchange, limit=15)
                    
                    for coin in trending_list:
                        if any(p['symbol'] == coin for p in active_pos): continue
                        
                        analysis = self.strategy.check_dual_trend(coin)
                        
                        # Score reduzido para 7 para ser mais agressivo nas entradas
                        if analysis['score'] >= 7:
                            ticker = self.exchange.fetch_ticker(coin)
                            price = ticker['last']
                            qty = self.strategy.calculate_safe_amount(self.exchange.market(coin), price, usdt_balance)
                            
                            if qty > 0:
                                order_side = 'buy' if analysis['trend'] == 'LONG' else 'sell'
                                self.exchange.create_market_order(coin, order_side, qty)
                                self.trade_memory[coin] = {'entry': price, 'peak': price, 'start_time': time.time()}
                                
                                self.sync_ui(
                                    {"symbol": coin, "analysis": analysis['reason'], "pnl": "0.00%", "balance": usdt_balance, "price": price}, 
                                    f"🔥 ENTRADA AGRESSIVA: {analysis['reason']}", 
                                    "ai_voice"
                                )
                                print(f"🚀 GATILHO DISPARADO: {analysis['trend']} em {coin}! (Score: {analysis['score']})")
                                break 
                    
                    self.last_scan_time = current_time

                # Monitoramento mais rápido (15 segundos)
                time.sleep(15)

            except Exception as e:
                if "timestamp" in str(e).lower():
                    self.exchange.load_markets()
                else:
                    print(f"⚠️ Erro no Motor Master: {e}")
                time.sleep(15)

if __name__ == "__main__":
    try:
        AlphaTraderMaster5m().run_engine()
    except KeyboardInterrupt:
        print("\n👋 Robô finalizado pelo usuário.")
        sys.exit(0)