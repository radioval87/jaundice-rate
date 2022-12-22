import asyncio

import aiofiles
import aiohttp
import pymorphy2
from anyio import create_task_group

from adapters.inosmi_ru import sanitize
from text_tools import calculate_jaundice_rate, split_by_words

TEST_ARTICLES = (
    'https://inosmi.ru/20221222/zemlya-259086442.html',
    'https://inosmi.ru/20221222/yandeks-259084346.html',
    'https://inosmi.ru/20221221/rasizm-259040011.html',
    'https://inosmi.ru/20221221/kanada-259046280.html',
    'https://inosmi.ru/20221221/oligarkhi-259041447.html'
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


async def process_article(session, morph, charged_words, url):
    html = await fetch(session, url)
    clean_text = sanitize(html)
    morphed_text = split_by_words(morph, clean_text)
    rate = calculate_jaundice_rate(morphed_text, charged_words)
    print('URL:', url)
    print('Рейтинг:', rate)
    print('Слов в статье:', len(morphed_text))
    print('')


async def main():
    morph = pymorphy2.MorphAnalyzer()
    charged_words = await get_charged_words()
    async with aiohttp.ClientSession() as session:
        async with create_task_group() as tg:
            for url in TEST_ARTICLES:
               tg.start_soon(process_article, session, morph, charged_words, url) 
        

asyncio.run(main())
