from datetime import datetime
import pandas as pd
from requests_html import HTMLSession
import time
import pymysql
import os
import yaml
from io import StringIO
import requests
import random
from dotenv import load_dotenv

load_dotenv()

class Scraper:
    def __init__(self) -> None:
        self.good_proxies = set()
        # self.crypto_scrape_data = None
        with open("headers.yml") as f_headers:
            self.browser_headers = yaml.safe_load(f_headers)
        self.URL = os.getenv("URL_CRYPTOS")
        self.session = HTMLSession()
        
        # Connexion à la base de données (adapter selon tes paramètres)
        self.connection = pymysql.connect(
            host=os.getenv("MYSQL_HOST"),
            user=os.getenv("MYSQL_USER"),
            password=os.getenv("MYSQL_PASSWORD"),
            db=os.getenv("MYSQL_DATABASE")
        )


    def get_list(self):
        print("💲 - Looking for cryptos")
        max_retry = 10
        actual_try = 0
        while True:
            print("☁️ - fetching for cryptos")
            self.session.headers = {}
            browser = self.get_browser()
            self.session.headers.update(
                self.browser_headers[browser]
            )
            random_proxy = self.get_random_proxy()
            print(f"🍀 - trying '{random_proxy}', wish me luck !")
            proxies = {"http": random_proxy, "https": random_proxy}
            try:
                r = self.session.get(f"{self.URL}?t={int(time.time())}", proxies=proxies, timeout=10)
                if r.status_code == 200:
                    self.crypto_scrape_data = r.text

                    print(f"😶‍🌫️ - data form cryptos found using : '{browser}' and proxy : '{random_proxy}'")
                    table = r.html.find("tbody", first=True)

                    rows = [elem.text.split("\n") for elem in table.find("tr")]

                    cryptos = []
                    date = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
                    for crypto in rows:
                        if len(crypto) > 2:
                            cryptos.append((crypto[1], float(crypto[3].replace('$', '').replace(',', '')), date))
                        else:
                            cryptos.append((crypto[0], float(crypto[1].replace('$', '').replace(',', '')), date))

                    print("💰 - Crypto grinded")
                    return cryptos
            except Exception as e:
                print("💀 - ", e)
                if actual_try == max_retry:
                    break
                actual_try += 1
                continue
            
        
    
    def get_valid_proxies(self):
        print("♻️ - Clearing old proxies")
        self.good_proxies.clear()
        print("🔎 - Looking for valid proxies")
        response = requests.get("https://free-proxy-list.net/")
        html_content = StringIO(response.text)
        proxy_list = pd.read_html(html_content)[0]
        proxy_list["url"] = "http://" + proxy_list["IP Address"] + ":" + proxy_list["Port"].astype(str)
        proxy_list.head()
        https_proxies = proxy_list[proxy_list["Https"] == "yes"]
        https_proxies.count()
        url = "https://httpbin.org/ip"
        headers = self.browser_headers[self.get_browser()]
        for proxy_url in https_proxies["url"]:
            proxies = {
                "http": proxy_url,
                "https": proxy_url,
            }
            
            try:
                response = requests.get(url, headers=headers, proxies=proxies, timeout=2)
                self.good_proxies.add(proxy_url)
                print(f"💫 - {proxy_url}")
            except Exception:
                pass
        
            if len(self.good_proxies) >= 20:
                break
        if len(self.good_proxies) > 0:
            print(f"✅ - Found {len(self.good_proxies)} proxies")
        else:
            print(f"❌ - 0 proxy found")
    
    def get_browser(self):
        browers = ["IE", "Firefox", "Edge", "Chrome"]
        print("🎲 - Select a random brower's header")
        return browers[random.randint(0, len(browers) - 1)]
    
    def get_random_proxy(self):
        print("🎲 - Select a random proxy's ip ")
        return random.choice(list(self.good_proxies))

    
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
        # finally:
        #     self.connection.close()

        


if __name__ == "__main__":
    scraper = Scraper()

    while True:
        while True:
            scraper.get_valid_proxies()
            if len(scraper.good_proxies) > 0:
                break
        for i in range(3): # Environ toutes les 5min, on change les proxies
            scraper.store_cryptos()
            print('⌛ - Waiting 10s')
            time.sleep(10)
        break