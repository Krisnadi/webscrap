# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.shortcuts import render
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, WebDriverException
from operator import itemgetter
from decimal import Decimal
from threading import Thread
import requests, time


def scrapRedmart(item, redmart):
    r = requests.get('https://api.redmart.com/v1.6.0/catalog/search?q='+item+'&pageSize=18&sort=1024')
    if 'products' in r.json():
        for i in r.json()['products']:
            item = {}
            item['name'] = i['title'] + ' (' + i['measure']['wt_or_vol'] + ')'
            item['price'] = i['pricing']['price']
            item['url'] = 'https://redmart.com/product/' + i['details']['uri']
            item['website'] = 'Redmart'
            redmart.append(item)

def scrapNtuc(item, ntuc, options):
    driver = webdriver.Chrome(settings.CHROME_PATH, chrome_options=options)
    try:
        driver.get("https://www.fairprice.com.sg/searchterm/"+item)
        # load_more = 1
        # for i in range(0, load_more):
        #     driver.find_element_by_link_text('LOAD MORE').click()
        #     time.sleep(1)
        elements = driver.find_elements_by_css_selector("div.pdt_list_wrap")
        for element in elements:
            try:
                item = {}
                item['name'] = element.find_element_by_tag_name("img").get_attribute("title") + ' (' + element.find_element_by_css_selector("span.pdt_Tweight").text + ')'
                item['price'] = Decimal(element.find_element_by_css_selector("span.pdt_C_price").text[1:])
                try:
                    item['url'] = element.find_element_by_css_selector("a.pdt_title").get_attribute("href")
                except NoSuchElementException:
                    item['url'] = None
                item['website'] = 'Ntuc'
                ntuc.append(item)
            except NoSuchElementException:
                continue
            except StaleElementReferenceException:
                continue
    except WebDriverException:
        pass
    driver.quit()

def scrapHonestbee(item, honestbee):
    headers = {'Accept': 'application/vnd.honestbee+json;version=2'}
    r = requests.get('https://www.honestbee.sg/api/api/stores/9345?q='+item+'&sort=relevance&page=1', headers=headers)
    if 'products' in r.json():
        for i in r.json()['products']:
            item = {}
            item['name'] = (i['productBrand'] + " " if i['productBrand'] else "") + i['title'] + ' (' + i['size'] + ')'
            item['price'] = Decimal(i['price'])
            item['url'] = 'https://www.honestbee.sg/en/groceries/stores/fresh-by-honestbee/products/' + str(i['id'])
            item['website'] = 'Honestbee'
            honestbee.append(item)

def scrapAmazonPrime(item, amazonprime, options):
    driver = webdriver.Chrome(settings.CHROME_PATH, chrome_options=options)
    try:
        driver.get("https://www.amazon.com/s/ref=nb_sb_noss?url=search-alias%3Daps&field-keywords="+item)
        # load_more = 1
        # for i in range(0, load_more):
        elements = driver.find_elements_by_css_selector("div.s-item-container")
        for element in elements:
            try:
                item = {}
                try:
                    item['price'] = Decimal(element.find_element_by_css_selector("span.sx-price-whole").text.replace(",", "") + '.' + element.find_element_by_css_selector("sup.sx-price-fractional").text)
                except NoSuchElementException:
                    continue
                try:
                    item['name'] = element.find_element_by_css_selector("h2.a-size-base.s-inline.s-access-title.a-text-normal").get_attribute("data-attribute")
                except NoSuchElementException:
                    item['name'] = element.find_element_by_css_selector("h2.a-size-medium.s-inline.s-access-title.a-text-normal").get_attribute("data-attribute")
                try:
                    item['url'] = element.find_elements_by_css_selector("a.a-link-normal.a-text-normal")[0].get_attribute("href")
                except IndexError:
                    item['url'] = None
                item['website'] = 'Amazon Prime'
                amazonprime.append(item)
                # if i < load_more - 1:
                #     driver.find_element_by_link_text('Next Page').click()
                #     time.sleep(2)
            except StaleElementReferenceException:
                continue
    except WebDriverException:
        pass
    driver.quit()

def index(request):
    current_name, items = '', []
    if request.method == 'POST':
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')

        current_name, redmart, ntuc, honestbee, amazonprime = request.POST['item'], [], [], [], []

        # create threads
        redmart_thread = Thread(target=scrapRedmart, args=(request.POST['item'], redmart,))
        ntuc_thread = Thread(target=scrapNtuc, args=(request.POST['item'], ntuc, options,))
        honestbee_thread = Thread(target=scrapHonestbee, args=(request.POST['item'], honestbee,))
        amazonprime_thread = Thread(target=scrapAmazonPrime, args=(request.POST['item'], amazonprime, options,))

        # run all threads
        redmart_thread.start()
        ntuc_thread.start()
        honestbee_thread.start()
        amazonprime_thread.start()

        # wait until all threads finished
        redmart_thread.join()
        ntuc_thread.join()
        honestbee_thread.join()
        amazonprime_thread.join()

        items = redmart + ntuc + honestbee + amazonprime
        items = sorted(items, key=itemgetter('price'))
    return render(request, 'scrap/index.html', {'current_name':current_name, 'items':items})