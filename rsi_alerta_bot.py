import ccxt
import pandas as pd
import ta
import asyncio
import datetime
import logging
from telegram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Configurações principais
TELEGRAM_TOKEN = '7194137223:AAHKByhVzacxlYRJgi9Yz8sRlg45gleUvP4'
TELEGRAM_USER_ID = 701816743
EXCHANGE = ccxt.binance()

# Configurar o bot do Telegram
bot = Bot(token=TELEGRAM_TOKEN)

# Variáveis globais
tokens_monitorados = []

# Função para buscar os 100 tokens de maior volume
async def buscar_top_tokens():
    global tokens_monitorados
    print("Atualizando lista de tokens...")
    
    tickers = EXCHANGE.fetch_tickers()
    df = pd.DataFrame([
        {
            'symbol': k,
            'baseVolume': v['baseVolume'],
            'last': v['last'],
            'high': v['high'],
            'low': v['low']
        }
        for k, v in tickers.items()
        if '/USDT' in k and v['baseVolume'] is not None
    ])

    # Pegar os 100 com maior volume
    df = df.sort_values('baseVolume', ascending=False).head(100)

    # Calcular volatilidade (alta - baixa) / última
    df['volatilidade'] = (df['high'] - df['low']) / df['last']

    # Pegar os 10 mais voláteis
    tokens_monitorados = df.sort_values('volatilidade', ascending=False).head(10)['symbol'].tolist()
    print(f"Tokens monitorados: {tokens_monitorados}")

# Função para calcular RSI
def calcular_rsi(candles):
    close_prices = [candle[4] for candle in candles]
    df = pd.DataFrame({'close': close_prices})
    rsi = ta.momentum.RSIIndicator(df['close'], window=14)
    return rsi.rsi().iloc[-1]

# Função principal para monitorar RSI
async def monitorar_rsi():
    while True:
        for symbol in tokens_monitorados:
            try:
                ohlcv = EXCHANGE.fetch_ohlcv(symbol, timeframe='1h', limit=100)
                if ohlcv:
                    rsi = calcular_rsi(ohlcv)
                    print(f"RSI de {symbol}: {rsi:.2f}")

                    if rsi < 30:
                        await bot.send_message(chat_id=TELEGRAM_USER_ID, text=f"⚡ ALERTA RSI ⚡\n{symbol} está com RSI abaixo de 30!\nRSI atual: {rsi:.2f}")
            except Exception as e:
                print(f"Erro ao verificar {symbol}: {e}")

        await asyncio.sleep(3600)  # Espera 1 hora para checar de novo

# Inicialização
async def main():
    await buscar_top_tokens()  # Primeira vez
    scheduler = AsyncIOScheduler()
    scheduler.add_job(buscar_top_tokens, 'cron', hour=0, minute=0)  # Atualizar todo dia às 00h
    scheduler.start()
    await monitorar_rsi()

# Logs básicos
logging.basicConfig(level=logging.INFO)

# Rodar
asyncio.run(main())
