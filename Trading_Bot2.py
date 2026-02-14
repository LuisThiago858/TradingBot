import os
import time
from datetime import datetime
import logging

import pandas as pd
from binance.client import Client
from binance.enums import *

from Logger import createLogOrder

# Variáveis de ambiente (chaves de API)
api_key = os.environ.get('binance_api')
secret_key = os.environ.get('binance_secret')
# Configurações iniciais
STOCK_CODE = 'BTC'
OPERATION_CODE = 'SOLBRL'
CANDLE_PERIOD = Client.KLINE_INTERVAL_1MINUTE
TRADED_QUANTITY = 0.0001  # Ajustado para evitar compras pequenas demais

# Configuração do logger
logging.basicConfig(
    filename='trading_bot.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class BinanceTraderBot:
    last_trade_decision: str  # "BUY", "SELL" ou "HOLD"

    def __init__(self, stock_code, operation_code, traded_quantity, candle_period):
        self.stock_code = stock_code
        self.operation_code = operation_code
        self.traded_quantity = traded_quantity
        self.candle_period = candle_period
        self.client_binance = Client(api_key, secret_key, testnet=True)

        self.last_buy_price = None  # Armazena o preço da última compra
        self.last_trade_time = None  # Armazena o tempo da última operação

        self.updateAllData()

        print('-----------------------------------')
        print('Robô trader iniciando as negociações...')

    def updateAllData(self):
        self.acount_data = self.getUpdatedAccountData()
        self.last_stock_account_balance = self.getStockAccountBalance()
        self.actual_trade_position = self.getActualTradePosition()
        self.stock_data = self.getStockData_ClosePrice_OpenTime()

    def getUpdatedAccountData(self):
        return self.client_binance.get_account()

    def getStockAccountBalance(self):
        for stock in self.acount_data['balances']:
            if stock['asset'] == self.stock_code:
                return float(stock['free'])
        return 0.0

    def getActualTradePosition(self):
        return self.last_stock_account_balance > 0.001

    def getStockData_ClosePrice_OpenTime(self):
        candles = self.client_binance.get_klines(
            symbol=self.operation_code,
            interval=self.candle_period,
            limit=500
        )

        prices = pd.DataFrame(candles)
        prices.columns = ['open_time', 'open_price', 'high_price', 'low_price',
                          'close_price', 'volume', 'close_time',
                          'quote_asset_volume', 'number_of_trades',
                          'taker_buy_base_asset_volume',
                          'taker_buy_quote_asset_volume', '-']

        prices = prices[['open_time', 'close_price']]
        prices['open_time'] = pd.to_datetime(prices['open_time'], unit='ms')\
                               .dt.tz_localize('UTC')\
                               .dt.tz_convert('America/Sao_Paulo')

        prices['close_price'] = prices['close_price'].astype(float)
        return prices

    def getMovingAverageTradeStrategy(self, fast_window=7, slow_window=40):
        self.stock_data['ma_fast'] = self.stock_data['close_price'].rolling(window=fast_window).mean()
        self.stock_data['ma_slow'] = self.stock_data['close_price'].rolling(window=slow_window).mean()

        last_ma_fast = self.stock_data['ma_fast'].iloc[-1]
        last_ma_slow = self.stock_data['ma_slow'].iloc[-1]
        previous_ma_fast = self.stock_data['ma_fast'].iloc[-2]
        previous_ma_slow = self.stock_data['ma_slow'].iloc[-2]

        if previous_ma_fast < previous_ma_slow and last_ma_fast > last_ma_slow:
            return "BUY"
        elif previous_ma_fast > previous_ma_slow and last_ma_fast < last_ma_slow:
            return "SELL"
        else:
            return "HOLD"

    def shouldSell(self, current_price):
        stop_loss_threshold = 0.95
        take_profit_threshold = 1.10

        if self.last_buy_price is None:
            return False

        if current_price <= self.last_buy_price * stop_loss_threshold:
            print("⚠️ Stop-Loss ativado!")
            return True
        elif current_price >= self.last_buy_price * take_profit_threshold:
            print("🎯 Take-Profit atingido!")
            return True
        return False

    def shouldBuy(self, current_price):
        min_balance_btc = 0.001
        min_time_between_trades = 60 * 5

        if self.last_trade_time and (time.time() - self.last_trade_time) < min_time_between_trades:
            return False

        if self.last_stock_account_balance < min_balance_btc:
            print("❌ Saldo insuficiente para compra!")
            return False

        return True

    def buyStock(self):
        min_qty = 0.0001
        quantity_to_buy = max(round(self.traded_quantity, 6), min_qty)

        order_buy = self.client_binance.create_order(
            symbol=self.operation_code,
            side=SIDE_BUY,
            type=ORDER_TYPE_MARKET,
            quantity=quantity_to_buy
        )
        self.actual_trade_position = True
        self.last_buy_price = self.stock_data['close_price'].iloc[-1]
        self.last_trade_time = time.time()
        createLogOrder(order_buy)
        return order_buy

    def sellStock(self):
        min_qty = 0.0001
        quantity_to_sell = max(round(self.last_stock_account_balance, 6), min_qty)

        order_sell = self.client_binance.create_order(
            symbol=self.operation_code,
            side=SIDE_SELL,
            type=ORDER_TYPE_MARKET,
            quantity=quantity_to_sell
        )
        self.actual_trade_position = False
        self.last_trade_time = time.time()
        createLogOrder(order_sell)
        return order_sell

    def execute(self):
        self.updateAllData()
        print(f'🚀 Executando ({datetime.now().strftime("%Y-%m-%d %H:%M:%S")})')

        trade_decision = self.getMovingAverageTradeStrategy()
        current_price = self.stock_data['close_price'].iloc[-1]

        if trade_decision == "BUY" and self.shouldBuy(current_price):
            print("✅ Decisão: Comprar!")
            self.buyStock()
        elif trade_decision == "SELL" or self.shouldSell(current_price):
            print("✅ Decisão: Vender!")
            self.sellStock()
        else:
            print("🔍 Nenhuma ação tomada, aguardando melhor oportunidade.")

if __name__ == "__main__":
    MaTrader = BinanceTraderBot(STOCK_CODE, OPERATION_CODE, TRADED_QUANTITY, CANDLE_PERIOD)
    
    while True:
        MaTrader.execute()
        time.sleep(60)
