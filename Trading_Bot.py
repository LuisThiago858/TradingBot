import os
import time
from datetime import datetime
import logging

import pandas as pd
from binance.client import Client
from binance.enums import *

# Importando a função createLogOrder do seu arquivo logger.py
from Logger import createLogOrder
from dotenv import load_dotenv

load_dotenv()

# Variáveis de ambiente (chaves de API)
api_key = os.environ.get('binance_api')
#os.environ.get('binance_api') use uma api de teste fornecido pela binance para evitar perdas reais enquanto testa o bot

secret_key = os.environ.get('binance_secret')
#os.environ.get('binance_secret') use uma secret de teste fornecido pela binance para evitar perdas reais enquanto testa o bot


# Configurações iniciais
STOCK_CODE = 'BTC'                   # Ativo que deseja negociar (ex: BTC)
OPERATION_CODE = 'BTCUSDT'            # Par de negociação (ex: BTCBRL, SOLBRL, etc.)
CANDLE_PERIOD = Client.KLINE_INTERVAL_1MINUTE
TRADED_QUANTITY = 0.00002           # Quantidade básica que será usada nas compras/vendas

# Define o logger
logging.basicConfig(
    filename='trading_bot.log',      # Ajuste aqui o caminho do arquivo de log se desejar
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class BinanceTraderBot:
    """
    Classe principal do seu robô trader na Binance.
    """
    last_trade_decision: bool  # Armazena a última decisão de posição (False = Venda, True = Compra)

    def __init__(self, stock_code, operation_code, traded_quantity, trade_percentage, candle_period):
        # Atributos básicos
        self.stock_code = stock_code                # Ex.: 'BTC'
        self.operation_code = operation_code        # Ex.: 'BTCBRL'
        self.traded_quantity = traded_quantity      # Ex.: 0.000001
        self.trade_percentage = trade_percentage    # Porcentagem do total da carteira a ser negociada (futuro)
        self.candle_period = candle_period          # Periodicidade do candle (ex.: 1m, 5m, etc.)

        # Cliente da binance
        #self.client_binance = Client(api_key, secret_key)
        # Modo de teste (não executa ordens reais)
        self.client_binance = Client(api_key, secret_key, testnet=False)

        # Pega dados iniciais
        self.updateAllData()

        print('-----------------------------------')
        print('Robô trader iniciando as negociações...')

    def updateAllData(self):
        """
        Método para atualizar de forma centralizada os dados importantes:
        - Saldo da conta.
        - Saldo do ativo principal.
        - Posição atual (comprado ou vendido).
        - DataFrame com preços (candles).
        """
        self.acount_data = self.getUpdatedAccountData()          # Dados atualizados da conta
        self.last_stock_account_balance = self.getStockAccountBalance()  # Saldo em estoque
        self.actual_trade_position = self.getActualTradePosition()       # Posição atual (vendido ou comprado)
        self.stock_data = self.getStockData_ClosePrice_OpenTime()        # Dados de preços do ativo

    # --------------------
    # Métodos auxiliares
    # --------------------

    def getUpdatedAccountData(self):
        """
        Retorna dados da conta obtidos diretamente da Binance.
        """
        return self.client_binance.get_account()

    def getStockAccountBalance(self):
        """
        Busca o saldo disponível do ativo principal (self.stock_code) na conta.
        """
        for stock in self.acount_data['balances']:
            if stock['asset'] == self.stock_code:
                in_wallet_account = stock['free']
                return float(in_wallet_account)
        return 0.0

    def getActualTradePosition(self):
        """
        Checa se a posição atual está comprada ou vendida com base no saldo do ativo.
        True = Comprado / False = Vendido.
        """
        if self.last_stock_account_balance > 0.001:
            return True  # Comprado
        else:
            return False # Vendido

    def getStockData_ClosePrice_OpenTime(self):
        
        candles = self.client_binance.get_klines(
            symbol=self.operation_code,
            interval=self.candle_period,
            limit=500
        )

        
        prices = pd.DataFrame(candles)
        prices.columns = [
            'open_time', 'open_price', 'high_price', 'low_price',
            'close_price', 'volume', 'close_time',
            'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume',
            'taker_buy_quote_asset_volume', '_ignore_'
        ]

        
        prices = prices[['open_time', 'close_price']]

        
        prices['open_time'] = pd.to_datetime(prices['open_time'], unit='ms')\
                               .dt.tz_localize('UTC')\
                               .dt.tz_convert('America/Sao_Paulo')

        
        prices['close_price'] = prices['close_price'].astype(float)

        return prices
    
    # -------------------------------------
    # Estratégia de RSI
    # -------------------------------------
    
    def calcular_rsi(self, series: pd.Series, period: int = 14) -> pd.Series:
        """
        Calcula o RSI (Relative Strength Index) para uma série de preços de fechamento.
        Retorna uma Series com o RSI para cada candle.
        """
        # Calcula a variação do preço entre um candle e outro
        delta = series.diff()

        # Separa ganhos (g) e perdas (l)
        ganhos = delta.clip(lower=0)
        perdas = -1 * delta.clip(upper=0)

        # Exponencial moving average (EMA) ou média móvel simples (SMA) das perdas/ganhos
        # Aqui uso EMA (mais comum no RSI atual)
        ganho_medio = ganhos.ewm(com=period - 1, adjust=False).mean()
        perda_media = perdas.ewm(com=period - 1, adjust=False).mean()

        # Evita divisão por zero
        rs = ganho_medio / (perda_media + 1e-10)

        # RSI propriamente dito
        rsi = 100 - (100 / (1 + rs))

        return rsi
    
    def getRSITradeStrategy(self, period=14, rsi_buy_threshold=30, rsi_sell_threshold=70):
        """
        Estratégia baseada em RSI:
          - Se RSI < 30, sinal de compra (sobrevendido).
          - Se RSI > 70, sinal de venda (sobrecomprado).
          - Caso contrário, retorna None (sem operação).
        """
        # Garante que temos a coluna 'rsi' calculada no self.stock_data
        if 'rsi' not in self.stock_data.columns:
            self.stock_data['rsi'] = self.calcular_rsi(self.stock_data['close_price'], period)

        # Pega o último valor do RSI
        last_rsi = self.stock_data['rsi'].iloc[-1]

        print(f"[RSI] Último valor: {last_rsi:.2f}")

        if last_rsi < rsi_buy_threshold:
            print("RSI Strategy => Sinal de COMPRA (RSI abaixo de 30)")
            return True
        elif last_rsi > rsi_sell_threshold:
            print("RSI Strategy => Sinal de VENDA (RSI acima de 70)")
            return False
        else:
            print("RSI Strategy => Nenhum sinal de trade (RSI entre 30 e 70)")
            return None

    # -------------------------------------
    # Estratégia Combinada
    # -------------------------------------

    def getCombinedTradeStrategy(self):
        """
        Exemplo: só compra se AMBAS as estratégias (MA e RSI) sinalizarem compra.
                 só vende se AMBAS as estratégias sinalizarem venda.
        Caso elas divergam ou nenhuma dê sinal, retorna None.
        """
        ma_signal = self.getMovingAverageTradeStrategy()  # True (compra) ou False (venda)
        rsi_signal = self.getRSITradeStrategy()

        # Se RSI deu None, significa "não operar"; podemos tratar de várias formas
        if rsi_signal is None:
            print("RSI sem sinal, não opera.")
            return None

        # Exemplo simples: só opera se ambos concordarem
        if ma_signal == rsi_signal:
            # Se ambos são True => COMPRA
            if ma_signal is True:
                return True
            # Se ambos são False => VENDA
            else:
                return False
        else:
            # Sinais divergentes
            print("Sinais divergentes (MA != RSI), não opera.")
            return None
    

    # -------------------------------------
    # Estratégia de média móvel simples
    # -------------------------------------
    def getMovingAverageTradeStrategy(self, fast_window=5, slow_window=15):
        """
        Exemplo de estratégia simples baseado no cruzamento de Médias Móveis (MA).
        Se a média rápida > média lenta = sinal de compra, senão, sinal de venda.
        Estrategias que eu posso usar
        Para curto prazo: Use 9 EMA e 21 EMA para trades rápidos.
        Para médio prazo: Use 7 EMA e 40 EMA (boa escolha para Swing Trade).
        Para longo prazo: Use 50 EMA e 200 EMA para capturar grandes tendências.
        """
        # Calcula as médias móveis
        self.stock_data['ma_fast'] = self.stock_data['close_price'].rolling(window=fast_window).mean()
        self.stock_data['ma_slow'] = self.stock_data['close_price'].rolling(window=slow_window).mean()
        #usando EMA
        #self.stock_data['ema_fast'] = self.stock_data['close_price'].ewm(span=fast_window, adjust=False).mean()
        #self.stock_data['ema_slow'] = self.stock_data['close_price'].ewm(span=slow_window, adjust=False).mean()

        # Pega o valor das últimas médias
        last_ma_fast = self.stock_data['ma_fast'].iloc[-1]
        last_ma_slow = self.stock_data['ma_slow'].iloc[-1]

        # Decide com base no cruzamento
        if last_ma_fast > last_ma_slow:
            ma_trade_decision = True   # Compra
        else:
            ma_trade_decision = False  # Venda

        print("-----")
        print("Estratégia Executada : Moving Average")
        print(f"({self.operation_code})\n | {last_ma_fast:.3f} = Última Média Rápida\n | {last_ma_slow:.3f} = Última Média Lenta\n")
        print(f"Decisão de posição: {'Compra' if ma_trade_decision else 'Venda'}")
        print("-----")

        return ma_trade_decision
    
    # -------------------------------------
    # Estratégia de Bollinger
    # -------------------------------------

    def getBollingerTradeStrategy(self, window=20, num_std=2.0):
        """
        Exemplo simples:
          - Calcula as bandas de Bollinger (média +/- 2 desvios-padrão).
          - Se preço fechar abaixo da banda inferior => sinal de compra (sobrevendido).
          - Se preço fechar acima da banda superior => sinal de venda (sobrecomprado).
          - Caso contrário => None (sem sinal).
        """
        df = self.stock_data

        if 'bb_middle' not in df.columns:
            # Calcula a média e o desvio padrão
            df['bb_middle'] = df['close_price'].rolling(window=window).mean()
            df['bb_std'] = df['close_price'].rolling(window=window).std()

            # Bandas superior e inferior
            df['bb_upper'] = df['bb_middle'] + (num_std * df['bb_std'])
            df['bb_lower'] = df['bb_middle'] - (num_std * df['bb_std'])

        last_close = df['close_price'].iloc[-1]
        last_lower = df['bb_lower'].iloc[-1]
        last_upper = df['bb_upper'].iloc[-1]

        if last_close < last_lower:
            print("Bollinger => Sinal de COMPRA (fechou abaixo da banda inferior)")
            return True
        elif last_close > last_upper:
            print("Bollinger => Sinal de VENDA (fechou acima da banda superior)")
            return False
        else:
            return None
    

    # ------------------------
    # Métodos de trade (Ordem)
    # ------------------------
    def buyStock(self):
        """
        Realiza a compra do ativo definido em self.operation_code.
        """
        # Define a quantidade mínima permitida (exemplo: 0.0001 BTC)
        min_qty = 0.0001

        # Arredonda a quantidade para atender aos requisitos da Binance
        quantity_to_buy = max(round(self.traded_quantity, 6), min_qty)

        # Verifica saldo disponível em USDT
        usdt_balance = 0.0
        for stock in self.acount_data['balances']:
            if stock['asset'] == 'USDT':
                usdt_balance = float(stock['free'])
                break

        if usdt_balance < (self.traded_quantity * self.stock_data['close_price'].iloc[-1]):
            print("Saldo insuficiente em USDT para comprar!")
            return False

        if not self.actual_trade_position:  # Se a posição atual está vendida

            # Define a quantidade mínima permitida (exemplo: 0.0001 BTC)
            min_qty = 0.0001

            # Arredonda a quantidade para atender aos requisitos da Binance
            quantity_to_buy = max(round(self.traded_quantity, 6), min_qty)

            order_buy = self.client_binance.create_order(
                symbol=self.operation_code,
                side=SIDE_BUY,
                type=ORDER_TYPE_MARKET,
                quantity=quantity_to_buy
            )
            self.actual_trade_position = True
            createLogOrder(order_buy)  # Cria log da ordem
            return order_buy
        else:
            logging.error("Erro ao comprar a stock (já está comprado?)")
            print("Erro ao comprar a stock (já está comprado?)")
            return False

    def sellStock(self):
        """
        Realiza a venda do ativo definido em self.operation_code.
        """
        # Define a quantidade mínima permitida (exemplo: 0.0001 BTC)
        min_qty = 0.0001
        # Arredonda para atender aos requisitos da Binance
        quantity_to_sell = max(round(self.last_stock_account_balance, 6), min_qty)

        if self.actual_trade_position:  # Se a posição atual está comprada
            # Define a quantidade mínima permitida (exemplo: 0.0001 BTC)
            min_qty = 0.0001
            # Arredonda para atender aos requisitos da Binance
            quantity_to_sell = max(round(self.last_stock_account_balance, 6), min_qty)

            order_sell = self.client_binance.create_order(
                symbol=self.operation_code,
                side=SIDE_SELL,
                type=ORDER_TYPE_MARKET,
                quantity=quantity_to_sell
            )
            self.actual_trade_position = False
            createLogOrder(order_sell)  # Cria log da ordem
            return order_sell
        else:
            logging.error("Erro ao vender a stock (já está vendido?)")
            print("Erro ao vender a stock (já está vendido?)")
            return False

    # -------------------------
    # Métodos de impressão
    # -------------------------
    def printWallet(self):
        """
        Printa todas as moedas em que o saldo é maior que 0.
        """
        for stock in self.acount_data['balances']:
            if float(stock['free']) > 0:
                print(stock)

    def printStock(self):
        """
        Printa apenas o saldo do ativo principal definido em self.stock_code.
        """
        for stock in self.acount_data['balances']:
            if stock['asset'] == self.stock_code:
                print(stock)

    def printUSDT(self):
        """
        Printa apenas o saldo em BRL.
        """
        for stock in self.acount_data['balances']:
            if stock['asset'] == 'BRL':
                print(stock)

    # -------------------------
    # Loop principal de execução
    # -------------------------
    def execute(self):
        """
        Faz uma execução única de todas as etapas:
        - Atualiza dados.
        - Printa posição atual.
        - Executa estratégia de média móvel.
        - Decide se vai comprar ou vender.
        """
        # Atualiza os dados
        self.updateAllData()

        print('-----------------------------------')
        print(f'Executando ({datetime.now().strftime("%Y-%m-%d %H:%M:%S")})')
        print(f'Posição Atual: {"Comprado" if self.actual_trade_position else "Vendido"}')
        print(f'Balanço Atual: {self.last_stock_account_balance} ({self.stock_code})')
        print('-----------------------------------')

        # 1 - Obtém decisão de trade via estratégia de médias
        ma_trade_decision = self.getMovingAverageTradeStrategy()
        # 2 - Obtém decisão de trade via estratégia de RSI
        #ma_trade_decision = self.getRSITradeStrategy()
        # 3 - Obtém a estrategia combinada RSI + MA
        #ma_trade_decision = self.getCombinedTradeStrategy()
        # 4 - Obtém a estrategia Bolling
        #ma_trade_decision = self.getBollingerTradeStrategy()

        self.last_trade_decision = ma_trade_decision

        # Caso a posição seja vendida (False) e a decisão seja compra (True), compra
        if not self.actual_trade_position and self.last_trade_decision:
            self.printStock()
            self.printUSDT()
            self.buyStock()
            time.sleep(2)
            self.updateAllData()
            self.printStock()
            self.printUSDT()

        # Caso a posição seja comprada (True) e a decisão seja venda (False), vende
        elif self.actual_trade_position and not self.last_trade_decision:
            self.printStock()
            self.printUSDT()
            self.sellStock()
            time.sleep(2)
            self.updateAllData()
            self.printStock()
            self.printUSDT()


if __name__ == "__main__":
    """
    Rotina principal de execução do bot.
    Aqui você instância a classe e define o loop de quanto em quanto tempo
    quer rodar a estratégia (no exemplo, a cada 60 segundos).
    """
    MaTrader = BinanceTraderBot(STOCK_CODE, OPERATION_CODE, TRADED_QUANTITY, 100, CANDLE_PERIOD)
    
    # Loop infinito, execute a estratégia a cada 60 segundos (1 minuto).
    while True:
        MaTrader.execute()
        time.sleep(60)
