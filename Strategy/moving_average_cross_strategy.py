# moving_average_cross_strategy.py
from Strategy.strategy import Strategy
from event import SignalEvent
import numpy as np  # en haut du fichier si ce n'est pas déjà fait

class MovingAverageCrossStrategy(Strategy):
    """
    Stratégie de croisement de moyennes mobiles :
    - LONG quand SMA courte > SMA longue
    - EXIT quand SMA courte < SMA longue
    """

    def __init__(self, data_handler, events, short_window=40, long_window=100):
        self.data_handler = data_handler
        self.events = events
        self.short_window = short_window
        self.long_window = long_window
        self.symbol_list = self.data_handler.symbol_list

        # Initialise l'état (pas encore en position)
        self.bought = {symbol: False for symbol in self.symbol_list}

    def calculate_signals(self, event):
        if event.type != 'MARKET':
            return

        for symbol in self.symbol_list:
            # Récupère les prix de clôture nécessaires
            bars = self.data_handler.get_latest_bars_values(symbol, "adj_close", N=self.long_window)

            if bars is None or len(bars) < self.long_window:
                continue  # On attend d'avoir assez de données



            short_sma = np.mean(bars[-self.short_window:])
            long_sma = np.mean(bars)

            dt = self.data_handler.get_latest_bar_datetime(symbol)

            # STRATÉGIE
            if short_sma > long_sma and not self.bought[symbol]:
                signal = SignalEvent("MACross", symbol, dt, "LONG", 1.0)
                self.events.put(signal)
                self.bought[symbol] = True
                print(f"[{dt}] Signal LONG sur {symbol} (SMA{self.short_window}>{self.long_window})")

            elif short_sma < long_sma and self.bought[symbol]:
                signal = SignalEvent("MACross", symbol, dt, "EXIT", 1.0)
                self.events.put(signal)
                self.bought[symbol] = False
                print(f"[{dt}] Signal EXIT sur {symbol} (SMA{self.short_window}<{self.long_window})")
