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

import match
import player
from request import request, Request
from threading import Thread, Event
from Queue import Queue, Empty
from time import sleep
import logging
import signal
from db import get_connection
from settings import DATABASE_HOST, DATABASE_PORT, DATABASE_USERNAME, DATABASE_PASSWORD, DATABASE_NAME
from settings import API_URL_MATCH_HISTORY, API_URL_MATCH
from settings import SEASON_NAME

THREADS = 16

# ---------------------------------------------------- #
# Logging
# ---------------------------------------------------- #

logging.basicConfig(format="%(asctime)s: %(levelname)s: %(message)s")
logging.getLogger("requests").setLevel(logging.ERROR)
logging.getLogger("requests.packages.urllib3").setLevel(logging.ERROR)
logger = logging.getLogger('freelo')
logger.setLevel(logging.INFO)

# ---------------------------------------------------- #
# Signal Handling
# ---------------------------------------------------- #

def signal_handler(signum, frame):
    logger.debug("Received Signal: %s at frame: %s" % (signum, frame))

    if signum == signal.SIGTERM:
        logger.info('Received request to terminate daemon (SIGTERM)')
        stopThreadEvent.set()
    elif signum == signal.SIGINT:
        logger.info('Received request to terminate daemon (Keyboard)')
        stopThreadEvent.set()
    elif signum == signal.SIGHUP:
        logger.info('Received reload config request (SIGHUP)')
        reloadEvent.set()

signal.signal(signal.SIGHUP, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

stopThreadEvent = Event()
reloadEvent = Event()

# ---------------------------------------------------- #
# Fetchers
# ---------------------------------------------------- #

def fetch_recent_matches(region, summoner_id, limit=15, page=1):
    beginIndex = (page-1) * limit
    endIndex = beginIndex + limit

    return request(API_URL_MATCH_HISTORY, region, summonerId=summoner_id, beginIndex=beginIndex, endIndex=endIndex)

def fetch_match(region, match_id, include_timeline=True):
    return request(API_URL_MATCH, region, matchId=match_id, includeTimeline='true' if include_timeline else 'false')

# ---------------------------------------------------- #
# Runner Threads
# ---------------------------------------------------- #

def thread_find_user(in_queue):
    database = get_connection(DATABASE_HOST, DATABASE_PORT, DATABASE_USERNAME, DATABASE_PASSWORD, DATABASE_NAME, cache=False)

    while not stopThreadEvent.is_set():
        try:
            region, summoner_id = in_queue.get(timeout=0.1)
        except Empty:
            continue

        # ---------------------------------------------------- #
        # Fetch Match IDs to inspect
        # ---------------------------------------------------- #

        logger.debug("Summoner {id} {region}...".format(id=summoner_id, region=region))

        try:

            # Find match IDs that have not been touched yet
            # And are in this season
            page = 1
            match_ids_to_fetch = []
            while len(match_ids_to_fetch) < 5:
                recent_matches = fetch_recent_matches(region, summoner_id, limit=10, page=page).get('matches', [])
                match_ids = [_match['matchId'] for _match in recent_matches if _match['season'] == SEASON_NAME]
                match_id_strs = [str(match_id) for match_id in match_ids]

                # if we found no matches this season, BAIL
                if not match_ids:
                    break

                # Find all matches we've already fetched
                match_ids_prerecorded = database.fetch_all_value(u"""
                    SELECT match_id from matches where match_region = '{}' AND match_id IN ({})
                """.format(
                    region,
                    ",".join(match_id_strs)
                ))

                match_ids_prerecorded_dict = {int(match_id): True for match_id in match_ids_prerecorded}
                for match_id in match_ids:
                    if not match_id in match_ids_prerecorded_dict:
                        match_ids_to_fetch.append(match_id)

                page += 1

            if not match_ids_to_fetch:
                logger.warning("NO MATCHES...")

                continue


            # ---------------------------------------------------- #
            # Fetch Matches
            # ---------------------------------------------------- #

            match_requests = []
            for match_id in match_ids_to_fetch:
                match_requests.append((match_id, Request(API_URL_MATCH, region, matchId=match_id, includeTimeline=True)))

            match_stats = []
            for match_id, match_request in match_requests:
                _match = match_request.response()
                if not _match or not 'timeline' in _match:
                    logger.warning("Match is kill D: #{}...".format(match_id))
                    continue

                match_stats.append(match.get_stats(_match))

            # ---------------------------------------------------- #
            # Get Match Stats
            # ---------------------------------------------------- #

            if match_stats:
                logger.info("Getting Players...")
                player_stats = player.get_stats(match_stats, database)

                logger.info("Inserting Players...")
                player.insert(player_stats, database, summoner_id)

                logger.info("Inserting Stats...")
                for match_stat in match_stats:
                    try:
                        match.insert(match_stat, player_stats, database)
                    except Exception, e:
                        logger.warning("Exception adding match, possible dupe {} {}... ({})".format(region, match_stat['match']['id'], e))
            else:
                logger.debug("NO PLAYERS WTF {} {}...".format(region, summoner_id))
        except Exception, e:
            logger.debug("Shit the bed while fetching/inserting: {}".format(e))

# ---------------------------------------------------- #
# Start
# ---------------------------------------------------- #

# This loops the script so that it restarts after it finishes and continues to collect data until told to stop
def run():
    in_queue = Queue()

    logger.debug("Spinning up {} threads".format(THREADS))
    for i in range(THREADS):
        Thread(target=thread_find_user, args=(in_queue,)).start()


    summoners_query = u'''
        SELECT
          id,
          region
        FROM
          summoners
        WHERE
          1
          {}
          AND last_spider_datetime > UTC_TIMESTAMP() - INTERVAL 1 DAY
          OR  last_spider_datetime is NULL
        ORDER BY RAND()
        LIMIT {}
    '''

    while not stopThreadEvent.is_set():
        logger.info("Finding Summoners...")

        database = get_connection(DATABASE_HOST, DATABASE_PORT, DATABASE_USERNAME, DATABASE_PASSWORD, DATABASE_NAME)

        summoners = []
        summoners = summoners + database.fetch_all_dict(summoners_query.format('', 20))
        summoners = summoners + database.fetch_all_dict(summoners_query.format( "AND rank_tier = 'BRONZE'", 100 ))
        summoners = summoners + database.fetch_all_dict(summoners_query.format( "AND rank_tier = 'MASTER'", 2 ))
        summoners = summoners + database.fetch_all_dict(summoners_query.format( "AND rank_tier = 'CHALLENGER'", 2 ))

        for summoner in summoners:
            in_queue.put((summoner['region'], summoner['id']))

        logger.info("Queued...")
        while not in_queue.empty() and not stopThreadEvent.is_set():
            sleep(0.1)

if __name__ == '__main__':
    logger.info("Spinning up fetcher")
    run()