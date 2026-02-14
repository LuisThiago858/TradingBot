import os
import time
import datetime
import pandas as pd
import numpy as np
from binance.client import Client
from binance.enums import *
import logging
import sys

# =============================================================================
# CONFIGURAÇÃO DE LOGGING
# =============================================================================
logger = logging.getLogger('TradingBot')
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    '[%(asctime)s] %(levelname)s - %(name)s - %(funcName)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

file_handler = logging.FileHandler('trading_bot.log', mode='a', encoding='utf-8')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

logger.info("Iniciando configuração do Trading Bot...")

# =============================================================================
# DISCLAIMER:
# Este código é para fins educacionais e não constitui aconselhamento financeiro.
# Utilize-o por sua conta e risco. Teste em ambiente de simulação (testnet)
# antes de operar com valores reais.
# =============================================================================

# =============================================================================
# 1. Definição das Estratégias
# =============================================================================
class Strategy:
    """Classe base para estratégias de trading."""
    def should_buy(self, df: pd.DataFrame) -> bool:
        """Retorna True se a estratégia indicar sinal de COMPRA."""
        raise NotImplementedError

    def should_sell(self, df: pd.DataFrame) -> bool:
        """Retorna True se a estratégia indicar sinal de VENDA."""
        raise NotImplementedError


class MovingAverageCrossStrategy(Strategy):
    """
    Estratégia de cruzamento de médias móveis:
    - Compra quando a SMA de curto prazo cruza a de longo prazo de baixo para cima.
    - Vende quando a SMA de curto prazo cruza a de longo prazo de cima para baixo.
    """
    def __init__(self, short_window: int = 5, long_window: int = 20):
        self.short_window = short_window
        self.long_window = long_window

    def should_buy(self, df: pd.DataFrame) -> bool:
        if len(df) < self.long_window:
            return False
        df = df.copy()  # Evita SettingWithCopyWarning
        df['SMA_short'] = df['close'].rolling(window=self.short_window).mean()
        df['SMA_long'] = df['close'].rolling(window=self.long_window).mean()

        # Cruzamento de SMA curta abaixo -> acima da SMA longa
        return (df['SMA_short'].iloc[-2] < df['SMA_long'].iloc[-2] and
                df['SMA_short'].iloc[-1] > df['SMA_long'].iloc[-1])

    def should_sell(self, df: pd.DataFrame) -> bool:
        if len(df) < self.long_window:
            return False
        df = df.copy()  # Evita SettingWithCopyWarning
        df['SMA_short'] = df['close'].rolling(window=self.short_window).mean()
        df['SMA_long'] = df['close'].rolling(window=self.long_window).mean()

        # Cruzamento de SMA curta acima -> abaixo da SMA longa
        return (df['SMA_short'].iloc[-2] > df['SMA_long'].iloc[-2] and
                df['SMA_short'].iloc[-1] < df['SMA_long'].iloc[-1])


