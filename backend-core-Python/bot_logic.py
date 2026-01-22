import pandas as pd
import numpy as np
import math
import requests
import json
import time
import os

class GeminiAgent:
    """
    O Cérebro de IA: Analisa a 'Vela Mestra' e filtra notícias de manipulação.
    """
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        # ATUALIZADO: Versão estável do modelo para evitar "Erro na IA"
        self.model = "gemini-1.5-flash" 
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

    def ask_gemini(self, prompt, is_news_check=False):
        system_instruction = (
            "Você é o Diretor de Risco do Sniper IA V3. "
            "Sua missão é detectar manipulação institucional e notícias de alto impacto. "
            "Se houver dados do FED, inflação (CPI) ou notícias negativas graves, retorne 'HOLD'. "
            "Caso contrário, avalie a força da tendência. "
            "Responda APENAS JSON: {'verdict': 'BUY/SELL/HOLD', 'confidence': 0-100, 'reason': 'breve'}."
        )

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "generationConfig": {"responseMimeType": "application/json"}
        }

        try:
            for i in [1, 2, 4]:
                response = requests.post(self.url, json=payload, timeout=8)
                if response.status_code == 200:
                    result = response.json()
                    text = result['candidates'][0]['content']['parts'][0]['text']
                    return json.loads(text)
                time.sleep(i)
        except: return None
        return None

class ReversalStrategy:
    def __init__(self, exchange=None):
        self.exchange = exchange
        self.ai = GeminiAgent()
        
        # --- CONFIGURAÇÃO DE ALTO IMPACTO (ATUALIZADA) ---
        self.config = {
            "RISK_PER_TRADE_PCT": 0.35,      # INVESTIMENTO DE 35% DA BANCA
            "MIN_NOTIONAL_USD": 6.10,
            "STOP_LOSS_MAX": 4.0,            # Stop levemente reduzido para maior giro
            "VOLUME_THRESHOLD": 1.4,         # MAIS AGRESSIVO: Baixei de 1.9 para 1.4 (pega mais entradas)
            "MOMENTUM_MIN": 0.20             # MAIS AGRESSIVO: Baixei de 0.35 para 0.20% de força na vela
        }

    def get_mtf_indicators(self, symbol):
        try:
            ohlcv_1d = self.exchange.fetch_ohlcv(symbol, timeframe='1d', limit=50)
            df_1d = pd.DataFrame(ohlcv_1d, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
            ema20_1d = df_1d['c'].ewm(span=20).mean().iloc[-1]
            
            ohlcv_5m = self.exchange.fetch_ohlcv(symbol, timeframe='5m', limit=100)
            df_5m = pd.DataFrame(ohlcv_5m, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
            
            df_5m['ema_fast'] = df_5m['c'].ewm(span=9).mean()
            df_5m['ema_slow'] = df_5m['c'].ewm(span=21).mean()
            
            return df_5m, ema20_1d, df_1d['c'].iloc[-1]
        except: return None, None, None

    def check_dual_trend(self, symbol):
        try:
            df_5m, ema20_1d, price_1d = self.get_mtf_indicators(symbol)
            if df_5m is None: return {'score': 0, 'trend': 'NONE'}

            last_5m = df_5m.iloc[-1]
            avg_vol = df_5m['v'].rolling(20).mean().iloc[-1]
            
            macro_trend = "LONG" if price_1d > ema20_1d else "SHORT"
            
            # Detecção AGRESSIVA de Vela Institucional
            is_huge_volume = last_5m['v'] > (avg_vol * self.config["VOLUME_THRESHOLD"])
            candle_change = ((last_5m['c'] - last_5m['o']) / last_5m['o']) * 100
            
            score = 0
            # Agora ele entra com nota 7 se o volume for bom, mesmo sem ser "perfeito"
            if is_huge_volume and abs(candle_change) >= self.config["MOMENTUM_MIN"]:
                if macro_trend == "LONG" and candle_change > 0: score = 10
                if macro_trend == "SHORT" and candle_change < 0: score = 10

            if score >= 7: 
                prompt = (
                    f"CONTEXTO: Moeda {symbol}. Tendência Diária: {macro_trend}. "
                    f"Vela de 5m com volume {last_5m['v']/avg_vol:.1f}x acima da média. "
                    "Posso entrar?"
                )
                ai_res = self.ai.ask_gemini(prompt)
                
                # Se a IA der erro (None), o robô entra assim mesmo (Modo Ultra Agressivo)
                if ai_res is None:
                    print(f"⚠️ IA OFFLINE: Entrando por análise técnica pura (Score {score})")
                    return {
                        'score': score, 
                        'trend': macro_trend, 
                        'reason': "🔥 ENTRADA TÉCNICA (IA OFFLINE)"
                    }

                if ai_res['verdict'] != 'HOLD' and ai_res['confidence'] > 55:
                    return {
                        'score': score, 
                        'trend': macro_trend, 
                        'reason': f"🔥 {ai_res['reason']} | Confiança: {ai_res['confidence']}%"
                    }
                else:
                    print(f"🛑 IA FILTROU: {ai_res['reason']}")
                    
            return {'score': 0, 'trend': 'NONE'}
        except Exception as e:
            return {'score': 0, 'trend': 'ERROR'}

    def monitor_trend_follow(self, symbol, side, entry, peak):
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe='5m', limit=30)
            df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
            df['ema_fast'] = df['c'].ewm(span=9).mean()
            df['ema_slow'] = df['c'].ewm(span=21).mean()
            
            last = df.iloc[-1]
            pnl = ((last['c'] - entry) / entry) * 100 if side == 'LONG' else ((entry - last['c']) / entry) * 100
            
            should_exit = False
            reason = ""

            if side == 'LONG':
                if last['ema_fast'] < last['ema_slow'] and pnl > 0.1: # PNL mínimo de saída reduzido
                    should_exit = True
                    reason = "MUDANÇA DE DIREÇÃO (EMA CROSSOVER)"
            else:
                if last['ema_fast'] > last['ema_slow'] and pnl > 0.1:
                    should_exit = True
                    reason = "MUDANÇA DE DIREÇÃO (EMA CROSSOVER)"

            if pnl <= -self.config["STOP_LOSS_MAX"]:
                should_exit = True
                reason = "STOP LOSS DE SEGURANÇA"

            return should_exit, reason, pnl, last['c']
        except: return False, "Erro", 0, peak

    def calculate_safe_amount(self, market_info, price, total_balance):
        try:
            # FIXO EM 35% CONFORME SOLICITADO
            val = total_balance * self.config["RISK_PER_TRADE_PCT"]
            lot = next(f for f in market_info['info']['filters'] if f['filterType'] == 'LOT_SIZE')
            step = float(lot['stepSize'])
            prec = int(round(-math.log10(step), 0)) if step < 1 else 0
            return math.floor((val / price) * (10 ** prec)) / (10 ** prec)
        except: return 0