import ccxt
import time
import os
import requests
from dotenv import load_dotenv

# Importação da inteligência e do scanner de alta volatilidade
from bot_logic import ReversalStrategy
from scanner import get_market_movers

# --- CARREGAMENTO DE CONFIGURAÇÕES ---
load_dotenv()

# Credenciais lidas do ficheiro .env para segurança
BINANCE_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_SECRET = os.getenv("BINANCE_SECRET_KEY")
API_URL = "http://127.0.0.1:3000/api/update"

# PARÂMETROS OPERACIONAIS (Calibrados para Banca de $35)
MAX_SLOTS = 2               # Quantas moedas operam ao mesmo tempo
LEVERAGE = 10               # Alavancagem configurada na Binance
SCAN_DELAY = 10             # Intervalo entre análises (segundos)

class AlphaTrader:
    def __init__(self):
        # Inicializa a conexão com a Binance Futures
        self.exchange = ccxt.binance({
            'apiKey': BINANCE_KEY,
            'secret': BINANCE_SECRET,
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })
        self.exchange.load_markets()
        self.timers = {} # Registo de tempo para monitorização da IA
        self.strategy = ReversalStrategy(self.exchange)

    def sync_dashboard(self, md, log, t="info"):
        """Envia os dados em tempo real para o Dashboard via Node.js."""
        try:
            payload = {
                "market_data": md,
                "log": {"type": t, "time": time.strftime("%H:%M:%S"), "message": log}
            }
            requests.post(API_URL, json=payload, timeout=2)
        except Exception:
            pass 

    def force_close_position(self, symbol, side, reason):
        """Executa o encerramento da posição verificando o inventário real na Binance."""
        try:
            # Sincroniza mercados e posições
            self.exchange.load_markets()
            pos_data = self.exchange.fetch_positions([symbol])
            pos = next((p for p in pos_data if p['symbol'] == symbol), None)
            
            # Se não houver contratos abertos, limpa o registo local
            if not pos or 'info' not in pos or float(pos['info']['positionAmt']) == 0:
                print(f"ℹ️ {symbol} já está liquidado na Binance.")
                return True

            actual_amt = float(pos['info']['positionAmt'])
            amount = abs(actual_amt)
            
            # LÓGICA DE FECHO: 
            # Se Amt > 0 (LONG) -> SELL | Se Amt < 0 (SHORT) -> BUY
            close_side = 'sell' if actual_amt > 0 else 'buy'
            
            print(f"🏁 LIQUIDAÇÃO REAL: {close_side.upper()} {amount} {symbol}")
            
            # Envia ordem com 'reduceOnly' para segurança máxima
            self.exchange.create_market_order(
                symbol, 
                close_side, 
                amount, 
                params={'reduceOnly': True}
            )
            
            self.sync_dashboard(
                {"pnl": reason, "symbol": "SCANNER"}, 
                f"🏁 POSIÇÃO FECHADA: {symbol} | {reason}", 
                "success"
            )
            return True
        except Exception as e:
            print(f"❌ Erro Crítico ao fechar {symbol}: {e}")
            return False

    def start_trade(self, symbol, side, reason):
        """Inicia uma nova operação validada pela Inteligência Artificial."""
        try:
            self.exchange.load_markets()
            self.exchange.set_leverage(LEVERAGE, symbol)
            
            ticker = self.exchange.fetch_ticker(symbol)
            price = ticker['last']
            market_info = self.exchange.market(symbol)
            
            # Busca saldo real para cálculo dinâmico de lote
            balance_info = self.exchange.fetch_balance()
            total_usd = balance_info['total'].get('USDT', 35.0)

            # Calcula quantidade segura (Mínimo de ~$6.10 para evitar erro de Notional)
            qty = self.strategy.calculate_safe_amount(market_info, price, total_usd)
            
            if qty > 0:
                order_side = 'buy' if side == 'LONG' else 'sell'
                print(f"🚀 ENTRANDO: {side} {symbol} | Valor Est: ${round(qty*price, 2)}")
                
                self.exchange.create_market_order(symbol, order_side, qty)
                self.timers[symbol] = time.time() # Inicia cronómetro para a IA
                
                self.sync_dashboard(
                    {"symbol": symbol, "pnl": "0.00%"}, 
                    f"🎯 ENTRADA IA: {side} em {symbol} ({reason})", 
                    "success"
                )
                return True
        except Exception as e:
            print(f"⚠️ Erro ao abrir trade em {symbol}: {e}")
        return False

def main():
    trader = AlphaTrader()
    print("\n" + "="*50)
    print("🤖 SNIPER IA V3 - MOTOR PRINCIPAL ATIVO")
    print("="*50 + "\n")

    while True:
        try:
            # 1. SINCRONIZAÇÃO DE CONTA E POSIÇÕES
            balance_all = trader.exchange.fetch_balance()
            usdt_balance = balance_all['total'].get('USDT', 0)
            
            # Obtém apenas posições que a Binance confirma estarem abertas
            positions = [p for p in trader.exchange.fetch_positions() if float(p['info']['positionAmt']) != 0]
            num_pos = len(positions)

            # 2. MONITORIZAÇÃO DE SAÍDAS (Cérebro Gemini)
            for p in positions:
                sym = p['symbol']
                amt = float(p['info']['positionAmt'])
                side = 'LONG' if amt > 0 else 'SHORT'
                entry = float(p['entryPrice'])
                
                # Calcula minutos desde a abertura para a IA decidir permanência
                start_time = trader.timers.get(sym, time.time())
                elapsed = (time.time() - start_time) / 60
                
                should_close, reason, pnl = trader.strategy.monitor_exit_with_timeout(sym, side, entry, elapsed)
                
                if should_close:
                    if trader.force_close_position(sym, side, reason):
                        trader.timers.pop(sym, None)
                else:
                    trader.sync_dashboard(
                        {"symbol": sym, "pnl": f"{pnl:.2f}%", "balance": round(usdt_balance, 2)}, 
                        f"Vigiando {sym} ({pnl:.2f}%)", 
                        "info"
                    )

            # 3. SCANNER DE OPORTUNIDADES (Apenas se houver slots livres)
            if num_pos < MAX_SLOTS:
                # Busca moedas com maior volatilidade (Altas e Baixas)
                trending_coins = get_market_movers(trader.exchange, limit=20)
                
                for symbol in trending_coins:
                    if any(pos['symbol'] == symbol for pos in positions):
                        continue
                    
                    # Validação Técnica + Veridito da IA
                    analysis = trader.strategy.check_dual_trend(symbol)
                    
                    if analysis['score'] >= 5:
                        if trader.start_trade(symbol, analysis['trend'], analysis['reason']):
                            break # Abre apenas uma de cada vez para segurança

            # Heartbeat para o Dashboard
            trader.sync_dashboard({"balance": round(usdt_balance, 2)}, "Agente Gemini em patrulha...")
            time.sleep(SCAN_DELAY)

        except Exception as e:
            print(f"❌ Erro Inesperado no Loop: {e}")
            time.sleep(15)

if __name__ == "__main__":
    main()