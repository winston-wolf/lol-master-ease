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
from settings import API_URL_LEAGUES_CHALLENGER, API_URL_LEAGUES_MASTER

# ---------------------------------------------------- #
# Logging
# ---------------------------------------------------- #

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s: %(levelname)s: %(message)s")
logger = logging.getLogger('freelo')

# ---------------------------------------------------- #
# Fetchers
# ---------------------------------------------------- #

def fetch_challenger_players(region):
    return request(API_URL_LEAGUES_CHALLENGER, region)['entries']

def fetch_master_players(region):
    return request(API_URL_LEAGUES_MASTER, region)['entries']

# ---------------------------------------------------- #
# Start
# ---------------------------------------------------- #

# This loops the script so that it restarts after it finishes and continues to collect data until told to stop
def run():
    database = get_connection(DATABASE_HOST, DATABASE_PORT, DATABASE_USERNAME, DATABASE_PASSWORD, DATABASE_NAME)
    insert_values = []
    for region in ['na', 'euw', 'kr']:
        for tier in ['MASTER', 'CHALLENGER']:
            print "Getting {} {}".format(region, tier)

            players = fetch_challenger_players(region) if tier == 'CHALLENGER' else fetch_master_players(region)
            for player in players:
                insert_values.append(u"({}, '{}', {}, '{}', '{}', UTC_TIMESTAMP())".format(
                    player['playerOrTeamId'], region, database.escape(player['playerOrTeamName']), tier, player['division']
                ))

            print "Adding {}".format(region)
            insert_query = u'''
                INSERT INTO summoners
                (id, region, name, rank_tier, rank_division, last_update_datetime)
                VALUES
                {}
                ON DUPLICATE KEY UPDATE
                  rank_tier = VALUES(rank_tier),
                  rank_division = VALUES(rank_division),
                  last_update_datetime = VALUES(last_update_datetime)
            '''.format(u','.join(insert_values))

            database.execute(insert_query)



if __name__ == '__main__':
    logger.info("Spinning up fetcher")
    run()