#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Tap评论爬取
@author: github.com/zhengxiaoyao0716
"""

from collections import namedtuple
import requests
import logging
from bs4 import BeautifulSoup
import re
import json
import os

config = namedtuple('Config', (
    'appId',
    'maxPage'
))(
    84458,
    1000,
)


def makeUrl(appid: str, page: int, order='default'):
    return f'https://www.taptap.com/app/{appid}/review?page={page}&order={order}'


def fetch(url: str):
    """抓取页面"""
    print('正在抓取 `%s`:' % url)
    resp = requests.get(url)  # 请求页面
    try:
        data = list(parse(resp))
    except Exception as e:  # pylint: disable=W0703
        logging.error('解析失败，请检查目标页面格式并修正解析器')
        logging.exception(e)
        return []
    num = len(data)
    if num:
        print(f'成功，抓取到{num}条数据\n')
    else:
        print(f'无更多数据')
    return data


def parse(resp: requests.Response):
    resp.encoding = 'utf-8'  # 设置响应编码
    soup = BeautifulSoup(resp.text, 'lxml')  # 读取页面内容
    reviews = (
        (li.get('id'), li.select_one('div.review-item-text'), li)
        for li in soup.select('ul#reviewsList>li')
    )  # [(id, review), ...]

    return (
        {
            'id': int(id[7:]) if id else 0,
            'user': pick(review, 'div.item-text-header>span.taptap-user>a.taptap-user-name'),
            'createAt': pick(review, 'div.item-text-header>a.text-header-time span[data-dynamic-time]'),
            'score': pick_score(review),
            'content': pick(review, 'div.item-text-body'),
            'device': pick(review, 'div.item-text-footer>span.text-footer-device', optional=True),
            'vote': {
                'funny': int(pick(review, 'div.item-text-footer button[data-value="funny"]>span[data-taptap-ajax-vote="count"]') or '0'),
                'up': int(pick(review, 'div.item-text-footer button[data-value="up"]>span[data-taptap-ajax-vote="count"]') or '0'),
                'down': int(pick(review, 'div.item-text-footer button[data-value="down"]>span[data-taptap-ajax-vote="count"]') or '0'),
            },
            'comments': list(pick_comments(review)),
        } if review else pick_invalid_li(li)
        for (id, review, li) in reviews
    )


def pick(soup: BeautifulSoup, selector: str, optional=False):
    """摘取指定文本"""
    field = soup.select_one(selector)
    if not field:
        if optional:
            return None
        logging.error(f'解析失败，无法提取指定文本，selector: {selector}, soup: {soup}')
    return field.text.strip() if field else ''


def pick_score(soup: BeautifulSoup, reg_exp=re.compile(r'width:\s?(\d+)px')):
    """提取评分，居然用style.width来存放，真™奇葩"""
    style = soup.select_one('div.item-text-score>i.colored')['style']
    return float(reg_exp.match(style).group(1)) / 70


def pick_comments(soup: BeautifulSoup):
    """摘取评论回复"""
    # TODO 只摘取了当前页上的回复，然而事实上回复也可能有分页，考虑是否需要追踪所有回复
    comments = (
        (li.get('id'), li.select_one('div.comment-item-text'), li)
        for li in soup.select('div.taptap-comments>ul>li')
    )  # [(id, comment), ...]

    return (
        {
            'id': int(id[8:]) if id else 0,
            'user': pick(comment, 'div.item-text-header>span.taptap-user>a.taptap-user-name'),
            'time': pick(comment, 'div.item-text-footer span[data-dynamic-time]'),
            'content': pick(comment, 'div.item-text-body'),
            'vote': {
                'up': int(pick(comment, 'div.item-text-footer button[data-value="up"]>span[data-taptap-ajax-vote="count"]') or '0'),
                'down': int(pick(comment, 'div.item-text-footer button[data-value="down"]>span[data-taptap-ajax-vote="count"]') or '0'),
            },
        } if comment else {'id': int(id[8:]) if id else 0}
        for (id, comment, li) in comments
    )


def pick_invalid_li(soup: BeautifulSoup):
    """li格式无效时提取替代用的信息"""
    collapsed = soup.select_one('button.review-item-collapsed')
    if collapsed:
        id = collapsed['data-taptap-dispute']
        # TODO 该评论被折叠，考虑是否有必要追踪折叠前的内容
        return {'id': int(id[8:]) if id else 0, 'error': collapsed.text.strip()}

    logging.error(f'解析失败，未知的li格式，soup: {soup}')
    return {'id': 0, 'error': 'invalid format'}


def main():
    for page in range(1, 1 + config.maxPage):
        url = makeUrl(config.appId, page)
        # TODO 当前为逐条请求抓取，速度较慢，但比较安全，考虑改为批量异步请求的话速度提升较大，但需要防封杀
        data = fetch(url)
        if not len(data):
            break
        os.makedirs('./out', exist_ok=True)
        with open(f'out/page-{page}.json', mode='w', encoding='UTF-8') as file:
            json.dump(data, file, indent=4, ensure_ascii=False)

    print(f'全部页面抓取完成，已输出到"./out"目录')


if __name__ == '__main__':
    main()
