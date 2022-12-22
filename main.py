import asyncio
from enum import Enum

import aiofiles
import aiohttp
import pymorphy2
from anyio import create_task_group

from adapters.exceptions import ArticleNotFound
from adapters.inosmi_ru import sanitize
from text_tools import calculate_jaundice_rate, split_by_words

TEST_ARTICLES = (
    'https://inosmi.ru/20221222/zemlya-259086442.html',
    'https://inosmi.ru/20221222/yandeks-259084346.html',
    'https://inosmi.ru/20221221/rasizm-259040011.html',
    'https://inosmi.ru/20221221/kanada-259046280.html',
    'https://inosmi.ru/20221221/oligarkhi-259041447.ht'
)


async def get_charged_words():
    charged_words = []

    async def read_words_from_file(path):
        nonlocal charged_words
        async with aiofiles.open(path, mode='r') as f:
            msgs = await f.read()
            for msg in msgs.split('\n'):
                charged_words.append(msg)

    async def get_negative_words():
        await read_words_from_file('./negative_words.txt')

    async def get_positive_words():
        await read_words_from_file('./positive_words.txt')
    
    async with create_task_group() as tg:
        tg.start_soon(get_negative_words)
        tg.start_soon(get_positive_words)
    return charged_words


async def fetch(session, url):
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()


class ProcessingStatus(Enum):
    OK = 'OK'
    FETCH_ERROR = 'FETCH_ERROR'
    PARSING_ERROR = 'PARSING_ERROR'


async def process_article(session, morph, charged_words, url, results):
    status = ProcessingStatus.OK
    rate = None
    words_count = None

    try:
        html = await fetch(session, url)
    except aiohttp.ClientResponseError:
        status = ProcessingStatus.FETCH_ERROR
        
    if status == ProcessingStatus.OK:
        try:
            clean_text = sanitize(html)
        except ArticleNotFound:
            status = ProcessingStatus.PARSING_ERROR

    if status == ProcessingStatus.OK:
        morphed_text = split_by_words(morph, clean_text)
        rate = calculate_jaundice_rate(morphed_text, charged_words)
        words_count = len(morphed_text)

    results.append({
        'url': url,
        'status': status,
        'rate': rate,
        'words_count': words_count
    })


async def main():
    morph = pymorphy2.MorphAnalyzer()
    charged_words = await get_charged_words()
    results = []
    async with aiohttp.ClientSession() as session:
        async with create_task_group() as tg:
            for url in TEST_ARTICLES:
                tg.start_soon(
                   process_article, session, morph, charged_words, url, results
                )
    for result in results:
        print('URL:', result['url'])
        print('Статус:', result['status'])
        print('Рейтинг:', result['rate'])
        print('Слов в статье:', result['words_count'])
        print('')


asyncio.run(main())
