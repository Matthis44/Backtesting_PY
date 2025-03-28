# live_data.py
import asyncio
from abc import ABC
from datetime import datetime
from collections import defaultdict

from binance import AsyncClient, BinanceSocketManager
from event import MarketEvent
from Data.data import DataHandler


class LiveBinanceWebSocketDataHandler(DataHandler, ABC):
    """
    DataHandler en mode live via WebSocket Binance.
    Récupère les flux de marché en direct et publie des MarketEvent.
    """

    def __init__(self, events, symbol_list, interval='1m'):
        self.events = events
        self.symbol_list = [symbol.lower() for symbol in symbol_list]
        self.interval = interval

        self.latest_symbol_data = defaultdict(list)
        self.continue_backtest = True  # ici backtest == stream running

        # Sockets & client
        self.client = None
        self.bsm = None
        self.tasks = []

    async def connect(self):
        self.client = await AsyncClient.create()
        self.bsm = BinanceSocketManager(self.client)

    async def stream_data(self, symbol):
        stream = self.bsm.kline_socket(symbol, interval=self.interval)

        async with stream as s:
            while True:
                msg = await s.recv()
                if msg['e'] == 'kline':
                    kline = msg['k']
                    timestamp = datetime.fromtimestamp(kline['t'] / 1000.0)
                    bar = {
                        'open': float(kline['o']),
                        'high': float(kline['h']),
                        'low': float(kline['l']),
                        'close': float(kline['c']),
                        'volume': float(kline['v'])
                    }

                    self.latest_symbol_data[symbol].append((timestamp, bar))
                    self.events.put(MarketEvent())
                    print(f"[{symbol}] Tick received at {timestamp}")

    async def run(self):
        await self.connect()
        self.tasks = [asyncio.create_task(self.stream_data(symbol)) for symbol in self.symbol_list]
        await asyncio.gather(*self.tasks)

    # Implémentation de l'interface DataHandler :

    def get_latest_bar(self, symbol):
        return self.latest_symbol_data[symbol][-1]

    def get_latest_bars(self, symbol, N=1):
        return self.latest_symbol_data[symbol][-N:]

    def get_latest_bar_datetime(self, symbol):
        return self.get_latest_bar(symbol)[0]

    def get_latest_bar_value(self, symbol, val_type):
        return self.get_latest_bar(symbol)[1][val_type]

    def get_latest_bars_values(self, symbol, val_type, N=1):
        return [bar[1][val_type] for bar in self.get_latest_bars(symbol, N)]

    def update_bars(self):
        pass  # non utilisé ici, car c’est le flux WebSocket qui "pousse" les données