# =============================================================================
# 2. Bot de Trading com Gestão de Risco e Ordens OCO
# =============================================================================
class TradingBot:
    """
    Classe principal do bot de trading. Responsável por:
    - Obter dados de mercado.
    - Executar a estratégia para detectar sinais de compra/venda.
    - Enviar ordens de compra/venda (e OCO, se habilitado).
    """
    def __init__(self, api_key: str, api_secret: str, strategy: Strategy,
                 symbol: str = 'BTCUSDT', interval: str = '1m', quantity: float = 0.001,
                 testnet: bool = True, use_risk_management: bool = True,
                 stop_loss_multiplier: float = 0.98, take_profit_multiplier: float = 1.02):
        """
        :param api_key: Chave de API da Binance.
        :param api_secret: Chave secreta de API da Binance.
        :param strategy: Instância da estratégia de trading.
        :param symbol: Par de negociação (ex: BTCUSDT).
        :param interval: Intervalo dos candles (ex: '1m', '5m').
        :param quantity: Quantidade fixa a ser operada em cada trade.
        :param testnet: Se True, usa a Binance Testnet (dinheiro fictício).
        :param use_risk_management: Se True, após comprar, cria ordem OCO (stop loss e take profit).
        :param stop_loss_multiplier: Multiplicador para stop loss (ex: 0.98 => -2%).
        :param take_profit_multiplier: Multiplicador para take profit (ex: 1.02 => +2%).
        """
        # Conexão com a Binance
        if testnet:
            self.client = Client(api_key, api_secret, testnet=True)
            self.client.API_URL = 'https://testnet.binance.vision/api'
            logger.info("Conectado à Testnet da Binance.")
        else:
            self.client = Client(api_key, api_secret)
            logger.info("Conectado à Binance (produção).")

        self.strategy = strategy
        self.symbol = symbol
        self.interval = interval
        self.quantity = quantity
        self.in_position = False
        self.buy_price = None

        # Gestão de risco
        self.use_risk_management = use_risk_management
        self.stop_loss_multiplier = stop_loss_multiplier
        self.take_profit_multiplier = take_profit_multiplier

    def get_historical_data(self, lookback: int = 100) -> pd.DataFrame:
        """
        Retorna um DataFrame com os dados de candles (OHLCV) do par configurado.
        """
        klines = self.client.get_klines(symbol=self.symbol, interval=self.interval, limit=lookback)
        data = []
        for k in klines:
            data.append({
                'open_time': datetime.datetime.fromtimestamp(k[0] / 1000),
                'open': float(k[1]),
                'high': float(k[2]),
                'low': float(k[3]),
                'close': float(k[4]),
                'volume': float(k[5]),
                'close_time': datetime.datetime.fromtimestamp(k[6] / 1000)
            })
        df = pd.DataFrame(data)
        return df

    def place_risk_management_order(self, current_price: float):
        """
        Coloca uma ordem OCO para gestão de risco: stop loss + take profit.
        """
        take_profit_price = round(current_price * self.take_profit_multiplier, 2)
        stop_loss_price = round(current_price * self.stop_loss_multiplier, 2)
        # Stop limit price (levemente abaixo do stop loss)
        stop_limit_price = round(stop_loss_price * 0.995, 2)

        try:
            oco_order = self.client.order_oco_sell(
                symbol=self.symbol,
                quantity=self.quantity,
                price=str(take_profit_price),
                stopPrice=str(stop_loss_price),
                stopLimitPrice=str(stop_limit_price),
                stopLimitTimeInForce='GTC'
            )
            logger.info(f"Ordem OCO criada: {oco_order}")
        except Exception as e:
            logger.error(f"Erro ao criar ordem OCO: {e}")

    def cancel_open_orders(self):
        """
        Cancela todas as ordens abertas para o símbolo configurado.
        """
        try:
            open_orders = self.client.get_open_orders(symbol=self.symbol)
            for order in open_orders:
                result = self.client.cancel_order(symbol=self.symbol, orderId=order['orderId'])
                logger.info(f"Ordem cancelada: {result}")
        except Exception as e:
            logger.error(f"Erro ao cancelar ordens: {e}")

    def execute_trade(self):
        """
        - Obtém dados de mercado.
        - Verifica sinais de compra/venda via estratégia.
        - Executa ordens de mercado e, se ativado, cria OCO.
        """
        df = self.get_historical_data()
        current_price = df.iloc[-1]['close']

        # Verifica sinal de COMPRA
        if self.strategy.should_buy(df) and not self.in_position:
            try:
                order = self.client.order_market_buy(symbol=self.symbol, quantity=self.quantity)
                logger.info(f"Ordem de COMPRA executada: {order}")
                self.in_position = True
                self.buy_price = current_price

                # Se gestão de risco estiver ativa, coloca a ordem OCO
                if self.use_risk_management:
                    self.place_risk_management_order(current_price)
            except Exception as e:
                logger.error(f"Erro na ordem de compra: {e}")

        # Verifica sinal de VENDA
        elif self.strategy.should_sell(df) and self.in_position:
            try:
                self.cancel_open_orders()  # Cancelar OCO pendentes
                order = self.client.order_market_sell(symbol=self.symbol, quantity=self.quantity)
                logger.info(f"Ordem de VENDA executada: {order}")
                self.in_position = False
                self.buy_price = None
            except Exception as e:
                logger.error(f"Erro na ordem de venda: {e}")
        else:
            logger.info("Nenhum sinal de negociação identificado.")

    def run(self):
        """
        Loop principal que mantém o bot rodando até ser interrompido manualmente.
        """
        logger.info("Iniciando o Trading Bot...")
        while True:
            try:
                self.execute_trade()
            except Exception as e:
                logger.exception(f"Erro inesperado no loop principal: {e}")

            # Intervalo entre cada iteração (60s para intervalos de 1m).
            time.sleep(60)


