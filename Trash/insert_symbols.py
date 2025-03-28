#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime
import requests
from bs4 import BeautifulSoup
import mysql.connector  # On utilise mysql-connector-python (pas MySQLdb)

def obtain_parse_wiki_snp500():
    """
    Télécharge et parse la liste des entreprises du S&P500
    depuis Wikipedia avec BeautifulSoup.
    Retourne une liste de tuples prêts à insérer en base.
    """
    now = datetime.datetime.utcnow()

    response = requests.get(
        "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    )
    soup = BeautifulSoup(response.text, "html.parser")

    symbolslist = soup.select("table")[0].select("tr")[1:]

    symbols = []
    for symbol in symbolslist:
        tds = symbol.select("td")
        if len(tds) >= 4:
            symbols.append(
                (
                    tds[0].select("a")[0].text.strip(),  # Ticker
                    "stock",
                    tds[1].text.strip(),                 # Name
                    tds[3].text.strip(),                 # Sector
                    "USD",
                    now,
                    now
                )
            )
    return symbols

def insert_snp500_symbols(symbols):
    """
    Insère les données des symboles dans la base MySQL
    """
    db_config = {
        "host": "localhost",
        "user": "sec_user",
        "password": "1Lo2Ma3Is@",  # remplace par ton vrai mot de passe
        "database": "securities_master"
    }

    con = mysql.connector.connect(**db_config)

    column_str = """ticker, instrument, name, sector,
                    currency, created_date, last_updated_date"""
    insert_str = ("%s, " * 7)[:-2]
    final_str = f"INSERT INTO symbol ({column_str}) VALUES ({insert_str})"

    with con.cursor() as cur:
        cur.executemany(final_str, symbols)
        con.commit()

# Point d'entrée du script
if __name__ == "__main__":
    symbols = obtain_parse_wiki_snp500()
    insert_snp500_symbols(symbols)
    print(f"{len(symbols)} symbols were successfully added.")
