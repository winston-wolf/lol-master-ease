# +----------------------------------------------------------------------+
# | Copyright (c) 2015 Winston Wolf                                      |
# +----------------------------------------------------------------------+
# | This source file is bound by United States copyright law.            |
# +----------------------------------------------------------------------+
# | Author: Winston Wolf <winston.the.cleaner@gmail.com>                 |
# +----------------------------------------------------------------------+

import logging
from settings import API_URL_LEAGUES_RANK
from request import Request

logger = logging.getLogger('freelo')

def sanitize_name(name):
    return name.replace(' ', '').lower()

# Finds recent ranking for all players in a list of matches
# Assumes all matches are on the same region
def get_stats(match_stats, database):
    players = {}
    region = match_stats[0]['match']['region']
    platform = match_stats[0]['match']['platform']
    for match_stat in match_stats:
        _region = match_stat['match']['region']
        if not _region == region:
            raise Exception('Cross region match pulling not supported')
        for player in match_stat['players']:
            summoner_id = player['id']
            if not summoner_id in players:
                players[summoner_id] = { 'region': _region, 'platform': platform, 'found_in_database': False, 'name': player['name'] }

    # Fetch anything we can locally
    player_ranks = database.fetch_all_dict("""
      SELECT
        id, rank_tier, rank_division, name
      FROM summoners
      WHERE 1
        AND region = '{}'
        AND id IN ({})
        AND last_update_datetime >= UTC_TIMESTAMP() - INTERVAL 14 DAY
    """.format(
        region,
        ",".join([ str(_id) for _id in players.keys() ]),
    ))

    for player_rank in player_ranks:
        player = players[player_rank['id']]
        player['rank_tier'] = player_rank['rank_tier']
        player['rank_division'] = player_rank['rank_division']
        player['found_in_database'] = True

    # Fetch missing players
    requests = []
    for summoner_id, player in players.items():
        if not 'rank' in player:
            logger.warning('adding request for player {}'.format(summoner_id))
            requests.append((summoner_id, player, Request(API_URL_LEAGUES_RANK, region, summonerId=summoner_id)))

    for summoner_id, player, _request in requests:
        try:
            logger.warning('waiting for response for player {}'.format(summoner_id))
            response = _request.response()
            logger.warning('got response')
            found = False
            rankings = response.get(str(summoner_id))
            if rankings:
                for entry in rankings:
                    if entry['queue'] == 'RANKED_SOLO_5x5':
                        player['rank_tier'] = entry['tier']
                        player['rank_division'] = entry['entries'][0]['division']
                        found = True
                        break
        except Exception, e:
            logger.warning("Rank not found: {} -> {}".format(region, summoner_id))

        if not found:
            logger.warning("Summoner has unknown rank: {} -> {}".format(region, summoner_id))
            # Nothing found :{
            player['rank_tier'] = 'UNRANKED'
            player['rank_division'] = None

    return players


def insert(player_stats, database, summoner_id_spidered=0):
    insert_values = []
    for summoner_id, player in player_stats.items():
        if not player['found_in_database'] or summoner_id == summoner_id_spidered:
            insert_values.append(u"({id}, '{region}', '{platform}', {name}, {searchable_name}, '{rank_tier}', '{rank_division}', {last_spider_datetime}, UTC_TIMESTAMP())".format(
                id=summoner_id,
                region=player['region'],
                platform=player['platform'],
                name=database.escape(player['name']),
                searchable_name=database.escape(sanitize_name(player['name'])),
                rank_tier=player['rank_tier'],
                rank_division=player['rank_division'],
                last_spider_datetime='UTC_TIMESTAMP()' if summoner_id == summoner_id_spidered else 'NULL',
            ))

    if insert_values:
        insert_query = u'''
            INSERT INTO summoners
                (id, region, platform, name, searchable_name, rank_tier, rank_division, last_spider_datetime, last_update_datetime)
            VALUES
                {}
            ON DUPLICATE KEY UPDATE
                platform = VALUES(platform),
                name = VALUES(name),
                searchable_name = VALUES(searchable_name),
                rank_tier = VALUES(rank_tier),
                rank_division = VALUES(rank_division),
                last_spider_datetime = IFNULL(VALUES(last_spider_datetime), last_spider_datetime),
                last_update_datetime = VALUES(last_update_datetime)
        '''.format(u','.join(insert_values))
        database.execute(insert_query)