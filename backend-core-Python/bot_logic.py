import pandas as pd
import numpy as np
import math
import requests
import json
import time
import os

class GeminiAgent:
    """O Cérebro de IA que valida múltiplas confluências de momentum e reversão."""
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.model = "gemini-2.5-flash-preview-09-2025"
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

    def ask_gemini(self, prompt):
        """Consulta o Gemini com proteção contra erros de conexão e retentativas."""
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "systemInstruction": {
                "parts": [{"text": (
                    "És um Analista Quantitativo de Elite. Analisa RSI, Bollinger, Momentum, Volume e Price Action. "
                    "Sê proativo e agressivo. Não esperes apenas por baleias. Se houver força de movimento, valida a entrada. "
                    "Responde apenas JSON: {'verdict': 'BUY/SELL/HOLD/WAIT', 'confidence': 0-100, 'reason': 'breve'}."
                )}]
            },
            "generationConfig": {"responseMimeType": "application/json"}
        }

        for i in range(5):
            try:
                response = requests.post(self.url, json=payload, timeout=12)
                if response.status_code == 200:
                    result = response.json()
                    text = result['candidates'][0]['content']['parts'][0]['text']
                    return json.loads(text)
            except:
                time.sleep(2 ** i)
        return None

class ReversalStrategy:
    def __init__(self, exchange=None):
        self.exchange = exchange
        self.ai = GeminiAgent()
        self.config = {
            "RISK_PER_TRADE_PCT": 0.18,    # 18% de $35 ~ $6.30
            "MIN_NOTIONAL_USD": 6.50,      # Segurança contra Erro -4164 ($5 min)
            "TAKE_PROFIT_PCT": 1.1,        # Alvo de Scalping rápido
            "STOP_LOSS_PCT": 3.0,          # Proteção técnica contra volatilidade
            "MIN_SCORE": 3                 # Gatilho técnico agressivo
        }

    def get_indicators(self, df):
        """Calcula múltiplos indicadores para análise simultânea."""
        # 1. RSI (Momentum)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss.replace(0, 0.001)
        df['rsi'] = 100 - (100 / (1 + rs))

        # 2. Bandas de Bollinger (Volatilidade)
        df['sma'] = df['close'].rolling(window=20).mean()
        df['std'] = df['close'].rolling(window=20).std()
        df['upper'] = df['sma'] + (df['std'] * 2)
        df['lower'] = df['sma'] - (df['std'] * 2)

        # 3. EMA 200 (Tendência Macro)
        df['ema200'] = df['close'].ewm(span=200).mean()
        return df

    def detect_price_action(self, df):
        """Identifica padrões de velas em tempo real."""
        last = df.iloc[-1]
        prev = df.iloc[-2]
        body = abs(last['close'] - last['open'])
        lower_wick = min(last['close'], last['open']) - last['low']
        upper_wick = last['high'] - max(last['close'], last['open'])

        patterns = {"bullish": 0, "bearish": 0}
        
        # Hammer / Rejeição de Fundo
        if lower_wick > (body * 2) and body > 0: patterns["bullish"] += 2
        # Engolfo de Alta
        if last['close'] > prev['open'] and last['open'] < prev['close'] and last['close'] > last['open']: patterns["bullish"] += 2
        # Shooting Star / Rejeição de Topo
        if upper_wick > (body * 2) and body > 0: patterns["bearish"] += 2
        
        return patterns

    def check_dual_trend(self, symbol):
        """MOTOR MULTI-ESTRATÉGIA: RSI + Bollinger + Price Action + IA."""
        df = self.get_data(symbol, '1m', 100)
        if df is None or len(df) < 50: return {'score': 0, 'trend': 'NONE', 'reason': 'Dados insuficientes'}

        df = self.get_indicators(df)
        patterns = self.detect_price_action(df)
        last = df.iloc[-1]
        
        # Correção do RuntimeWarning de volume
        vol_mean = df['volume'].mean()
        vol_factor = last['volume'] / vol_mean if vol_mean > 0 else 1
        
        score_long = 0
        score_short = 0

        # ESTRATÉGIA 1: EMA 200
        if last['close'] > last['ema200']: score_long += 1
        else: score_short += 1

        # ESTRATÉGIA 2: RSI Agressivo
        if last['rsi'] < 40: score_long += 1
        if last['rsi'] > 60: score_short += 1

        # ESTRATÉGIA 3: Bollinger Reversion
        if last['close'] <= last['lower']: score_long += 2
        if last['close'] >= last['upper']: score_short += 2

        # ESTRATÉGIA 4: Price Action
        score_long += patterns["bullish"]
        score_short += patterns["bearish"]

        # ESTRATÉGIA 5: Volume de Agressão
        if vol_factor > 1.3:
            score_long += 1
            score_short += 1

        final_score = max(score_long, score_short)
        trend = "LONG" if score_long > score_short else "SHORT"

        # VALIDAÇÃO AGRESSIVA DA IA (Gatilho para score >= 3)
        if final_score >= 3:
            prompt = (f"Moeda {symbol} a {last['close']}. RSI: {last['rsi']:.1f}, "
                      f"Price Action Score: {max(patterns.values())}, Volume: {vol_factor:.1f}x. "
                      f"Sinal de {trend} detectado. Validas entrada rápida?")
            
            ai_res = self.ai.ask_gemini(prompt)
            if ai_res:
                print(f"🧠 Gemini [{symbol}]: {ai_res['verdict']} | Confiança: {ai_res['confidence']}% | {ai_res['reason']}")
                # Confiança reduzida para 65% para maior rotatividade
                if ai_res['verdict'] in ['BUY', 'SELL'] and ai_res['confidence'] >= 65:
                    return {'score': 5, 'trend': trend, 'reason': ai_res['reason']}

        # Confluência Técnica Pura (Score alto)
        if final_score >= 5:
            return {'score': 5, 'trend': trend, 'reason': 'Confluência Técnica Máxima'}

        return {'score': 0, 'trend': 'NONE', 'reason': 'Análise incompleta'}

    def monitor_exit_with_timeout(self, symbol, side, entry_price, elapsed_minutes):
        """Gere a saída com foco em lucro rápido e proteção de capital."""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            cur = ticker['last']
            pnl = ((cur - entry_price) / entry_price) * 100 if side == 'LONG' else ((entry_price - cur) / entry_price) * 100
            
            # Saídas Fixas
            if pnl >= self.config['TAKE_PROFIT_PCT']: return True, f"🎯 LUCRO: {pnl:.2f}%", pnl
            if pnl <= -self.config['STOP_LOSS_PCT']: return True, f"🛑 STOP: {pnl:.2f}%", pnl

            # IA decide se a tendência acabou a cada 2 minutos
            if elapsed_minutes >= 2 and int(elapsed_minutes) % 2 == 0:
                ai_decision = self.ai.ask_gemini(f"Trade {side} {symbol} com {pnl:.2f}% PNL. A força continua?")
                if ai_decision and ai_decision['verdict'] in ['SELL', 'WAIT'] and pnl > 0.1:
                    return True, f"IA: Saída Antecipada ({ai_decision['reason']})", pnl

            return False, "Vigiando", pnl
        except: return False, "Erro", 0

    def get_data(self, symbol, timeframe, limit):
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            return pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        except: return None

    def calculate_safe_amount(self, symbol_info, price, total_balance):
        """Calcula quantidade garantindo que o valor nominal seja > $6.00."""
        try:
            # 1. Calcula com base nos 18% da banca
            calculated_value = total_balance * self.config["RISK_PER_TRADE_PCT"]
            # 2. Força o mínimo de $6.50 para evitar erro -4164
            order_value = max(calculated_value, self.config["MIN_NOTIONAL_USD"])
            
            lot_filter = next(f for f in symbol_info['info']['filters'] if f['filterType'] == 'LOT_SIZE')
            step_size = float(lot_filter['stepSize'])
            precision = int(round(-math.log10(step_size), 0)) if step_size < 1 else 0
            
            qty = math.floor((order_value / price) * (10 ** precision)) / (10 ** precision)
            
            # Garantia final de arredondamento
            if (qty * price) < 5.10:
                qty = math.ceil((5.20 / price) * (10 ** precision)) / (10 ** precision)
                
            return qty
        except: return 0