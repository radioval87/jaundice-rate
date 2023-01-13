import asyncio
import logging
import signal
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

morph = pymorphy2.MorphAnalyzer()


class sync_timeout:
    def __init__(self, seconds=1, error_message='Timeout'):
        self.seconds = seconds
        self.error_message = error_message
    def handle_timeout(self, signum, frame):
        raise TimeoutError(self.error_message)
    def __enter__(self):
        signal.signal(signal.SIGALRM, self.handle_timeout)
        signal.alarm(self.seconds)
    def __exit__(self, type, value, traceback):
        signal.alarm(0)


TEST_ARTICLES = (
    'https://inosmi.ru/20221222/zemlya-259086442.html',
    'https://inosmi.ru/20221222/yandeks-259084346.html',
    'https://inosmi.ru/20221221/rasizm-259040011.html',
    'https://inosmi.ru/20221221/kanada-259046280.html',
    'https://inosmi.ru/20221221/oligarkhi-259041447.ht',
    'https://anyio.readthedocs.io/en/latest/tasks.html'
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


async def process_article(session, morph, charged_words, url, results,
    fetch_timeout=2, big_text_test=False):

    status = ProcessingStatus.OK
    rate = None
    words_count = None

    if big_text_test:
        with open('./big_text.txt', 'r') as f:
            clean_text = f.read()
    else:
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

    if status == ProcessingStatus.OK:
        try:
            with sync_timeout(seconds=3):
                with timeit(): 
                    morphed_text = split_by_words(morph, clean_text)
                rate = calculate_jaundice_rate(morphed_text, charged_words)
                words_count = len(morphed_text)
        except TimeoutError:
            status = ProcessingStatus.TIMEOUT

    results.append({
        'status': status,
        'url': url,
        'score': rate,
        'words_count': words_count
    })


async def main(urls=TEST_ARTICLES):
    logging.basicConfig(
        format=(
            '%(filename)s[LINE:%(lineno)d]# %(levelname)-8s [%(asctime)s] '
            '%(message)s'
        ),
        level=logging.DEBUG
    )

    charged_words = await get_charged_words()
    results = []
    async with aiohttp.ClientSession() as session:
        async with create_task_group() as tg:
            for url in urls:
                tg.start_soon(
                    process_article,
                    session, morph, charged_words, url, results
                )
    return results
    

@pytest.mark.asyncio
async def test_process_article():
    charged_words = ('аутсайдер', 'побег')
    correct_url = 'https://inosmi.ru/20221221/oligarkhi-259041447.html'
    incorrect_url = 'https://inosmi.ru/20221221/oligarkhi-259041447.ht'
    incompatible_url = 'https://anyio.readthedocs.io/en/latest/tasks.html'

    results = []
    async with aiohttp.ClientSession() as session:
        await process_article(
            session,
            morph,
            charged_words,
            correct_url,
            results
        )
    assert results[0]['status'] == 'OK'

    results = []
    async with aiohttp.ClientSession() as session:
        await process_article(
            session,
            morph,
            charged_words,
            incorrect_url,
            results
        )
    assert results[0]['status'] == 'FETCH_ERROR'

    results = []
    async with aiohttp.ClientSession() as session:
        await process_article(
            session,
            morph,
            charged_words,
            correct_url,
            results,
            fetch_timeout=0.01
        )
    assert results[0]['status'] == 'TIMEOUT'

    results = []
    async with aiohttp.ClientSession() as session:
        await process_article(
            session,
            morph,
            charged_words,
            correct_url,
            results,
            big_text_test=True
        )
    assert results[0]['status'] == 'TIMEOUT'

    results = []
    async with aiohttp.ClientSession() as session:
        await process_article(
            session,
            morph,
            charged_words,
            incompatible_url,
            results
        )
    assert results[0]['status'] == 'PARSING_ERROR'


asyncio.run(main())
