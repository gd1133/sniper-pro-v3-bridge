import ccxt
import time
import os
import requests
import sys
from dotenv import load_dotenv

# Importação da inteligência e do scanner de alta volatilidade
try:
    from bot_logic import ReversalStrategy
    from scanner import get_market_movers
except ImportError as e:
    print(f"❌ Erro ao importar módulos locais: {e}")
    print("Certifique-se de que bot_logic.py e scanner.py estão na mesma pasta.")
    sys.exit(1)

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
        # Configuração Ultra-Robusta: Ignoramos sub-APIs problemáticas
        self.exchange = ccxt.binance({
            'apiKey': BINANCE_KEY,
            'secret': BINANCE_SECRET,
            'enableRateLimit': True,
            'timeout': 60000, # Aumentado para 60s
            'options': {
                'defaultType': 'future', # Foco em USDT-M
                'adjustForTimeDifference': True,
                'recvWindow': 10000,
                # Forçamos o CCXT a carregar apenas mercados de Futuros USDT (fapi)
                # Isso evita que ele tente conectar ao dapi.binance.com que está a falhar.
                'warnOnFetchOpenOrdersWithoutSymbol': False,
            }
        })
        
        # Override manual de URLs para saltar o dapi (Coin-M) que causa o erro
        self.exchange.urls['api']['delivery'] = 'https://fapi.binance.com/fapi/v1'
        self.exchange.urls['api']['public'] = 'https://fapi.binance.com/fapi/v1'
        self.exchange.urls['api']['private'] = 'https://fapi.binance.com/fapi/v1'
        
        self.load_markets_with_retry()
        
        self.timers = {} # Registo de tempo para monitorização da IA
        self.strategy = ReversalStrategy(self.exchange)

    def load_markets_with_retry(self, retries=5, delay=5):
        """Tenta carregar os mercados da Binance com várias tentativas e troca de hostname."""
        for i in range(retries):
            try:
                print(f"📡 Sincronizando mercados (Foco: USDT-M)... (Tentativa {i+1}/{retries})")
                self.exchange.load_markets()
                print("✅ Conectado à Binance com sucesso!")
                return
            except (ccxt.RequestTimeout, ccxt.NetworkError) as e:
                print(f"⚠️ Erro de rede: {e}")
                
                # Trocando para endpoints alternativos da Binance em caso de falha
                hostnames = ['fapi.binance.com', 'fapi.binance.us', 'binance.com']
                if i < len(hostnames):
                    print(f"🔄 Trocando hostname para: {hostnames[i]}")
                    self.exchange.hostname = hostnames[i]
                
                if i < retries - 1:
                    print(f"⏳ Aguardando {delay}s...")
                    time.sleep(delay)
                else:
                    print("❌ Falha crítica de conexão local.")
                    print("💡 DICA: Se estiver no Brasil, o acesso à API de Futuros em redes domésticas é frequentemente bloqueado.")
                    print("🚀 RECOMENDAÇÃO: Suba este código para o Render ou Railway.")
                    sys.exit(1)

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
        """Encerra a posição verificando o inventário real."""
        try:
            pos_data = self.exchange.fetch_positions([symbol])
            pos = next((p for p in pos_data if p['symbol'] == symbol), None)
            
            if not pos or float(pos['info']['positionAmt']) == 0:
                return True

            actual_amt = float(pos['info']['positionAmt'])
            amount = abs(actual_amt)
            close_side = 'sell' if actual_amt > 0 else 'buy'
            
            self.exchange.create_market_order(symbol, close_side, amount, params={'reduceOnly': True})
            self.sync_dashboard({"pnl": reason, "symbol": "SCANNER"}, f"🏁 FECHADO: {symbol} | {reason}", "success")
            return True
        except Exception as e:
            print(f"❌ Erro ao fechar {symbol}: {e}")
            return False

    def start_trade(self, symbol, side, reason):
        """Inicia uma nova operação validada pela IA."""
        try:
            self.exchange.set_leverage(LEVERAGE, symbol)
            ticker = self.exchange.fetch_ticker(symbol)
            price = ticker['last']
            market_info = self.exchange.market(symbol)
            balance_info = self.exchange.fetch_balance()
            total_usd = balance_info['total'].get('USDT', 35.0)

            qty = self.strategy.calculate_safe_amount(market_info, price, total_usd)
            
            if qty > 0:
                order_side = 'buy' if side == 'LONG' else 'sell'
                self.exchange.create_market_order(symbol, order_side, qty)
                self.timers[symbol] = time.time()
                self.sync_dashboard({"symbol": symbol, "pnl": "0.00%"}, f"🎯 ENTRADA IA: {side} em {symbol}", "success")
                return True
        except Exception as e:
            print(f"⚠️ Erro no trade {symbol}: {e}")
        return False

def main():
    try:
        trader = AlphaTrader()
    except Exception as e:
        print(f"❌ Erro fatal: {e}")
        sys.exit(1)

    print("\n" + "="*50)
    print("🤖 SNIPER IA V3 - MOTOR PRINCIPAL ATIVO")
    print("="*50 + "\n")

    while True:
        try:
            balance_all = trader.exchange.fetch_balance()
            usdt_balance = balance_all['total'].get('USDT', 0)
            positions = [p for p in trader.exchange.fetch_positions() if float(p['info']['positionAmt']) != 0]
            num_pos = len(positions)

            for p in positions:
                sym = p['symbol']
                amt = float(p['info']['positionAmt'])
                side = 'LONG' if amt > 0 else 'SHORT'
                entry = float(p['entryPrice'])
                start_time = trader.timers.get(sym, time.time())
                elapsed = (time.time() - start_time) / 60
                
                should_close, reason, pnl = trader.strategy.monitor_exit_with_timeout(sym, side, entry, elapsed)
                if should_close and trader.force_close_position(sym, side, reason):
                    trader.timers.pop(sym, None)
                else:
                    trader.sync_dashboard({"symbol": sym, "pnl": f"{pnl:.2f}%", "balance": round(usdt_balance, 2)}, f"Vigiando {sym}", "info")

            if num_pos < MAX_SLOTS:
                trending_coins = get_market_movers(trader.exchange, limit=20)
                for symbol in trending_coins:
                    if any(pos['symbol'] == symbol for pos in positions): continue
                    analysis = trader.strategy.check_dual_trend(symbol)
                    if analysis['score'] >= 5:
                        if trader.start_trade(symbol, analysis['trend'], analysis['reason']): break

            trader.sync_dashboard({"balance": round(usdt_balance, 2)}, "Agente Gemini em patrulha...")
            time.sleep(SCAN_DELAY)

        except Exception as e:
            print(f"❌ Erro no Loop: {e}")
            time.sleep(15)

if __name__ == "__main__":
    main()