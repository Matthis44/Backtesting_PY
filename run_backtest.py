# run_backtest.py

import pandas as pd
from backtest import Backtest

# Modules internes
from Data.mysql_data_handler import MySQLDataHandler  # ou HistoricCSVDataHandler si tu utilises des CSV
from Strategy.moving_average_cross_strategy import MovingAverageCrossStrategy
from execution import SimulatedExecutionHandler
from portfolio import Portfolio

if __name__ == "__main__":
    # === CONFIGURATION ===
    DATA_SOURCE = "mysql"  # 'mysql' ou 'csv'
    SYMBOLS = ["AAPL"]
    START_DATE = pd.Timestamp("2000-01-01")
    INITIAL_CAPITAL = 10000.0
    HEARTBEAT = 0.0  # instantané pour le backtest

    if DATA_SOURCE == "mysql":
        data_handler_class = MySQLDataHandler
        data_config = {
            "user": "sec_user",
            "password": "1Lo2Ma3Is@",
            "host": "localhost",
            "db": "securities_master"
        }
    elif DATA_SOURCE == "csv":
        from Data.data import HistoricCSVDataHandler  # si tu as un CSV handler
        data_handler_class = HistoricCSVDataHandler
        data_config = {
            "csv_dir": "data/"  # dossier contenant les fichiers AAPL.csv, etc.
        }
    else:
        raise ValueError("DATA_SOURCE must be 'mysql' or 'csv'")

    # === LANCEMENT DU BACKTEST ===
    print("Démarrage du backtest...")

    bt = Backtest(
        symbol_list=SYMBOLS,
        initial_capital=INITIAL_CAPITAL,
        heartbeat=HEARTBEAT,
        start_date=START_DATE,
        data_handler=data_handler_class,
        execution_handler=SimulatedExecutionHandler,
        portfolio=Portfolio,
        strategy=MovingAverageCrossStrategy,
        data_source_type=DATA_SOURCE,
        data_source_config=data_config
    )

    bt.simulate_trading()
    print("Backtest terminé.")
