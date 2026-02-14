import logging
from datetime import datetime

# Define o logger
logging.basicConfig(
    filename='trading_bot.log',  
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def format_number(value, decimals=8):
    """
    Formata um número para exibição legível, arredondando e adicionando separadores de milhar.
    """
    if isinstance(value, str):  
        try:
            value = float(value)  # Converte strings numéricas para float
        except ValueError:
            return value  # Retorna como está se não for um número válido
    return f"{value:,.{decimals}f}"  # Formata com separador de milhar e casas decimais

def createLogOrder(order):
    """
    Printa e cria um log de ordem de compra ou venda
    a partir do objeto retornado pela API da Binance.
    """
    side = order['side']
    order_type = order['type']
    quantity = format_number(order['executedQty'], 6)  # Arredondando para 6 casas decimais
    asset = order['symbol']
    
    # Pegando o primeiro fill e formatando os valores
    price_per_unit = format_number(order['fills'][0]['price'], 6)
    currency = order['fills'][0]['commissionAsset']
    total_value = format_number(order['cummulativeQuoteQty'], 2)  # Para valores totais, 2 casas decimais

    timestamp = order['transactTime']
    datetime_transact = datetime.utcfromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')

    # Criando a mensagem de log formatada
    log_message = (
        "\n-----------------------\n"
        "ORDEM EXECUTADA\n"
        f"Side: {side}\n"
        f"Ativo: {asset}\n"
        f"Quantidade: {quantity}\n"
        f"Valor por unidade: {price_per_unit}\n"
        f"Moeda: {currency}\n"
        f"Valor total em {currency}: {total_value}\n"
        f"Tipo de Ordem: {order_type}\n"
        f"Data/Hora: {datetime_transact}\n"
        "\nOrdem completa:\n"
        f"{order}\n"
        "\n------------------------\n"
    )

    # Criando a mensagem para exibir no console
    print_message = (
        "\n-----------------------\n"
        "ORDEM EXECUTADA\n"
        f"Side: {side}\n"
        f"Ativo: {asset}\n"
        f"Quantidade: {quantity}\n"
        f"Valor por unidade: {price_per_unit}\n"
        f"Moeda: {currency}\n"
        f"Valor total em {currency}: {total_value}\n"
        f"Tipo de Ordem: {order_type}\n"
        f"Data/Hora: {datetime_transact}\n"
    )

    # Exibe no console
    print(print_message)

    # Grava no arquivo de log
    logging.info(log_message)




