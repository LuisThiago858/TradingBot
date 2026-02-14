# 🤖 TradingBot — Bot de Trading Automatizado para Binance

> **Aviso:** Este projeto é **educacional**. Não constitui recomendação financeira. Use somente após testes extensivos na *Testnet*. Operar em produção envolve risco real de perda de capital.

---

## 📌 Visão Geral
O **TradingBot** é um bot de negociação automatizada em Python que se conecta à **API da Binance** para executar ordens de compra e venda com base em estratégias quantitativas. O sistema coleta dados históricos de mercado (candles/klines), aplica uma estratégia de decisão e envia ordens automaticamente, incluindo **gestão de risco com OCO (Stop Loss + Take Profit)**.

O projeto foi pensado para ser:
- Simples de entender
- Modular (estratégias plugáveis)
- Seguro para testes (Testnet habilitada)
- Extensível para novos indicadores e modelos

---

## ✨ Principais Funcionalidades

- Conexão com a **Binance API** (Testnet ou Produção)
- Coleta automática de dados OHLCV
- Execução de estratégias de trading
- Estratégia de cruzamento de médias móveis (SMA Cross)
- Execução automática de ordens
- Ordens OCO (Take Profit + Stop Loss)
- Gestão básica de posição
- Sistema de logs detalhado
- Estrutura orientada a objetos

---

## 🧠 Estratégia Implementada
### Moving Average Cross Strategy (SMA Cross)
A estratégia atual utiliza o cruzamento entre duas médias móveis simples:

- **SMA Curta (Short Window)**
- **SMA Longa (Long Window)**

#### Sinal de Compra
Quando a média curta cruza **de baixo para cima** a média longa.

#### Sinal de Venda
Quando a média curta cruza **de cima para baixo** a média longa.

Este tipo de estratégia é conhecido como *trend following* (seguidora de tendência).

---

## 🧱 Arquitetura do Projeto

```
TradingBot/
│
├── tradingbot.py        # Núcleo principal do bot
├── Logger.py            # Configuração de logs
├── backup.py            # Utilitário auxiliar
├── requirements.txt     # Dependências
├── .env.example         # Modelo de configuração
├── trading_bot.log      # Arquivo de logs gerados
└── .env                 # Suas chaves (não versionar!)
```

### Componentes

| Componente | Responsabilidade |
|----------|------|
| `Strategy` | Interface base de estratégias |
| `MovingAverageCrossStrategy` | Implementação de decisão de compra/venda |
| `TradingBot` | Motor principal do sistema |
| `Logger` | Registro de eventos |

---

## ⚙️ Requisitos

- Python 3.10+
- Conta na Binance
- Chaves de API habilitadas para trading

---

## 🔑 Criando API Key na Binance (TESTNET)
1. Acesse: https://testnet.binance.vision/
2. Faça login com GitHub
3. Crie uma API Key
4. Copie:
   - API Key
   - Secret Key

⚠️ **Nunca compartilhe essas chaves.**

---

## 🧪 Instalação

### 1) Clonar o repositório
```bash
git clone https://github.com/LuisThiago858/TradingBot.git
cd TradingBot
```

### 2) Criar ambiente virtual

#### Windows (PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

#### Linux/Mac
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3) Instalar dependências
```bash
pip install -r requirements.txt
```

---

## 🔐 Configuração (.env)
Crie um arquivo `.env` baseado no `.env.example`:

```
BINANCE_API_KEY=SEU_API_KEY
BINANCE_API_SECRET=SUA_SECRET_KEY
```

---

## ▶️ Executando o Bot

```bash
python tradingbot.py
```

Ao iniciar, o bot:
1. Conecta à Binance
2. Baixa candles históricos
3. Avalia a estratégia
4. Decide comprar ou vender
5. Executa ordem automaticamente

---

## 🛡️ Gestão de Risco
Após uma compra, o bot pode criar automaticamente uma ordem **OCO**:

- Stop Loss → Limita perdas
- Take Profit → Garante lucro

Parâmetros configuráveis:

| Parâmetro | Descrição |
|---|---|
| `stop_loss_multiplier` | Percentual máximo de perda |
| `take_profit_multiplier` | Percentual alvo de ganho |

Exemplo:
```
stop_loss_multiplier = 0.98  (-2%)
take_profit_multiplier = 1.02 (+2%)
```

---

## 📊 Logs
Todos os eventos são registrados em:
```
trading_bot.log
```

Exemplo:
```
[2025-02-12 21:10:02] INFO - TradingBot - Executando ordem de compra BTCUSDT
```

---

## 🔄 Como Adicionar Nova Estratégia
Basta criar uma classe herdando de `Strategy`:

```python
class MinhaEstrategia(Strategy):
    def should_buy(self, df):
        return condicao_de_compra

    def should_sell(self, df):
        return condicao_de_venda
```

Depois instanciar no bot:

```python
strategy = MinhaEstrategia()
bot = TradingBot(api_key, api_secret, strategy)
```

---

## 💡 Ideias de Melhorias (Roadmap)
- Backtesting histórico
- Interface Web (Dashboard)
- Múltiplos pares simultâneos
- Indicadores técnicos (RSI, MACD, Bollinger Bands)
- Banco de dados para histórico de trades
- Integração com Telegram/Discord
- Machine Learning para previsão

---

## ⚠️ Boas Práticas
- Sempre iniciar na **Testnet**
- Operar primeiro com valores mínimos
- Nunca deixar rodando sem monitoramento
- Monitorar logs diariamente
- Não commitar o `.env`
- Não versionar a pasta `venv/`

---

## 🧾 Disclaimer
Este software é fornecido apenas para fins educacionais. O autor não se responsabiliza por perdas financeiras decorrentes do uso do sistema. Trading envolve risco elevado e pode resultar em perda total do capital investido.

---

## 🤝 Contribuição
Pull requests são bem-vindos.

1. Fork o projeto
2. Crie uma branch (`feature/minha-feature`)
3. Commit suas mudanças
4. Push para sua branch
5. Abra um Pull Request

---

## 📜 Licença
Uso apenas educacional e pessoal.

---

## 👨‍💻 Autor
Projeto desenvolvido para estudos em automação de trading quantitativo usando Python e Binance API.

