from aiohttp import web
from aiohttp.web_request import Request

from main import main as process_articles


async def get_articles_stats(request: Request):
    urls = []
    if 'urls' in request.rel_url.query and request.rel_url.query['urls']:
        urls = request.rel_url.query['urls'].split(',')
        if len(urls) > 10:
            return web.json_response(
                data={
                    "error": "too many urls in request, should be 10 or less"
                }, status=400
            )
        for url in urls:
            url = url.strip()

    results = await process_articles(urls)
    response = {
        'results': results
    }
    return web.json_response(response)


def main():
    app = web.Application()
    app.add_routes(
        [
            web.get('', get_articles_stats),
        ]
    )
    web.run_app(app, host='127.0.0.1', port=8081)


if __name__ == '__main__':
    main()
