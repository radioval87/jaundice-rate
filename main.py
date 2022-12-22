import asyncio

import aiofiles
import aiohttp
import pymorphy2

from adapters.inosmi_ru import sanitize
from text_tools import calculate_jaundice_rate, split_by_words

morph = pymorphy2.MorphAnalyzer()


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
    
    await asyncio.gather(
        get_negative_words(),
        get_positive_words()
    )
    return charged_words


async def fetch(session, url):
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()


async def main():
    async with aiohttp.ClientSession() as session:
        charged_words = await get_charged_words()
        html = await fetch(session, 'https://inosmi.ru/economic/20190629/245384784.html')
        clean_text = sanitize(html)
        morphed_text = split_by_words(morph, clean_text)
        rate = calculate_jaundice_rate(morphed_text, charged_words)
        print(f'Рейтинг: {rate}\nСлов в статье: {len(morphed_text)}')

asyncio.run(main())
