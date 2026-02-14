import os
import time
from datetime import datetime
import logging

import pandas as pd
from binance.client import Client
from binance.enums import *

from Logger import *
api_key = os.environ.get('binance_api')
secret_key = os.environ.get('binance_secret')

#configuraçoes

STOCK_CODE = 'BTC'
OPERATION_CODE = 'SOLBRL'
CANDLE_PERIOD = Client.KLINE_INTERVAL_1MINUTE
TRADED_QUANTITY = 0.000001

#define o logger

logging.basicConfig(
    filename='/trading_bot.log',
    level=logging.INFO,
    format= '%(asctime)s  -  %(levelname)s  -  %(message)s'
)

#Classe Principal

class BinanceTraderBot():
    last_trade_decision : bool #Ultima decisão de posicao (False = Venda, True = Compra)
    def __init__(self, stock_code, operation_code, traded_quantity, trade_percentage, candle_period):
        self.stock_code = stock_code #Codigo principal da stock negociada (ex: BTC)
        self.operation_code = operation_code #Codigo negociado/moeda (ex: BTCBRL)
        self.traded_quantity = traded_quantity #Quantidade inicial que será operada
        self.trade_percentage = trade_percentage #Porcentagem do total da carteira, que será negociada
        self.candle_period = candle_period #Periodo levado em consideração para operação (ex: 1m, 5m, 15m, 1h, 1d)

        self.client_binance = Client(api_key, secret_key)

        self.updateAllData()#Busca e atualiza os dados

        print('-----------------------------------')
        print('Robô trader iniciando as negociações....')

    def updateAllData(self):
        self.acount_data = self.getUpdatedAccountData() #dados atualizados da conta
        self.last_stock_account_balance = self.getStockAccountBalance() #Saldo da conta em estoque
        self.actual_trade_position = self.getActualTradePosition() #Posição atual da trade(false = vendido, true = comprado)
        self.stock_data = self.getStockData_ClosePrice_OpenTime() #atualiza os dados da stock


        #Busca infos atualizada da conta binance
        def getUpdatedAccountData(self):
            return self.client_binance.get_account()
        #Busca o ultimo balanço da conta, na stock escolhida
        def getLastStockAccountBalance(self):

            for stock in self.acount_data['balances']:
                if stock['asset'] == self.stock_code:
                    in_wallet_acount = stock['free']
            
            return float(in_wallet_acount)
        
        #Checa se a posição atual é comprada ou vendida
        #Faturamento integra no banco de dados
        #Guarda este dado com mais precisão

        def getActualTradePosition(self):
            if self.last_stock_account_balance > 0.001:
                return True #Comprado
            else:
                return False #Está vendido
            
        #Busca oos dados ativo da stock no periodo
        def getStockData_ClosePrice_OpenTime(self):
            
            #busca dados na binance dos ultimos 1000 periodos
            candles = self.client_binance.get_klines(symbol=self.operation_code, interval=self.candle_period, limit=500)

            #transforma os dados em um dataframe pandas
            prices = pd.DataFrame(candles)

            #renomeia as colunas baseada na documentação da binance
            prices.columns = ['open_time', 'open_price', 'high_price', 'low_price',
                               'close_price', 'volume', 'close_time', 
                               'quote_asset_volume', 'number_of_trades',
                                 'taker_buy_base_asset_volume',
                                   'taker_buy_quote_asset_volume', '-']
            
            #pega apenas os indicadores que queremos para esse modelo
            prices = prices[['clodes_price', 'open_time']]
            #corrige o tempo de fechamento
            prices['open_time'] = pd.to_datetime(prices['open_time'], unit='ms').dt.tz_localize('UTC')
            #Converte para o fuso horarios UTC -3
            prices['open_time'] = prices['open_time'].dt.tz_convert('America/Sao_Paulo')

            return prices
        
        def getMovingAverageTradeStrategy(self, fast_window = 7, slow_window = 40):
            #Calcula as medias moveis
            self.stock_data['ma_fast'] = self.stock_data['close_price'].rolling(window=fast_window).mean()    #Media Rápida
            self.stock_data['ma_slow'] = self.stock_data['close_price'].rolling(window=slow_window).mean()   #Media Lenta

            #Pega as ultimas medias moveis

            last_ma_fast = self.stock_data['ma_fast'].iloc[-1] #Ultima media rapida do array
            last_ma_slow = self.stock_data['ma_slow'].iloc[-1] #Ultima media lenta do array

            #Toma a decisão de compra ou venda baseada na posiçao da média movel
            #(False = Venda, True = Compra)
            if last_ma_fast > last_ma_slow:
                ma_trade_decision = True
            else:
                ma_trade_decision = False

            print('-----')
            print('Estrategia Executada : Moving Average')
            print(f'({self.operation_code})\n | {last_ma_fast: .3f} = Ultima Media Rapida\n | {last_ma_slow: .3f} = Ultima Media Lenta\n')
            print(f'Decisão de posicao: {"Compra" if ma_trade_decision == True else "Venda"}')
            print('-----')

            return ma_trade_decision
        
        #Prints

        #printa toda a carteira

        def printWallet(self):
            for stock in self.acount_data['balances']:
                if float(stock['free']) > 0:
                    print(stock)

        def buyStock(self):
            if self.actual_trade_position == False: #se a posição atual for vendida
                order = self.client_binance.create_order(
                    symbol=self.operation_code,
                    side=SIDE_BUY,
                    type=ORDER_TYPE_MARKET,
                    quantity=self.traded_quantity
                )

                self.actual_trade_position = True #define a posição atual como comprada	
                createLogOrder(order_buy) #cria um log da ordem
                return order_buy #Retorna a ordem
            else:
                #se ocorreu um erro
                logging.error('Erro ao comprar a stock')
                print('Erro ao comprar a stock')
                return False
            
        def sellStock(self):
            if self.actual_trade_position == True: #se a posição atual for comprada
                order = self.client_binance.create_order(
                    symbol=self.operation_code,
                    side=SIDE_SELL,
                    type=ORDER_TYPE_MARKET,
                    quantity=int(self.last_stock_account_balance * 1000) / 1000 #arredonda para 3 casas decimais
                )

                self.actual_trade_position = False #define a posição atual como vendida
                createLogOrder(order_sell) #cria um log da ordem
                return order_sell #Retorna a ordem
            else:
                #se ocorreu um erro
                logging.error('Erro ao vender a stock')
                print('Erro ao vender a stock')
                return False
            
        def execute(self):
            while True:
                #Atualiza os dados
                self.updateAllData()

                print('-----------------------------------')
                print(f'Executando ({datetime.now().strftime("%Y-%m-%d %H:%M:%S")})') #adiciona a data e hora atual
                print(f'Posicao Atual: {"Comprado" if MaTrader.actual_trade_position == True else "Vendido"}')# printa a posição atual
                print(f'Balanço Atual: {MaTrader.last_stock_account_balance} ({self.stock_code})') #printa o balanço atual
                print('-----------------------------------')

                #Executa a estrategia de media movel
                ma_trade_decision = self.getMovingAverageTradeStrategy()

                #Melhorias futuras
                #criar outras estrategias e ir adicionando elas aqui
                #E criar uma funcao que vai olhar para todas essas estrategias e tomar a decisao final
                #E passar isso como uma last_trade_decision
                #Desenvolver mais estrategias de analise tecnica

                #Neste caso, a decisao final sera a mesma da media movel
                self.last_trade_decision = ma_trade_decision

                #Se a posicao atual for vendida (False) e a decisao for de compra (True), compra o ativo
                #Se a posicao atual for comprada (True) e a decisao for de venda (False), vende o ativo
                if self.actual_trade_position == False and self.last_trade_decision == True:
                    self.printStock()
                    self.printBRL()
                    self.buyStock()
                    time.sleep(2)
                    self.updateAllData()
                    self.printStock()
                    self.printBRL()
                elif self.actual_trade_position == True and self.last_trade_decision == False:
                    self.printStock()
                    self.printBRL()
                    self.sellStock()
                    time.sleep(2)
                    self.updateAllData()
                    self.printStock()
                    self.printBRL()
                else:
                    print('Nenhuma ação realizada')

        MaTrader = BinanceTraderBot(STOCK_CODE, OPERATION_CODE, TRADED_QUANTITY, 100, CANDLE_PERIOD)

        while(1):
            MaTrader.execute()
            time.sleep(60)


        #Prints

        #Printa toda a carteira
        def printWallet(self):
            for stock in self.acount_data['balances']:
                if float(stock['free']) > 0:
                    print(stock)

        
        #Printa o ativo definido na classe
        def printStock(self):
            for stock in self.acount_data['balances']:
                if stock['asset'] == self.stock_code:
                    print(stock)

        #printa o saldo em BRL
        def printBRL(self):
            for stock in self.acount_data['balances']:
                if stock['asset'] == 'BRL':
                    print(stock)

        #Gets auxiliares
        #Retorna toda a carteira
        def getWallet(self):
            return self.acount_data['balances']
        #Retorna todo o ativo definido na classe
        def getStock(self):
            for stock in self.acount_data['balances']:
                if stock['asset'] == self.stock_code:
                    return stock