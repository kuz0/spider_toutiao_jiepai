# -*- coding: utf-8 -*-

import os
import re
import json
import requests
from pyquery import PyQuery as pq
from pymongo import MongoClient
from hashlib import md5
from multiprocessing import Pool
from config import *


client = MongoClient(MONGO_URI, connect=False)
db = client[MONGO_DB]


def get_page_index(offset, keyword):
    payload = {
        'offset': offset,
        'format': 'json',
        'keyword': keyword,
        'autoload': 'true',
        'count': '20',
        'cur_tab': '3',
        'from': 'gallery',
    }
    url = 'https://www.toutiao.com/search_content/'
    try:
        response = requests.get(url, params=payload)
        if response.status_code == requests.codes.ok:
            return response.text
        return None
    except Exception as e:
        print(e)


def parse_page_index(response):
    try:
        data = json.loads(response)
        if data and 'data' in data.keys():
            for item in data.get('data'):
                yield item.get('article_url')
    except Exception as e:
        print(e)


def get_page_detail(url):
    try:
        response = requests.get(url)
        if response.status_code == requests.codes.ok:
            return response.text
        return None
    except Exception as e:
        print(e)


def parse_page_detail(html, url):
    doc = pq(html)
    title = doc('title').text()
    images_pattern = re.compile('gallery: JSON.parse\("(.*?)"\)', re.S)
    result = re.search(images_pattern, html)
    if result:
        result = result.group(1).replace(r'\"', r'"')
        result = result.replace(r'\\', r'')
        try:
            data = json.loads(result)
            if data and 'sub_images' in data.keys():
                sub_images = data.get('sub_images')
                images = [item.get('url') for item in sub_images]
                for image in images:
                    download_image(image)
                return {
                    'title': title,
                    'url': url,
                    'images': images,
                }
        except Exception as e:
            print(e)


def save_to_mongodb(result):
    try:
        if db[MONGO_TABLE].insert_one(result):
            print('Successfully Saved!', result['title'])
    except Exception as e:
        print(e)


def download_image(url):
    print('Downloading', url)
    try:
        response = requests.get(url)
        if response.status_code == requests.codes.ok:
            save_image(response.content)
        return None
    except Exception as e:
        print(e)


def save_image(content):
    file_path = '{0}/{1}.jpg'.format(os.getcwd(),
                                     md5(content).hexdigest())
    if not os.path.exists(file_path):
        print(file_path)
        with open(file_path, 'wb') as f:
            f.write(content)
            f.close()


def main(offset):
    text = get_page_index(offset, KEYWORD)
    urls = parse_page_index(text)
    for url in urls:
        html = get_page_detail(url)
        result = parse_page_detail(html, url)
        if result:
            save_to_mongodb(result)


if __name__ == '__main__':
    pool = Pool()
    groups = [x * 20 for x in range(GROUP_START, GROUP_END + 1)]
    pool.map(main, groups)
    pool.close()
    pool.join()

