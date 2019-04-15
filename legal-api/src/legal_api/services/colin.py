import aiohttp
import asyncio
import async_timeout
import concurrent

from flask import current_app


class Colin():

    @staticmethod
    async def get_business(identifier):

        url = current_app.config.get('COLIN_URL')

        rv = Colin.fetch("http://localhost:8080/rest/colin-api/0.9/api/v1/businesses/CP7654321")

        print('colin url', url)

        return rv

    @staticmethod
    async def fetch(url):
        timeout = aiohttp.ClientTimeout(total=1, connect=None,
                                        sock_connect=None, sock_read=None)
        try:
            async with aiohttp.ClientSession() as session, async_timeout.timeout(60):

                async with session.get(url, timeout=timeout) as response:
                    test = await response.text()
                    return [test, response.status]
        except aiohttp.client_exceptions.ClientConnectorError as cce:
            print(cce)
            return 404
        except concurrent.futures._base.TimeoutError as te:
            print(te)
            return 404
        except Exception as err:
            print('the exception', type(err))
            return 500
