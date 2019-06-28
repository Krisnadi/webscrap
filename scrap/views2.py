# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.shortcuts import render
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from operator import itemgetter
from decimal import Decimal
import requests, time


options = webdriver.ChromeOptions()
options.add_argument('--headless')

def scrapRedmart(item):
    data = []
    r = requests.get('https://api.redmart.com/v1.6.0/catalog/search?q='+item+'&pageSize=18&sort=1024')
    if 'products' in r.json():
        for i in r.json()['products']:
            item = {}
            item['name'] = i['title']
            item['price'] = i['pricing']['price']
            item['website'] = 'Redmart'
            data.append(item)
    return data

def scrapNtuc(driver, item):
    data = []
    driver.get("https://www.fairprice.com.sg/searchterm/"+item)
    # load_more = 1
    # for i in range(0, load_more):
    #     driver.find_element_by_link_text('LOAD MORE').click()
    #     time.sleep(1)
    elements = driver.find_elements_by_css_selector("div.pdt_list_wrap")
    for element in elements:
        try:
            item = {}
            item['name'] = element.find_element_by_tag_name("img").get_attribute("title")
            item['price'] = Decimal(element.find_element_by_css_selector("span.pdt_C_price").text[1:])
            item['website'] = 'Ntuc'
            data.append(item)
        except NoSuchElementException:
            continue
        except StaleElementReferenceException:
            continue
    return data

def scrapHonestbee(driver, item):
    data = []
    driver.get("https://www.honestbee.sg/en/groceries/stores/fresh-by-honestbee/search?q="+item)
    # scroll = 1
    # time.sleep(2)
    # for i in range(0, scroll):
    #         driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    #         time.sleep(2)
    elements = driver.find_elements_by_css_selector("div._SvKXteR-KEhPC9z6PkxL")
    for element in elements:
        try:
            item = {}
            item['name'] = element.find_element_by_css_selector("div._2UCShViKs8ydkfj-XuvUhM").text
            item['price'] = Decimal(element.find_element_by_css_selector("div._23g1UkP8VGFqvGuLjUsc-H").text[1:])
            item['website'] = 'Honestbee'
            data.append(item)
        except NoSuchElementException:
            continue
        except StaleElementReferenceException:
            continue
    return data

def scrapAmazonPrime(driver, item):
    data = []
    driver.get("https://www.amazon.com/s/ref=nb_sb_noss?url=search-alias%3Daps&field-keywords="+item)
    # load_more = 1
    # for i in range(0, load_more):
    elements = driver.find_elements_by_css_selector("div.s-item-container")
    for element in elements:
        item = {}
        try:
            item['name'] = element.find_element_by_css_selector("h2.a-size-base.s-inline.s-access-title.a-text-normal").get_attribute("data-attribute")
            item['price'] = Decimal(element.find_element_by_css_selector("span.sx-price-whole").text.replace(",", "") + '.' + element.find_element_by_css_selector("sup.sx-price-fractional").text)
        except NoSuchElementException:
            try:
                item['name'] = element.find_element_by_css_selector("h2.a-size-medium.s-inline.s-access-title.a-text-normal").get_attribute("data-attribute")
                item['price'] = Decimal(element.find_element_by_css_selector("span.sx-price-whole").text.replace(",", "") + '.' + element.find_element_by_css_selector("sup.sx-price-fractional").text)
            except NoSuchElementException:
                continue
            except StaleElementReferenceException:
                continue
        except StaleElementReferenceException:
            continue
        item['website'] = 'Amazon Prime'
        data.append(item)
        # if i < load_more - 1:
        #     driver.find_element_by_link_text('Next Page').click()
        #     time.sleep(2)
    return data

def index(request):
    current_name = ''
    items = []
    if request.method == 'POST':
        driver = webdriver.Chrome(settings.CHROME_PATH, chrome_options=options)
        current_name = request.POST['item']
        redmart = scrapRedmart(request.POST['item'])
        ntuc = scrapNtuc(driver, request.POST['item'])
        honestbee = scrapHonestbee(driver, request.POST['item'])
        amazonprime = scrapAmazonPrime(driver, request.POST['item'])
        items = redmart + ntuc + honestbee + amazonprime
        items = sorted(items, key=itemgetter('price'))
        driver.quit()
    return render(request, 'scrap/index.html', {'current_name':current_name, 'items':items})