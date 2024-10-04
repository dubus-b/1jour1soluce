from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
import argparse
import json
import redis


from tmdb import TMDB_ENGINE

API_KEY = ""
CHROMEDRIVER_PATH = ''

r = redis.Redis(host='localhost', port=6379, db=0)


year = 2000

def victoire(driver):
    try:
        WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".MuiTypography-root.MuiTypography-h2.mui-1misjte"))
        )
        return True  # L'élément est trouvé
    except :
        return False  # L'élément n'est pas trouvé

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-search-engine-choice-screen")
    service = Service(CHROMEDRIVER_PATH)
    return webdriver.Chrome(service=service, options=chrome_options)


def get_first_actor_and_director(driver):
    acteurs_elements = driver.find_elements(By.CSS_SELECTOR, ".MuiGrid2-root.MuiGrid2-direction-xs-row.MuiGrid2-grid-xs-12.mui-qcpu3v .mui-cdkrf0")
    acteurs = [acteur.text for acteur in acteurs_elements] 
    return acteurs

     

def get_movie(engine):
    time.sleep(2)
    json_data_from_queue = r.rpop('movie_queue')
    if json_data_from_queue:
        movie = json.loads(json_data_from_queue)
        return movie
    else:
        engine.get_popular_movies()
        return None
    



def cheat(engine):
    driver = setup_driver()
    try:
        driver.get("https://1jour1film.fr/")
        svg_element = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'svg[aria-hidden="true"][data-testid="CloseIcon"]'))
        )
        svg_element.click()
        input_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, ":r0:"))
        )
        v = False
        while v is False:
            engine.movie.dump_info()
            movie  = get_movie(engine)
            if movie:
                input_element.click()
                input_element.clear()
                input_element.send_keys(movie['title'])
                time.sleep(3)
                input_element.send_keys(Keys.RETURN)
                wait = WebDriverWait(driver, 30)
                first_stack_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.MuiStack-root.mui-1qvrhbk')))
                
                buttons = first_stack_element.find_elements(By.CSS_SELECTOR, 'button.MuiButton-root')
                button_texts = [button.text for button in buttons]
                engine.parse_clue(button_texts)
                engine.set_actors(get_first_actor_and_director(driver))
            v = victoire(driver)

    finally:
        driver.quit()

def main():
    engine = TMDB_ENGINE()
    cheat(engine)

if __name__ == '__main__':
    main()
