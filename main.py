from unidecode import unidecode
from bs4 import BeautifulSoup
from datetime import date
from datetime import time
from typing import List
import pandas as pd
import jdatetime
import traceback
import requests
import copy
import time

LIST_OF_DICT = List[dict]
links = []

primary_url = input("enter url : ")
max_page_count = int(input("enter max page : "))


# Crawling page that we wanna extract data from them
def page_counter() -> int:
    page_counts = 0
    site = requests.get(primary_url)
    soup = BeautifulSoup(site.text, 'lxml')
    if soup.select_one(".c-pager__next"):
        page_counts = int(soup.select_one(".c-pager__next")["data-page"])
    else:
        for x in range(20):
            page_content = soup.find('div', id='content').find('ul', class_='c-listing__items js-plp-products-list')
            try:
                if page_content.div.div.div.p.text == 'جستجو برای این ترکیب از فیلترها با هیچ کالایی هم‌خوانی نداشت.':
                    page_counts -= 1
                    break
            except:
                page_counts += 1
    return page_counts


# Get links of products from pages(each page has 36 links maximum)
def get_links(page_num: str) -> None:
    global links
    # Add "pageno" parameter to url
    if "?" in primary_url:
        url = primary_url + '&pageno=' + page_num
    else:
        url = primary_url + '?pageno=' + page_num

    print(url)
    web_site_loader = requests.get(url)
    soup_loader = BeautifulSoup(web_site_loader.text, 'lxml')
    site_table = soup_loader.select_one('ul.c-listing__items')
    products = site_table.select('li .c-product-box')

    # After make a list of URLs of products, add product address to link list
    for product in products:
        try:
            link = 'https://www.digikala.com' + product.select_one("a.js-product-url")['href']
            print(link)
            links.append(link)
        except Exception as E:
            print(product)
            traceback.print_exc()
            time.sleep(0.5)


# Get and save info from each product,
# this func take an address of product
# and give us dict of information about product
def get_info(address: str) -> dict:
    site = requests.get(address)
    soup = BeautifulSoup(site.text, 'lxml')
    try:
        brand = soup.select_one('.c-product__title-container--brand-link').text.strip()
    except Exception:
        brand = None

    try:
        seller = soup.select_one('.c-product__seller-name').text.strip()
    except Exception:
        seller = None

    try:
        price = soup.select_one('.c-product__seller-price-prev').text.strip()
        price = unidecode(price.replace(",", ""))
    except Exception:
        price = None

    try:
        off_price = soup.select_one('.c-product__seller-price-pure').text.strip()
        off_price = unidecode(off_price.replace(",", ""))
    except Exception:
        off_price = None

    try:
        title = soup.select_one('.c-product__title').text.strip()
    except Exception:
        title = None

    try:
        image = soup.select_one('.js-gallery-img')["data-src"]

        # remove parameters of image's URL
        image = image.split("?")[0]
    except Exception:
        image = None

    try:
        rating = soup.select_one('.c-product__engagement-rating').text.strip()
        rating = unidecode(rating.replace(soup.select_one('.c-product__engagement-rating-num').text.strip(), ""))
    except Exception:
        rating = None

    try:
        rating_count = unidecode(soup.select_one('.c-product__engagement-rating-num').text.strip())
        rating_count = rating_count.replace("(", "")
        rating_count = rating_count.replace(")", "")
    except Exception:
        rating_count = None

    # Get time series of price for each one of products
    try:
        product_id = address.split("/")[4].replace("dkp-", "")
        product_price_series_data = requests.get(
            f'https://www.digikala.com/ajax/product/price-chart/{product_id}/').json()
        final_price_series = []
        if product_price_series_data["data"]:
            for i in product_price_series_data["data"]["Series"][0]["data"]:
                final_price_series.append(
                    {"time": product_price_series_data["data"]["Days"][i["day"]].replace("/", "-"),
                     "off_price": (int(i["price"]) // 10) if i["price"] else i["price"],
                     "price": (int(i["rrp"]) // 10) if i["rrp"] else i["rrp"],
                     "seller": i["seller"]
                     })
    except Exception as E:
        traceback.print_exc()
        final_price_series = []

    param_block = soup.select_one('ul.c-params__list')
    params = param_block.select('li')
    params_data = {}

    for param in params:
        try:
            param_key = param.select_one('.c-params__list-key').text.strip()
            param_value = param.select_one('.c-params__list-value').text.strip()
        except Exception:
            param_key = None
            param_value = None
        params_data[param_key] = param_value

    # Extract weight from parameters
    weight = params_data.get("وزن", None)
    if weight:
        weight = weight.replace("گرم", "")
        weight = weight.strip()

    # persian calender
    time = str(jdatetime.date.fromgregorian(date=date.today()))

    # Georgian Year
    # time = date.today()

    return {
        'title': title,
        'brand': brand,
        'price': price,
        'weight': weight,
        'off_price': off_price,
        'seller': seller,
        'rating': rating,
        'rating_count': rating_count,
        'image': image,
        'time': time,
        'params': params_data,
        'price_series': final_price_series,
    }


def get_all_product_of_category() -> LIST_OF_DICT:
    pages = min(max_page_count, page_counter())
    print(pages, 'pages were found')
    for page in range(1, pages + 1):
        page = str(page)
        try:
            get_links(page)
            print('page', page, 'done')
        except Exception as E:
            traceback.print_exc()
    print(len(links), 'links found')

    final_data = []
    for i in range(len(links)):
        link = links[i]
        data = get_info(link)

        # add all price series as independent
        price_series = data.pop("price_series")
        final_data.append(data)
        for x in price_series:
            temp_data = copy.deepcopy(data)
            temp_data.update(x)
            final_data.append(temp_data)
        print(str(i + 1) + ' of ' + str(len(links)) + ' completed.')
    return final_data


final_data = get_all_product_of_category()
# Change to Dataframe and save as csv file
data = pd.DataFrame(final_data)
data.to_csv("DigiKala  " + str(jdatetime.date.fromgregorian(date=date.today())) + ".csv")
