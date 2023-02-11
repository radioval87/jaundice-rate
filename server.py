from functools import partial

import pymorphy2
from aiohttp import web
from aiohttp.web_request import Request

from articles_processor import process_articles


async def get_articles_stats(request: Request, morph):
    urls = []
    query_parameters = request.rel_url.query
    if 'urls' in query_parameters and query_parameters['urls']:
        urls = query_parameters['urls'].replace(' ', '').split(',')
        if len(urls) > 10:
            return web.json_response(
                data={
                    "error": "too many urls in request, should be 10 or less"
                }, status=400
            )

    results = await process_articles(urls, morph)
    response = {
        'results': results
    }
    return web.json_response(response)


def main(morph):
    app = web.Application()
    app.add_routes(
        [
            web.get('', partial(get_articles_stats, morph=morph)),
        ]
    )
    web.run_app(app, host='127.0.0.1', port=8081)


if __name__ == '__main__':
    morph = pymorphy2.MorphAnalyzer()
    main(morph)
