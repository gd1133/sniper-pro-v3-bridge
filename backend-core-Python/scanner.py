import ccxt
import pandas as pd

def get_market_movers(exchange, limit=15):
    """
    Identifica as moedas que mais estão se movendo (Gains e Losses).
    Foca em volatilidade real para o Agente Gemini aproveitar a tendência.
    """
    try:
        # Busca todos os tickers (resumo de 24h)
        tickers = exchange.fetch_tickers()
        data = []
        
        for symbol, ticker in tickers.items():
            # Filtro: Apenas pares USDT e que tenham variação percentual
            if '/USDT' in symbol and ticker.get('percentage') is not None:
                # Filtrar moedas com volume mínimo de $5M para evitar "pumps" falsos
                if ticker.get('quoteVolume', 0) > 5_000_000:
                    data.append({
                        'symbol': symbol,
                        'percentage': float(ticker['percentage']),
                        'volume': float(ticker['quoteVolume'])
                    })
        
        if not data:
            return ['BTC/USDT:USDT', 'ETH/USDT:USDT']

        df = pd.DataFrame(data)
        
        # 1. Seleciona as Maiores Altas (Top Gainers)
        gainers = df.sort_values(by='percentage', ascending=False).head(limit)
        
        # 2. Seleciona as Maiores Baixas (Top Losers)
        losers = df.sort_values(by='percentage', ascending=True).head(limit)
        
        # Une as duas listas para o robô analisar
        trending_list = pd.concat([gainers, losers])['symbol'].unique().tolist()
        
        print(f"🔥 Scanner: {len(trending_list)} alvos de alta volatilidade detectados.")
        return trending_list

    except Exception as e:
        print(f"⚠️ Erro no Scanner de Tendências: {e}")
        return ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT']