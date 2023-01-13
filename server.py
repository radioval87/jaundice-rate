from aiohttp import web
from aiohttp.web_request import Request

from main import main as process_articles


async def get_articles_stats(request: Request):
    urls = []
    if request.rel_url.query['urls']:
        for url in request.rel_url.query['urls'].split(','):
            urls.append(url.strip())
    
    if len(urls) > 10:
        return web.json_response(data={
            "error": "too many urls in request, should be 10 or less"
            }, status=400
        )

    results = await process_articles(urls)
    response = {
        'results': results
    }
    return web.json_response(response)

app = web.Application()
app.add_routes(
    [
        web.get('', get_articles_stats),
    ]
)

if __name__ == '__main__':
    web.run_app(app, host='127.0.0.1', port=8081)
