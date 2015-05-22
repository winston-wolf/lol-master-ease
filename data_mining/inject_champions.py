# +----------------------------------------------------------------------+
# | Copyright (c) 2015 Winston Wolf                                      |
# +----------------------------------------------------------------------+
# | This source file is bound by United States copyright law.            |
# +----------------------------------------------------------------------+
# | Author: Winston Wolf <winston.the.cleaner@gmail.com>                 |
# +----------------------------------------------------------------------+

# ---------------------------------------------------- #
# Include shared code
# ---------------------------------------------------- #

import os
import sys

sys.path.append("{}/../".format(os.path.dirname(os.path.realpath(__file__))))

# ---------------------------------------------------- #
# Includes
# ---------------------------------------------------- #

from request import request
import logging
from db import get_connection
from settings import DATABASE_HOST, DATABASE_PORT, DATABASE_USERNAME, DATABASE_PASSWORD, DATABASE_NAME
from settings import API_URL_CHAMPIONS

# ---------------------------------------------------- #
# Logging
# ---------------------------------------------------- #

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s: %(levelname)s: %(message)s")
logger = logging.getLogger('freelo')


# ---------------------------------------------------- #
# Start
# ---------------------------------------------------- #

# This loops the script so that it restarts after it finishes and continues to collect data until told to stop
def run():
    database = get_connection(DATABASE_HOST, DATABASE_PORT, DATABASE_USERNAME, DATABASE_PASSWORD, DATABASE_NAME)
    insert_values = []

    champions_dict = request(API_URL_CHAMPIONS, 'global')['data']

    for champion in champions_dict.values():
        insert_values.append(u"({}, {}, {}, {}, {})".format(
            champion['id'],
            database.escape(champion['name']),
            database.escape('http://ddragon.leagueoflegends.com/cdn/5.2.1/img/champion/' + champion['image']['full']),
            database.escape('http://ddragon.leagueoflegends.com/cdn/img/champion/loading/' + champion['image']['full'].replace('.png', '_0.jpg')),
            database.escape('http://ddragon.leagueoflegends.com/cdn/img/champion/splash/' + champion['image']['full'].replace('.png', '_0.jpg')),
        ))

    insert_query = u'''
        INSERT INTO champions
        (id, name, image_icon_url, image_loading_url, image_splash_url)
        VALUES
        {}
    '''.format(u','.join(insert_values))

    database.execute('TRUNCATE TABLE champions')
    database.execute(insert_query)

if __name__ == '__main__':
    logger.info("Spinning up champion fetcher")
    run()