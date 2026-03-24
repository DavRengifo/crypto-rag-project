import chromedriver_autoinstaller
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd

# Installer et charger le driver Chrome
chromedriver_autoinstaller.install()
service = Service()
driver = webdriver.Chrome(service=service)
url = "https://coinmarketcap.com/"
driver.get(url)

# Vider le cache de Selenium
driver.execute_cdp_cmd('Network.clearBrowserCache', {})

# Attendre que les éléments spécifiques soient chargés
WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".cmc-table")))

from bs4 import BeautifulSoup

def extract_crypto_data():
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    # Trouver le div contenant la table des crypto-monnaies
    crypto_div = soup.find('div', class_='sc-7b3ac367-2')
    
    if crypto_div is None:
        raise ValueError("Le div contenant la table des crypto-monnaies n'a pas été trouvé.")
    
    # Trouver la table dans le div
    table = crypto_div.find('table', class_='sc-7b3ac367-3')
    
    if table is None:
        raise ValueError("La table des crypto-monnaies n'a pas été trouvée.")
    
    # Trouver le tbody dans la table
    crypto_tbody = table.find('tbody')
    
    if crypto_tbody is None:
        raise ValueError("Le tbody contenant les données des crypto-monnaies n'a pas été trouvé.")
    
    rows = crypto_tbody.find_all('tr')
    
    data = []
    
    for row in rows[:10]:
        cols = row.find_all('td')
        # print(cols)
        if len(cols) >= 2:
            # Trouver le nom de la crypto-monnaie
            name_element = cols[2].find('div', class_='sc-65e7f566-0')
            name = name_element.find('p', class_='sc-65e7f566-0').text.strip() if name_element else ""            
            # Trouver le prix
            price_element = cols[3].find('div', class_='sc-b3fc6b7-0 dzgUIj')
            print(price_element)
            price =  float(price_element.text.strip().replace('$', '').replace(',', ''))
            
            data.append({'Name': name, 'Price': price})
    
    return data


crypto_data = extract_crypto_data()
df = pd.DataFrame(crypto_data)
print(df)
df.to_csv('out.csv', index=False)
driver.quit()
