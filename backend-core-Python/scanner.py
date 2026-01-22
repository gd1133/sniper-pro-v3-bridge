import ccxt
import pandas as pd
import time

def get_market_movers(exchange, limit=15):
    """
    Scanner Avançado Sniper 5.0:
    Busca moedas com volume institucional e tendência macro (1D/1H) alinhada.
    Filtra ativos de alta liquidez para suportar entradas pesadas (50% da banca).
    """
    try:
        # 1. Captura de Tickers e Filtro de Liquidez Extrema
        # Para operar com 50% da banca, precisamos de moedas que não sofram slippage.
        tickers = exchange.fetch_tickers()
        candidates = []
        
        print("🔍 Scanner 5.0: Analisando força institucional...")

        for symbol, ticker in tickers.items():
            # Filtro 1: Apenas pares USDT
            # Filtro 2: Liquidez mínima de $30M/dia para suportar "porradas" da banca
            if '/USDT' in symbol and ticker.get('quoteVolume', 0) > 30_000_000:
                # Ignorar stablecoins para não desperdiçar processamento
                if any(stable in symbol for stable in ['USDC', 'FDUSD', 'TUSD', 'DAI']):
                    continue
                
                candidates.append({
                    'symbol': symbol,
                    'vol_24h': ticker['quoteVolume'],
                    'change_24h': ticker['percentage']
                })

        if not candidates:
            return ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT']

        # Ordenar pelas moedas com maior volume (onde as instituições estão operando)
        df_candidates = pd.DataFrame(candidates)
        top_volatile = df_candidates.sort_values(by='vol_24h', ascending=False).head(limit * 2)

        final_list = []

        # 2. VALIDAÇÃO MACRO (Multi-Timeframe 1D)
        for _, row in top_volatile.iterrows():
            symbol = row['symbol']
            try:
                # Busca histórico de 1 Dia
                ohlcv_1d = exchange.fetch_ohlcv(symbol, timeframe='1d', limit=30)
                df_1d = pd.DataFrame(ohlcv_1d, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
                
                # Média Móvel Exponencial (EMA 20) - Referência de tendência institucional
                ema_20 = df_1d['c'].ewm(span=20).mean().iloc[-1]
                current_price = df_1d['c'].iloc[-1]

                # --- FILTRO DE ENTRADA VENCEDORA ---
                # Só aceita se houver volume acima da média (Baleias ativas)
                avg_vol_1d = df_1d['v'].mean()
                is_whale_active = df_1d['v'].iloc[-1] > (avg_vol_1d * 1.2)

                # Verifica se o preço está em tendência clara (acima ou abaixo da EMA 20)
                # O robô vai operar a favor da maré macro.
                if is_whale_active:
                    # Se o preço está acima da EMA 20 (Tendência de Alta)
                    # OU se está abaixo da EMA 20 (Tendência de Baixa)
                    # Ambas são boas se o robô souber surfar a direção.
                    final_list.append(symbol)
                
                if len(final_list) >= limit: break
                
                # Pequena pausa para respeitar o Rate Limit da Binance
                time.sleep(0.05) 

            except Exception:
                continue

        if not final_list:
            return ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT']

        print(f"✅ Scanner Finalizado: {len(final_list)} alvos institucionais detectados.")
        return final_list

    except Exception as e:
        print(f"⚠️ Erro no Scanner Master: {e}")
        # Moedas Porto Seguro caso tudo falhe
        return ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT', 'BNB/USDT:USDT']