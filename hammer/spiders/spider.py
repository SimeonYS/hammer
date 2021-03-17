import re
import scrapy
from scrapy.loader import ItemLoader
from ..items import HammerItem
from itemloaders.processors import TakeFirst
import requests
import json
from scrapy import Selector

pattern = r'(\xa0)?'

url = "https://schelhammer.at/home/loadmorenews"

payload = "ajax=1&lastTimestamp={}&excludedArticles%5B%5D={}"
headers = {
    'authority': 'schelhammer.at',
    'pragma': 'no-cache',
    'cache-control': 'no-cache',
    'sec-ch-ua': '"Google Chrome";v="89", "Chromium";v="89", ";Not A Brand";v="99"',
    'accept': '*/*',
    'x-requested-with': 'XMLHttpRequest',
    'sec-ch-ua-mobile': '?0',
    'user-agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36',
    'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'origin': 'https://schelhammer.at',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-mode': 'cors',
    'sec-fetch-dest': 'empty',
    'referer': 'https://schelhammer.at/service/news/',
    'accept-language': 'en-US,en;q=0.9',
    'cookie': 'cookies_allowed_ads=true; cookies_allowed_analytics=true; _ga=GA1.2.1383455647.1614002107; _fbp=fb.1.1614002107557.603727059; PHPSESSID=fd123cf41abcae9c71a2d912602b837a; _gid=GA1.2.955324795.1615964718; _gat_gtag_UA_152076756_1=1'
}


class HammerSpider(scrapy.Spider):
    name = 'hammer'
    start_urls = ['https://schelhammer.at/service/news/']
    pay = 53
    stamp = 1601272800
    def parse(self, response):
        post_links = response.xpath('//h1/a/@href').getall()
        yield from response.follow_all(post_links, self.parse_post)

        data = requests.request("POST", url, headers=headers, data=payload.format(self.stamp, self.pay))
        data = json.loads(data.text)
        container = data['Content']
        links = Selector(text = container).xpath('//h1/a/@href').getall()
        yield from response.follow_all(links,self.parse_post)

        if data['MoreArticles']:
            self.stamp = data['LastTimestamp']
            self.pay = data['ExcludedIDs'][0]
            yield response.follow(response.url, self.parse, dont_filter=True)

    def parse_post(self, response):
        date = response.xpath('//h4[@class="article-category"]/text()').get().strip()
        title = response.xpath('//div[@class="padded-box-regular"]/h1/text()').get()
        content = response.xpath('//div[@class="content-element__content"]//text()[not (ancestor::p[@class="caption center"])] | //div[@class="text-img-element__html-content"]//text()').getall()
        content = [p.strip() for p in content if p.strip()]
        content = re.sub(pattern, "",' '.join(content))

        item = ItemLoader(item=HammerItem(), response=response)
        item.default_output_processor = TakeFirst()

        item.add_value('title', title)
        item.add_value('link', response.url)
        item.add_value('content', content)
        item.add_value('date', date)

        yield item.load_item()