# =============================================================================
# 3. Backtesting da Estratégia (Exemplo Simples)
# =============================================================================
def backtest_strategy(strategy: Strategy, df: pd.DataFrame, initial_capital: float = 1000.0):
    """
    Simula a estratégia utilizando dados históricos.
    - Assume que toda a posição é comprada/vendida de uma vez (100% do capital).
    - Retorna o capital final e a lista de trades.
    """
    capital = initial_capital
    position = 0.0
    trades = []

    for i in range(len(df)):
        sub_df = df.iloc[:i+1]
        current_price = sub_df.iloc[-1]['close']

        # Compra
        if strategy.should_buy(sub_df) and position == 0:
            position = capital / current_price
            capital = 0.0
            trades.append({
                'type': 'buy',
                'price': current_price,
                'quantity': position,
                'index': i
            })

        # Venda
        elif strategy.should_sell(sub_df) and position > 0:
            capital = position * current_price
            trades.append({
                'type': 'sell',
                'price': current_price,
                'quantity': position,
                'index': i
            })
            position = 0.0

    # Se ainda tiver posição aberta no final
    if position > 0:
        sell_price = df.iloc[-1]['close']
        capital = position * sell_price
        trades.append({
            'type': 'sell',
            'price': sell_price,
            'quantity': position,
            'index': len(df)-1
        })
        position = 0.0

    logger.info(f"Backtest finalizado. Capital final: {capital:.2f} (Inicial: {initial_capital})")
    return capital, trades


# =============================================================================
# 4. Execução Principal
# =============================================================================
if __name__ == '__main__':
    try:
        # Substitua pelas suas credenciais de API
        API_KEY = os.environ.get('binance_api')
        API_SECRET = os.environ.get('binance_secret')

        # Inicializa a estratégia
        strategy = MovingAverageCrossStrategy(short_window=3, long_window=5)

        # Inicializa o Trading Bot
        bot = TradingBot(
            api_key=API_KEY,
            api_secret=API_SECRET,
            strategy=strategy,
            symbol='BTCUSDT',
            interval='1m',
            quantity=0.001,
            testnet=True,             # True = Testnet (dinheiro fictício)
            use_risk_management=True, # Habilita ordens OCO
            stop_loss_multiplier=0.98,
            take_profit_multiplier=1.02
        )

        # EXEMPLO: Executar o bot em tempo real
        logger.info("Iniciando Trading Bot para operação em tempo real...")
        bot.run()

        # EXEMPLO (alternativo): Rodar backtesting
        # df_historical = bot.get_historical_data(lookback=500)
        # final_capital, trades = backtest_strategy(strategy, df_historical, initial_capital=1000.0)
        # logger.info(f"Resultados do Backtest: Capital final = {final_capital:.2f}")
        # logger.info(f"Histórico de operações: {trades}")

    except KeyboardInterrupt:
        logger.info("Interrompido pelo usuário. Encerrando o bot.")
