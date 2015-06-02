# +----------------------------------------------------------------------+
# | Copyright (c) 2015 Winston Wolf                                      |
# +----------------------------------------------------------------------+
# | This source file is bound by United States copyright law.            |
# +----------------------------------------------------------------------+
# | Author: Winston Wolf <winston.the.cleaner@gmail.com>                 |
# +----------------------------------------------------------------------+

import json
from urllib3 import HTTPSConnectionPool
from settings import API_KEY, API_REGIONS
from threading import Thread
from time import sleep
import logging

logger = logging.getLogger('freelo')

connection_pool_dict = {
    region: HTTPSConnectionPool('{region}.api.pvp.net'.format(region=region), maxsize=300, headers={}, timeout=10)
    for region in API_REGIONS + ['global']
}

class Request(object):
    thread = None
    _response = None

    def __init__(self, url, region, method='GET', **kwargs):
        self._response = []
        self.thread = Thread(target=Request.request, args=(self._response, url, region, method), kwargs=kwargs)
        self.thread.start()

    @staticmethod
    def request(results, url, region, method, **kwargs):
        try:
            response = request(url, region, method, **kwargs)
            results.append(None)
            results.append(response)
        except Exception as e:
            results.append(e)

        return True

    def response(self):
        self.thread.join()

        # Exception occurred
        if not self._response[0] is None:
            raise self._response[0]

        return self._response[1]

def request(url, region, type='GET', retry_count=0, **kwargs):
    response = connection_pool_dict[region].request(
        type,
        url.format(
            region=region,
            apiKey=API_KEY,
            **kwargs
        ),
        timeout=10.0
    )

    if response.status == 200:
        return json.loads(response.data)
    elif response.status == 404:
        return None
    elif response.status == 429:
        logging.info('Rate limit exceeded, waiting 20 seconds...')
        sleep(20)
        return request(url, region, type, retry_count+1, **kwargs)
    elif retry_count >= 3:
        raise Exception("Maximum retries exceeded")
    else:
        logging.warning('ELSE HAPPENED!!!!!!!!! -- Response Status: {} FOR {}'.format(response.status, url.format(region=region,apiKey=API_KEY,**kwargs)))
        logging.warning('ELSE HAPPENED!!!!!!!!! -- Response Data: {}'.format(response.data))
        return None
        return request(url, region, type, retry_count+1, **kwargs)