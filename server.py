from aiohttp import web
from aiohttp.web_request import Request

'''
http://127.0.0.1?urls=https://ya.ru,https://google.com

{
  "urls": [
    "https://ya.ru",
    "https://google.com"
  ]
}
'''

async def handle(request: Request):
    urls = []
    if request.rel_url.query['urls']:
        for url in request.rel_url.query['urls'].split(','):
            urls.append(url.strip())
    response = {
        "urls": urls
    }
    return web.json_response(response)

app = web.Application()
app.add_routes(
    [web.get('', handle),
    ]
)

if __name__ == '__main__':
    web.run_app(app, host='127.0.0.1', port=8081)
