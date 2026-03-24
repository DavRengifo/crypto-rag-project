from datetime import datetime
from requests_html import HTMLSession
import time
import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

class Scraper:
    def __init__(self) -> None:
        self.URL = os.getenv("URL_CRYPTOS")
        self.session = HTMLSession()

        # Ajout d'un user-agent pour éviter le blocage
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })
        
        # Connexion à la base de données (adapter selon tes paramètres)
        self.connection = pymysql.connect(
            host=os.getenv("MYSQL_HOST"),
            user=os.getenv("MYSQL_USER"),
            password=os.getenv("MYSQL_PASSWORD"),
            db=os.getenv("MYSQL_DATABASE")
        )


    def get_list(self):
        r = self.session.get(self.URL)
        table = r.html.find("tbody", first=True)

        rows = [elem.text.split("\n") for elem in table.find("tr")]

        cryptos = []
        date = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
        for crypto in rows:
            if len(crypto) > 2:
                cryptos.append((crypto[1], float(crypto[3].replace('$', '').replace(',', '')), date))
            else:
                cryptos.append((crypto[0], float(crypto[1].replace('$', '').replace(',', '')), date))

        return cryptos
    
    def store_cryptos(self):
        cryptos = self.get_list()
        # Entrer en BDD de façon BATCH
        try:
            with self.connection.cursor() as cursor:
                # Requête d'insertion en batch
                query = "INSERT INTO cryptos (nom, valeur, date) VALUES (%s, %s, %s)"
                
                # Insertion des données en batch
                cursor.executemany(query, cryptos)

            # Validation de la transaction
            self.connection.commit()

        except Exception as e:
            print(f"Erreur lors de l'insertion en BDD: {e}")
        finally:
            self.connection.close()  # Fermer la connexion après utilisation


if __name__ == "__main__":
    scraper = Scraper()

    while True:
        scraper.store_cryptos()
        print('done')
        time.sleep(5)
        break