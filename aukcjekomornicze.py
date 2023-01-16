from datetime import datetime
from selenium import webdriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from collections import defaultdict
import pandas as pd
import numpy as np
import math
import logging


class WebArticle:
    def __init__(self, title, location, params):
        self.title = title
        self.location = location
        self.params = params


class AHOffer:
    def __init__(self, title, rooms, building_area, land_area, price, location):
        self.title = title
        self.rooms = rooms
        self.building_area = building_area
        self.land_area = land_area
        self.price = price
        self.location = location

    def to_dict(self):
        return {
            "title": self.title,
            "rooms": self.rooms,
            "building_area": self.building_area,
            "land_area": self.land_area,
            "price": self.price,
            "location": self.location,
        }


# Initialize variable
app_name = "BailiffAutions"
today_date = datetime.today().strftime("%Y-%m-%d")
dir_path = "Provide path to target destination"
logging.basicConfig(
    filename= dir_path + app_name + "_" + today_date + ".log",
    level=logging.INFO,
    format="%(asctime)s:%(levelname)s:%(message)s",
)
file_name = dir_path + "aukcjekomornicze_" + today_date + ".csv"
options = Options()
# options.add_argument("start-maximized")
options.add_argument("--disable-javascript")
# options.add_argument("--headless")
url = r"https://www.otodom.pl/shop/komornicze-licytacje-IDttMr"


# definitions
def getNumberOfPages(initialPageContent: WebElement) -> int:
    logging.info("Get number of Pages.")
    offers_per_page = 25
    number_of_offers_description = initialPageContent.find_elements(
        By.CLASS_NAME, "offers-index"
    )[0]
    number_of_offers = int(
        number_of_offers_description.find_elements(By.TAG_NAME, "strong")[0].text
    )
    number_of_pages = math.ceil(number_of_offers / offers_per_page)
    return number_of_pages


def getWebArticlesFromPage(pageContent: WebElement) -> list[WebArticle]:
    logging.info("Get web articles from page.")
    articles_web = pageContent.find_elements(By.TAG_NAME, "article")
    articles = [
        WebArticle(
            article.find_elements(By.CLASS_NAME, "offer-item-title")[0].text,
            article.find_elements(By.TAG_NAME, "p")[0].text.split(": ")[1],
            article.find_elements(By.CLASS_NAME, "params")[0],
        )
        for article in articles_web
    ]
    return articles


def mapArticleParamsToDict(articles: list[WebArticle]) -> None:
    logging.info("Map article params to dictionary.")
    for article in articles:
        offer_details = article.params.find_elements(By.TAG_NAME, "li")
        details_dict = defaultdict(list)
        for offerD in offer_details:
            key = offerD.get_attribute("class")
            value = offerD.text
            details_dict[key].append(value)
        article.params = details_dict


def mapWebArticlesToAHOffers(articles: list[WebArticle]) -> list[AHOffer]:
    logging.info("Map web articles to AH offers.")
    mapArticleParamsToDict(articles)
    ahoffers = []
    for article in articles:
        details = article.params
        title = article.title
        rooms = (
            details["offer-item-rooms hidden-xs"][0]
            if details["offer-item-rooms hidden-xs"]
            else np.nan
        )
        area_list = (
            details["hidden-xs offer-item-area"]
            if details["hidden-xs offer-item-area"]
            else np.nan
        )
        building_area = area_list[0] if area_list else np.nan()
        land_area = area_list[1] if len(area_list) > 1 else np.nan
        price = (
            details["offer-item-price"][0] if details["offer-item-price"] else np.nan
        )
        location = article.location
        ahoffers.append(
            AHOffer(title, rooms, building_area, land_area, price, location)
        )
    return ahoffers


def cleanDataFrame(df: pd.DataFrame) -> pd.DataFrame:
    logging.info("Clean dataframe.")
    title_contains_dzialka = df["title"].str.contains("Działk", case=False, regex=True)
    df.loc[df["rooms"].isna() & title_contains_dzialka, "land_area"] = df["building_area"]
    df.loc[df["rooms"].isna() & title_contains_dzialka, "building_area"] = np.nan
    df[["City", "powiat", "District"]] = df["location"].str.split(", ", 0, expand=True)
    districtisblank = df["District"].isna()
    df.loc[districtisblank, "District"] = df["powiat"]
    del df["powiat"]
    return df


def main():
    try:
        logging.info("Install webdriver.")
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=options
        )
        driver.get(url)
        initialPageContent = driver.find_element(By.CLASS_NAME, "col-md-shop-content")
        numberOfPages = getNumberOfPages(initialPageContent)
        appendedAhOffers = []
        for page in range(1, numberOfPages + 1):
            page_url = url + "?page=" + str(page)
            logging.info("Get data from url: " + page_url)
            driver.get(page_url)
            pageContent = driver.find_element(By.CLASS_NAME, "col-md-shop-content")
            articles = getWebArticlesFromPage(pageContent)
            ahoffers = mapWebArticlesToAHOffers(articles)
            appendedAhOffers.extend(ahoffers)
        df = pd.DataFrame.from_records([offer.to_dict() for offer in appendedAhOffers])
        cleanedDf = cleanDataFrame(df)
        cleanedDf.to_csv(file_name, sep=",", encoding="utf-8")
        logging.info("Close driver.")
        driver.close()
    except Exception as e:
        print(e)
        logging.error(e)


if __name__ == "__main__":
    main()
