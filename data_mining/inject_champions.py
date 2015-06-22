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
import json
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
    json_values = []
    insert_values = []

    response = request(API_URL_CHAMPIONS, 'global')
    champions_dict = response['data']
    version = response['version']

    for champion in champions_dict.values():
        image_icon_url = 'http://ddragon.leagueoflegends.com/cdn/{}/img/champion/{}'.format(version, champion['image']['full'])
        image_loading_url = 'http://ddragon.leagueoflegends.com/cdn/img/champion/loading/' + champion['image']['full'].replace('.png', '_0.jpg')
        image_splash_url = 'http://ddragon.leagueoflegends.com/cdn/img/champion/splash/' + champion['image']['full'].replace('.png', '_0.jpg')

        json_values.append({
            'id': champion['id'],
            'name': champion['name'],
            'image_icon_url': image_icon_url,
            'image_loading_url': image_loading_url,
            'image_splash_url': image_splash_url,
        })

        insert_values.append(u"({}, {}, {}, {}, {})".format(
            champion['id'],
            database.escape(champion['name']),
            database.escape(image_icon_url),
            database.escape(image_loading_url),
            database.escape(image_splash_url),
        ))

    insert_query = u'''
        INSERT INTO champions
        (id, name, image_icon_url, image_loading_url, image_splash_url)
        VALUES
        {}
    '''.format(u','.join(insert_values))

    database.execute('TRUNCATE TABLE champions')
    database.execute(insert_query)

    # save champion data to disk, too
    cur_dir = os.path.dirname(os.path.realpath(__file__))
    f = open('{}/../site/front_end/static/data/champions.json'.format(cur_dir), 'w')
    f.write(json.dumps(json_values))
    f.close()


if __name__ == '__main__':
    logger.info("Spinning up champion fetcher")
    run()