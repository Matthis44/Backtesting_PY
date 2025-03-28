from collections import defaultdict
from sqlalchemy import create_engine, text
import pandas as pd
from urllib.parse import quote_plus

from event import MarketEvent  # <- à adapter selon ton architecture
from Data.data import DataHandler   # <- même remarque

class MySQLDataHandler(DataHandler):
    """
    DataHandler qui lit les données OHLCV depuis ta base MySQL 'securities_master'
    """

    def __init__(self, events, symbol_list, user="sec_user", password="1Lo2Ma3Is@", host="localhost", db="securities_master"):
        """
        Params :
        - events : queue d'évènements
        - symbol_list : tickers à charger (ex : ['AAPL', 'GOOG'])
        - user, password, host, db : infos de connexion MySQL
        """
        self.events = events
        self.symbol_list = symbol_list
        self.symbol_data = {}
        self.latest_symbol_data = defaultdict(list)
        self.continue_backtest = True
        safe_password = quote_plus(password)
        self.engine = create_engine(f"mysql+mysqlconnector://{user}:{safe_password}@{host}/{db}")
        self._load_data_from_db()

    def _load_data_from_db(self):
        """
        Charge les données OHLCV depuis la base pour chaque ticker
        """
        with self.engine.connect() as conn:
            for symbol in self.symbol_list:
                query = text("""
                    SELECT dp.price_date AS datetime,
                           dp.open_price AS open,
                           dp.high_price AS high,
                           dp.low_price AS low,
                           dp.close_price AS close,
                           dp.adj_close_price AS adj_close,
                           dp.volume AS volume
                    FROM daily_price dp
                    JOIN symbol s ON dp.symbol_id = s.id
                    WHERE s.ticker = :symbol
                    ORDER BY dp.price_date ASC
                """)
                df = pd.read_sql(query, conn, params={'symbol': symbol})
                df.set_index("datetime", inplace=True)
                self.symbol_data[symbol] = df.iterrows()

    def _get_new_bar(self, symbol):
        for bar in self.symbol_data[symbol]:
            yield bar

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
        """
        Simule l’arrivée d’un nouveau tick en poussant un bar dans le système
        """
        for symbol in self.symbol_list:
            try:
                bar = next(self._get_new_bar(symbol))
            except StopIteration:
                self.continue_backtest = False
            else:
                self.latest_symbol_data[symbol].append(bar)

        self.events.put(MarketEvent())
