import asyncio
import logging
import time
from contextlib import contextmanager
from enum import Enum

import aiofiles
import aiohttp
import async_timeout
import pymorphy2
import pytest
from anyio import create_task_group

from adapters.exceptions import ArticleNotFound
from adapters.inosmi_ru import sanitize
from text_tools import calculate_jaundice_rate, split_by_words

charged_words = []

TEST_ARTICLES = (
    'https://inosmi.ru/20221222/zemlya-259086442.html',
    'https://inosmi.ru/20221222/yandeks-259084346.html',
    'https://inosmi.ru/20221221/rasizm-259040011.html',
    'https://inosmi.ru/20221221/kanada-259046280.html',
    'https://inosmi.ru/20221221/oligarkhi-259041447.ht',
    'https://anyio.readthedocs.io/en/latest/tasks.html'
)


async def read_words_from_file(path):
    async with aiofiles.open(path, mode='r') as f:
        words = await f.read()
        for word in words.split('\n'):
            charged_words.append(word)


async def get_charged_words():
    await read_words_from_file('./negative_words.txt')
    await read_words_from_file('./positive_words.txt')


async def fetch(session, url):
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()


class ProcessingStatus(str, Enum):
    OK = 'OK'
    FETCH_ERROR = 'FETCH_ERROR'
    PARSING_ERROR = 'PARSING_ERROR'
    TIMEOUT = 'TIMEOUT'


@contextmanager
def timeit():
    start = time.monotonic()
    try:
        yield
    finally:
        logging.info(f'Анализ закончен за {time.monotonic() - start} сек')


async def get_article_text(session, url, fetch_timeout, status):
    clean_text = None
    try:
        async with async_timeout.timeout(fetch_timeout):
            html = await fetch(session, url)
    except aiohttp.ClientResponseError:
        status = ProcessingStatus.FETCH_ERROR
    except asyncio.TimeoutError:
        status = ProcessingStatus.TIMEOUT

    if status == ProcessingStatus.OK:
        try:
            clean_text = sanitize(html)
        except ArticleNotFound:
            status = ProcessingStatus.PARSING_ERROR
    return clean_text, status


async def process_article(session, morph, charged_words, url, results,
                          fetch_timeout=2, article_text=None):

    status = ProcessingStatus.OK
    rate = None
    words_count = None

    if not article_text:
        article_text, status = await get_article_text(
            session=session,
            url=url,
            fetch_timeout=fetch_timeout,
            status=status
        )

    if status == ProcessingStatus.OK:
        try:
            async with async_timeout.timeout(3):
                with timeit():
                    morphed_text = await split_by_words(morph, article_text)
                rate = calculate_jaundice_rate(morphed_text, charged_words)
                words_count = len(morphed_text)
        except asyncio.TimeoutError:
            status = ProcessingStatus.TIMEOUT

    results.append({
        'status': status,
        'url': url,
        'score': rate,
        'words_count': words_count
    })


async def process_articles(urls, morph):
    results = []
    async with aiohttp.ClientSession() as session:
        async with create_task_group() as tg:
            for url in urls:
                tg.start_soon(
                    process_article,
                    session,
                    morph,
                    charged_words,
                    url,
                    results
                )
    return results


async def main(morph, urls=TEST_ARTICLES):
    logging.basicConfig(
        format=(
            '%(filename)s[LINE:%(lineno)d]# %(levelname)-8s [%(asctime)s] '
            '%(message)s'
        ),
        level=logging.DEBUG
    )
    await get_charged_words()
    await process_articles(urls, morph)


@pytest.mark.asyncio
async def test_process_article():
    morph = pymorphy2.MorphAnalyzer()
    charged_words = ('аутсайдер', 'побег')
    correct_url = 'https://inosmi.ru/20221221/oligarkhi-259041447.html'
    incorrect_url = 'https://inosmi.ru/20221221/oligarkhi-259041447.ht'
    incompatible_url = 'https://anyio.readthedocs.io/en/latest/tasks.html'
    with open('./big_text.txt', 'r') as f:
        big_text = f.read()

    results = []
    async with aiohttp.ClientSession() as session:
        await process_article(
            session=session,
            morph=morph,
            charged_words=charged_words,
            url=correct_url,
            results=results
        )
    assert results[0]['status'] == 'OK'

    results = []
    async with aiohttp.ClientSession() as session:
        await process_article(
            session=session,
            morph=morph,
            charged_words=charged_words,
            url=incorrect_url,
            results=results
        )
    assert results[0]['status'] == 'FETCH_ERROR'

    results = []
    async with aiohttp.ClientSession() as session:
        await process_article(
            session=session,
            morph=morph,
            charged_words=charged_words,
            url=correct_url,
            results=results,
            fetch_timeout=0.01
        )
    assert results[0]['status'] == 'TIMEOUT'

    results = []
    async with aiohttp.ClientSession() as session:
        await process_article(
            session=session,
            morph=morph,
            charged_words=charged_words,
            url=correct_url,
            results=results,
            article_text=big_text
        )
    assert results[0]['status'] == 'TIMEOUT'

    results = []
    async with aiohttp.ClientSession() as session:
        await process_article(
            session=session,
            morph=morph,
            charged_words=charged_words,
            url=incompatible_url,
            results=results
        )
    assert results[0]['status'] == 'PARSING_ERROR'


if __name__ == '__main__':
    morph = pymorphy2.MorphAnalyzer()
    asyncio.run(main(morph))
