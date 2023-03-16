from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime, timedelta


PATH = r'D:\Uni\3-PhD\1-Dissertation\4-Webscraping\chromedriver.exe'
URL = 'https://db.edcs.eu/epigr/epi.php?s_sprache=de'
PROVINCE_LIST = ['Achaia', 'Baetica', 'Galatia', 'Mauretania Tingitana',
                 'Regnum Bospori', 'Aegyptus', 'Barbaricum', 'Raetia',
                 'Gallia Narbonensis', 'Mesopotamia', 'Roma', 'Asia',
                 'Aemilia / Regio VIII', 'Belgica', 'Germania inferior',
                 'Moesia inferior', 'Samnium / Regio IV', 'Armenia',
                 'Africa proconsularis', 'Britannia', 'Germania superior',
                 'Moesia superior', 'Sardinia', 'Alpes Cottiae', 'Dacia',
                 'Bruttium et Lucania / Regio III', 'Hispania citerior',
                 'Noricum', 'Sicilia', 'Alpes Graiae', 'Cappadocia',
                 'Italia', 'Numidia', 'Syria', 'Alpes Maritimae', 'Arabia',
                 'Cilicia', 'Latium et Campania / Regio I', 'Palaestina',
                 'Thracia', 'Alpes Poeninae', 'Corsica', 'Macedonia',
                 'Liguria / Regio IX', 'Pannonia inferior', 'Dalmatia',
                 'Transpadana / Regio XI', 'Apulia et Calabria / Regio II',
                 'Creta et Cyrenaica', 'Lugudunensis', 'Pannonia superior',
                 'Umbria / Regio VI', 'Aquitania', 'Aquitanica' 'Cyprus',
                 'Lusitania', 'Picenum / Regio V', 'Pontus et Bithynia',
                 'Venetia et Histria / Regio X', 'Provincia incerta',
                 'Lycia et Pamphylia', 'Etruria / Regio VII',
                 'Mauretania Caesariensis', 'Aquitani(c)a']


def scrape_edcs(date):
    """
    Scrapes the EDCS database on a province-by-province basis.
    For each province which exists in the EDCS database,
    a headless selenium chrome browser opens the EDCS website,
    enters the province in the relevant search field,
    waits until the results page is loaded,
    copies the entire sourcecode, and saves it to a text-file.
    """
    today = date.strftime('%Y-%m-%d')
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()),
                              options=chrome_options)
    driver.set_page_load_timeout(86400)
    for province in PROVINCE_LIST:
        print(province)
        driver.get(URL)
        search_bar = driver.find_element(By.NAME, 'p_provinz')
        search_bar.clear()
        search_bar.send_keys(province)
        search_bar.send_keys(Keys.RETURN)
        sourcetext = driver.page_source
        province = province.replace('/', '-')
        name = "EDCS_HTML_" + province + '_' + today + ".txt"
        with open(name, 'w', encoding="utf-8") as f:
            f.write(sourcetext)


def merge_sourcetext(today):
    """
    Merges the sourcetext of different provinces into one file.
    For each province in the PROVINCE_LIST, opens the corresponding
    HTML-file and appends HTML code to a list.
    Once all files are processed, the text from the sourcecode_list
    is concatenated into one long string and saved to disk.
    """
    sourcetext_list = []
    for province in PROVINCE_LIST:
        province = province.replace('/', '-')
        date = today
        searching = True
        while searching:
            date_str = date.strftime('%Y-%m-%d')
            filename = "EDCS_HTML_" + province + '_' + date_str + ".txt"
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    sourcecode = f.read()
                searching = False
            except FileNotFoundError:
                date = (date - timedelta(days=1))
        sourcetext_list.append(sourcecode)
    complete_text = '\n\nNEW PROVINCE\n\n'.join(sourcetext_list)
    today_str = today.strftime('%Y-%m-%d')
    name = 'EDCS_HTML_allprovinces_' + today_str + '.txt'
    with open(name, 'w', encoding='utf-8') as f:
        f.write(complete_text)


def main():
    """
    Main function, used to organise the script.
    """
    today = datetime.today()
    scrape_edcs(today)
    merge_sourcetext(today)


if __name__ == '__main__':
    main()
