# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render
from scrapy.crawler import CrawlerRunner
from scrapy import signals
from crochet import setup
from operator import itemgetter
from decimal import Decimal
from threading import Thread
import requests, scrapy
setup()


class NtucSpider(scrapy.Spider):
    name = "ntuc"

    def __init__(self, item=None, ntuc=None, flag=None, *args, **kwargs):
        super(NtucSpider, self).__init__(*args, **kwargs)
        self.start_urls = [
            'https://www.fairprice.com.sg/searchterm/' + item,
        ]
        self.ntuc = ntuc
        self.flag = flag

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(NtucSpider, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        return spider

    def spider_closed(self, spider):
        self.flag.append('ntuc')

    def parse(self, response):
        divs = response.css('div.pdt_list_wrap')
        for div in divs:
            item = {}
            item['name'] = div.css('img::attr(title)').extract_first() + ' (' + div.css('span.pdt_Tweight::text').extract_first() + ')'
            item['price'] = Decimal(div.css('span.pdt_C_price::text').extract_first().strip()[1:])
            item['url'] = div.css('a.pdt_title::attr(href)').extract_first()
            item['website'] = 'Ntuc'
            self.ntuc.append(item)

class AmazonPrimeSpider(scrapy.Spider):
    name = "amazonprime"

    def __init__(self, item=None, amazonprime=None, flag=None, *args, **kwargs):
        super(AmazonPrimeSpider, self).__init__(*args, **kwargs)
        self.start_urls = [
            'https://www.amazon.com/s/ref=nb_sb_noss?url=search-alias%3Daps&field-keywords=' + item,
        ]
        self.amazonprime = amazonprime
        self.flag = flag
        # self.page = 1
        # self.page_limit = 2

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(AmazonPrimeSpider, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        return spider

    def spider_closed(self, spider):
        self.flag.append('amazonprime')

    def parse(self, response):
        divs = response.css('div.s-item-container')
        for div in divs:
            item = {}
            if div.css('span.sx-price-whole'):
                item['price'] = Decimal(div.css('span.sx-price-whole::text').extract_first().replace(',', '') + '.' + div.css('sup.sx-price-fractional::text').extract_first())
            else:
                continue
            if div.css('h2.a-size-base.s-inline.s-access-title.a-text-normal'):
                item['name'] = div.css('h2.a-size-base.s-inline.s-access-title.a-text-normal::attr(data-attribute)').extract_first()
            else:
                item['name'] = div.css('h2.a-size-medium.s-inline.s-access-title.a-text-normal::attr(data-attribute)').extract_first()
            item['url'] = div.css('a.a-link-normal.a-text-normal::attr(href)').extract_first()
            item['website'] = 'Amazon Prime'
            self.amazonprime.append(item)
        # next_page = response.css('a#pagnNextLink::attr("href")').extract_first()
        # if next_page is not None and self.page < self.page_limit:
        #     self.page += 1
        #     yield response.follow(next_page, self.parse)

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

def scrapNtucAmazon(item, ntuc, amazonprime, flag):
    runner = CrawlerRunner()
    runner.crawl(NtucSpider, item=item, ntuc=ntuc, flag=flag)
    runner.crawl(AmazonPrimeSpider, item=item, amazonprime=amazonprime, flag=flag)
    runner.join()
    while len(flag) != 2: # ntuc and amazon crawl have not finished
        pass

def index(request):
    item, items = '', []
    if request.method == 'POST':
        item, redmart, ntuc, honestbee, amazonprime, flag = request.POST['item'], [], [], [], [], []

        # create threads
        redmart_thread = Thread(target=scrapRedmart, args=(item, redmart,))
        honestbee_thread = Thread(target=scrapHonestbee, args=(item, honestbee,))
        scrapy_thread = Thread(target=scrapNtucAmazon, args=(item, ntuc, amazonprime, flag))

        # run all threads
        redmart_thread.start()
        honestbee_thread.start()
        scrapy_thread.start()

        # wait until all threads finished
        redmart_thread.join()
        honestbee_thread.join()
        scrapy_thread.join()

        items = redmart + ntuc + honestbee + amazonprime
        items = sorted(items, key=itemgetter('price'))
    return render(request, 'scrap/index.html', {'item':item, 'items':items})