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
from settings import API_URL_SUMMONER_SPELLS

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

    response = request(API_URL_SUMMONER_SPELLS, 'global')
    summoner_spells_dict = response['data']
    version = response['version']

    for summoner_spell in summoner_spells_dict.values():
        insert_values.append(u"({}, {}, {})".format(
            summoner_spell['id'],
            database.escape(summoner_spell['name']),
            database.escape('http://ddragon.leagueoflegends.com/cdn/{}/img/spell/{}'.format(version, summoner_spell['image']['full'])),
        ))

    insert_query = u'''
        INSERT INTO summoner_spells
        (id, name, image_icon_url)
        VALUES
        {}
    '''.format(u','.join(insert_values))

    database.execute('TRUNCATE TABLE summoner_spells')
    database.execute(insert_query)

if __name__ == '__main__':
    logger.info("Spinning up summoner spell fetcher")
    run()