from flask.ext import restful
from flask.ext.restful import reqparse, abort
from flask import Blueprint
from time import sleep

from db import get_connection, close_connections
from settings import API_URL_SUMMONER_SEARCH, API_URL_MATCH_HISTORY, API_URL_MATCH
from settings import SEASON_NAME, RANK_TIERS, MATCHES_PER_PAGE, PLATFORM_IDS
from settings import DATABASE_HOST, DATABASE_PORT, DATABASE_USERNAME, DATABASE_PASSWORD, DATABASE_NAME

import player_helper
import match_helper
from request import request, Request

api_app = Blueprint('api_app', __name__, url_prefix='/api')
api = restful.Api(api_app)

parser = reqparse.RequestParser()
import logging
logger = logging.getLogger('freelo')
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
logger.addHandler(ch)

RANK_MAX = len(RANK_TIERS) - 1
RANK_ID_TO_NAME = {_id: name for _id, name in enumerate(RANK_TIERS)}
RANK_NAME_TO_ID = {name: _id for _id, name in RANK_ID_TO_NAME.items()}

MISSING_ITEM_TEMP_FIX_SQL = u"""
    AND (0
        OR summoner_item_0_id != 0
        OR summoner_item_1_id != 0
        OR summoner_item_2_id != 0
        OR summoner_item_3_id != 0
        OR summoner_item_4_id != 0
        OR summoner_item_5_id != 0
        OR summoner_item_6_id != 0
        OR match_create_datetime > '2015-06-02 00:00:00'
    )
"""


# returns a trimmed string value as an argument type
def str_trimmed(value):
    return value.strip()


# gets summoner information from the db and pulls from the api if it doesn't exist in our system yet
def get_summoner(region, summoner_name):
    database = get_connection(DATABASE_HOST, DATABASE_PORT, DATABASE_USERNAME, DATABASE_PASSWORD, DATABASE_NAME)

    sql = u"""
        SELECT
            id,
            platform,
            IF(last_refresh_datetime < UTC_TIMESTAMP() - INTERVAL 20 MINUTE OR last_refresh_datetime IS NULL, 1, 0) as `can_refresh`
        FROM
            summoners
        WHERE 1
            AND region = {}
            AND searchable_name = {}
            AND last_update_datetime > UTC_TIMESTAMP() - INTERVAL 7 DAY
    """.format(
        database.escape(region),
        database.escape(summoner_name)
    )

    summoner = database.fetch_one_dict(sql)
    logger.warning('[get_summoner] summoner: {} with sql {}'.format(summoner, sql))

    if not summoner:
        try:
            logger.warning('[get_summoner] adding request for summoner {}'.format(summoner_name))
            response = request(API_URL_SUMMONER_SEARCH, region, summonerName=summoner_name)

            if response is None:
                return False

            data = response.get(summoner_name)

            summoner = {
                # 'id': data.get('summonerId'),
                # 'platform': data.get('currentUser').get('platformId'),
                'id': data.get('id'),
                'platform': PLATFORM_IDS[region],
                'can_refresh': True,
            }
        except Exception as e:
            logger.warning('[get_summoner] Exception: {}'.format(e))
            return False

    return summoner


# gets match ids based on begin and end index and fetches more from the api if needed
def find_match_ids(region, summoner, begin_index, end_index):
    database = get_connection(DATABASE_HOST, DATABASE_PORT, DATABASE_USERNAME, DATABASE_PASSWORD, DATABASE_NAME)

    # if loading the first page and a refresh is possible, pull new data from the api
    if begin_index == 0 and summoner['can_refresh']:
        logger.warning('[find_match_ids] getting api matches')
        api_pull_match_history(region, summoner, begin_index)

        # update the last refresh datetime since we just refreshed
        sql = u"""
            UPDATE
                summoners
            SET
                last_refresh_datetime = UTC_TIMESTAMP()
            WHERE 1
                AND region = {}
                AND id = {}
        """.format(
            database.escape(region),
            summoner['id'],
        )
        database.execute(sql)

    # try getting match ids
    match_ids = db_get_match_ids(region, summoner, begin_index, end_index)
    logger.warning('[find_match_ids] db_get_match_ids FIRST TRY got {}'.format(match_ids))

    # if not the first page and no matches were found, try pulling new ones from the api
    if (begin_index > 0 and not match_ids) or len(match_ids) < MATCHES_PER_PAGE:
        logger.warning('[find_match_ids] getting api matches 2')
        api_pull_match_history(region, summoner, begin_index)
        match_ids = db_get_match_ids(region, summoner, begin_index, end_index)
        logger.warning('[find_match_ids] db_get_match_ids SECOND TRY got {}'.format(match_ids))

    return match_ids


# performs the query to find match ids
def db_get_match_ids(region, summoner, begin_index, end_index):
    database = get_connection(DATABASE_HOST, DATABASE_PORT, DATABASE_USERNAME, DATABASE_PASSWORD, DATABASE_NAME)

    sql = u"""
        SELECT
            match_id
        FROM
            matches
        WHERE 1
            AND match_region = {region}
            AND summoner_id = {summoner_id}
            {missing_item_temp_fix_sql}
        ORDER BY
            match_create_datetime DESC
        LIMIT {limit}
        OFFSET {offset}
    """.format(
        region=database.escape(region),
        summoner_id=summoner['id'],
        limit=(end_index - begin_index),
        offset=begin_index,
        missing_item_temp_fix_sql=MISSING_ITEM_TEMP_FIX_SQL,
    )

    logger.warning('[db_get_match_ids] SQL: {}'.format(sql))

    return database.fetch_all_value(sql)


# provided an offset, gives the difference in rank id, name, and offset
def get_diffed_rank(rank_id, offset):
    if offset is None:
        return {'id': -1, 'name': 'unranked', 'offset': 0}

    diffed_rank = rank_id + int(offset)

    if diffed_rank > RANK_MAX:
        rank_name = 'CHALLENGER'
        diffed_rank = RANK_MAX
    elif diffed_rank < 1:
        rank_name = 'BRONZE'
        diffed_rank = 0
    else:
        rank_name = RANK_ID_TO_NAME[diffed_rank]

    return {'id': diffed_rank, 'name': rank_name, 'offset': int(offset)}


def db_get_match_stats(match_id, region, summoner):
    database = get_connection(DATABASE_HOST, DATABASE_PORT, DATABASE_USERNAME, DATABASE_PASSWORD, DATABASE_NAME)

    player_game_data = database.fetch_all_dict("""
        SELECT
            q2.*,
            summoners.name as summoner_name,
            champions.name as champion_name,
            champions.id as champion_id,
            champions.image_icon_url as champion_icon_url,
            ROUND((tier_diff_cs + tier_diff_vision_wards_placed + tier_diff_assists + tier_diff_deaths + tier_diff_kills + tier_diff_sight_wards_placed + tier_diff_team_first_dragon_kill_time_in_minutes + tier_diff_match_time_in_minutes + tier_diff_damage_done_to_champions)/9) AS overall
        FROM
            (
                SELECT
                        q1.summoner_champion_id,
                        q1.match_region,
                        q1.role,
                        q1.summoner_id,
                        q1.summoner_team_id,
                        q1.summoner_rank_tier,
                        q1.match_create_datetime,
                        q1.match_total_time_in_minutes,
                        q1.summoner_is_winner,
                        q1.summoner_minions_killed,
                        q1.summoner_neutral_minions_killed,
                        q1.summoner_assists,
                        q1.summoner_deaths,
                        q1.summoner_kills,
                        q1.summoner_champion_level,

                        sum_icon1.image_icon_url as summoner_spell_1_icon_url,
                        sum_icon2.image_icon_url as summoner_spell_2_icon_url,

                        CEIL((q1.cs - afd.average_cs) / afd.freelo_dev_cs) AS tier_diff_cs,
                        CEIL((q1.vision_wards_placed - afd.average_vision_wards_placed) / afd.freelo_dev_vision_wards_placed) AS tier_diff_vision_wards_placed,
                        CEIL((q1.assists - afd.average_assists) / afd.freelo_dev_assists) AS tier_diff_assists,
                        CEIL((q1.deaths - afd.average_deaths) / afd.freelo_dev_deaths) AS tier_diff_deaths,
                        CEIL((q1.kills - afd.average_kills) / afd.freelo_dev_kills) AS tier_diff_kills,
                        CEIL((q1.sight_wards_placed - afd.average_sight_wards_placed) / afd.freelo_dev_sight_wards_placed) AS tier_diff_sight_wards_placed,
                        GREATEST(IFNULL(CEIL((q1.team_first_dragon_kill_time_in_minutes - afd.average_cs_first_dragon_time_in_minutes) / afd.freelo_dev_first_dragon_time_in_minutes), -3), -3) AS tier_diff_team_first_dragon_kill_time_in_minutes,
                        CEIL((q1.match_total_time_in_minutes - afd.average_match_time_in_minutes) / afd.freelo_dev_match_time_in_minutes) AS tier_diff_match_time_in_minutes,
                        CEIL((q1.damage_done_to_champions - afd.average_damage_done_to_champions) / afd.freelo_dev_damage_done_to_champions) AS tier_diff_damage_done_to_champions
                FROM
                    (
                        SELECT
                        CASE
                                WHEN summoner_lane = 'JUNGLE' THEN 'JUNGLE'
                                WHEN summoner_role = 'DUO_CARRY' THEN 'CARRY'
                                WHEN summoner_role = 'DUO_SUPPORT' THEN 'SUPPORT'
                                WHEN
                                    summoner_lane = 'MIDDLE'
                                        AND summoner_role IN ('NONE' , 'SOLO')
                                THEN
                                    'MIDDLE'
                                WHEN
                                    summoner_role = 'SOLO'
                                        AND summoner_lane != 'MIDDLE'
                                THEN
                                    'TOP'
                                WHEN summoner_minions_killed < 50 THEN 'SUPPORT'
                                WHEN summoner_role = 'DUO' THEN 'CARRY'
                                ELSE 'UNKNOWN'
                            END AS role,
                            match_region,
                            summoner_champion_id,
                            summoner_id,
                            summoner_team_id,
                            summoner_rank_tier,
                            match_create_datetime,
                            (summoner_minions_killed + summoner_neutral_minions_killed_team_jungle + summoner_neutral_minions_killed_enemy_jungle) / match_total_time_in_minutes * 32 AS cs,
                            summoner_vision_wards_placed / match_total_time_in_minutes * 32 AS vision_wards_placed,
                            summoner_minions_killed,
                            (summoner_neutral_minions_killed_team_jungle + summoner_neutral_minions_killed_enemy_jungle) as summoner_neutral_minions_killed,
                            summoner_spell_1_id,
                            summoner_spell_2_id,
                            summoner_assists,
                            summoner_deaths,
                            summoner_kills_total as summoner_kills,
                            summoner_champion_level,
                            summoner_assists / match_total_time_in_minutes * 32 AS assists,
                            summoner_deaths / match_total_time_in_minutes * 32 AS deaths,
                            summoner_kills_total / match_total_time_in_minutes * 32 AS kills,
                            summoner_sight_wards_placed / match_total_time_in_minutes * 32 AS sight_wards_placed,
                            team_first_dragon_kill_time_in_minutes,
                            match_total_time_in_minutes,
                            summoner_is_winner,
                            summoner_damage_done_to_champions / match_total_time_in_minutes * 32 AS damage_done_to_champions
                        FROM
                            matches
                        WHERE
                            match_id = {match_id}
                            AND match_region = {region}
                    ) q1
                LEFT JOIN aggregate_freelo_deviations afd ON afd.champion_role = q1.role
                    AND afd.champion_id = (CASE q1.summoner_champion_id WHEN 245 THEN 92 ELSE q1.summoner_champion_id END)
                INNER JOIN summoner_spells sum_icon1 ON sum_icon1.id = q1.summoner_spell_1_id
                INNER JOIN summoner_spells sum_icon2 ON sum_icon2.id = q1.summoner_spell_2_id
                GROUP BY
                    summoner_id
            ) q2
        INNER JOIN
            `champions`
            ON q2.summoner_champion_id = champions.id
        INNER JOIN
            `summoners`
            ON q2.summoner_id = summoners.id
            AND q2.match_region = summoners.region
        GROUP BY
            summoner_id
        ORDER BY q2.summoner_team_id, q2.summoner_id != {summoner_id}
    """.format(
        match_id=match_id,
        region=database.escape(region),
        summoner_id=summoner['id'],
    ))
    #TODO: disable the Ekko/Riven quick fix in the "LEFT JOIN aggregate_freelo_deviations" section above (swapping 92 for 245 on q1.summoner_champion_id check)

    # due to the ordering, the current player is either 1st or 5th
    # if the current player isn't 1st, then swap the last 5 with the first 5
    if player_game_data[0]['summoner_id'] != summoner['id']:
        player_game_data = player_game_data[5:] + player_game_data[:5]

    # ---------------------------------------------------- #
    # Predefine Stats
    # ---------------------------------------------------- #

    match_stats = {
        'id': match_id,
        'game_id': match_id,
        'create_datetime': player_game_data[0]['match_create_datetime'].isoformat(),
        'match_total_time_in_minutes': player_game_data[0]['match_total_time_in_minutes'],
        'current_player_team_red': player_game_data[0]['summoner_team_id'] == 200,
        'current_player_won': player_game_data[0]['summoner_is_winner'] == 1,
        'players': [],
        'key_factors': [
            {
                'id': 'overall',
                'name': 'Overall',
                'totals': [],
            },
            {
                'id': 'cs',
                'name': 'CS',
                'totals': [],
            },
            {
                'id': 'wards_vision',
                'name': 'Vision Wards',
                'totals': [],
            },
            {
                'id': 'assists',
                'name': 'Assists',
                'totals': [],
            },
            {
                'id': 'deaths',
                'name': 'Deaths',
                'totals': [],
            },
            {
                'id': 'kills',
                'name': 'Kills',
                'totals': [],
            },
            {
                'id': 'wards_sight',
                'name': 'Sight Wards',
                'totals': [],
            },
            {
                'id': 'first_dragon',
                'name': 'First Dragon',
                'totals': [],
            },
            # {
            #     'id': 'match_time',
            #     'name': 'Game Length',
            #     'totals': [],
            # },
            {
                'id': 'damage_done_to_champions',
                'name': 'Damage to Champions',
                'totals': [],
            },
        ]
    }

    # ---------------------------------------------------- #
    # Build Stats
    # ---------------------------------------------------- #

    stats_players = match_stats['players']
    stats_key_factors = {_factor['id']: _factor for _factor in match_stats['key_factors']}

    # Compensate
    players_ranked_total = 0
    players_ranked_sum = 0
    for player_game in player_game_data:
        rank_id = RANK_NAME_TO_ID[player_game['summoner_rank_tier']]
        player_game['summoner_rank_tier_id'] = rank_id
        if not rank_id == 0:
            players_ranked_sum += rank_id
            players_ranked_total += 1

    average_rank = int(round(float(players_ranked_sum) / players_ranked_total))
    for player_game in player_game_data:
        stats_players.append({
            'summoner_champion': {
                'id': player_game['champion_id'],
                'name': player_game['champion_name'],
                'image_icon_url': player_game['champion_icon_url'],
                'level': player_game['summoner_champion_level'],
            },
            'summoner_name': player_game['summoner_name'],
            'summoner_rank_tier': player_game['summoner_rank_tier'],
            'team_id': player_game['summoner_team_id'],
            'summoner_kills': player_game['summoner_kills'],
            'summoner_deaths': player_game['summoner_deaths'],
            'summoner_assists': player_game['summoner_assists'],
            'summoner_minions_killed': player_game['summoner_minions_killed'],
            'region': region.upper(),
            'summoner_neutral_minions_killed': player_game['summoner_neutral_minions_killed'],
            'summoner_cs': player_game['summoner_minions_killed'] + player_game['summoner_neutral_minions_killed'],
            'summoner_spell_1_icon_url': player_game['summoner_spell_1_icon_url'],
            'summoner_spell_2_icon_url': player_game['summoner_spell_2_icon_url'],
        })

        rank_id = player_game['summoner_rank_tier_id'] or average_rank

        stats_key_factors['overall']['totals'].append(get_diffed_rank(rank_id, player_game['overall']))
        stats_key_factors['cs']['totals'].append(get_diffed_rank(rank_id, player_game['tier_diff_cs']))
        stats_key_factors['wards_vision']['totals'].append(get_diffed_rank(rank_id, player_game['tier_diff_vision_wards_placed']))
        stats_key_factors['wards_sight']['totals'].append(get_diffed_rank(rank_id, player_game['tier_diff_sight_wards_placed']))
        stats_key_factors['assists']['totals'].append(get_diffed_rank(rank_id, player_game['tier_diff_assists']))
        stats_key_factors['deaths']['totals'].append(get_diffed_rank(rank_id, player_game['tier_diff_deaths']))
        stats_key_factors['kills']['totals'].append(get_diffed_rank(rank_id, player_game['tier_diff_kills']))
        stats_key_factors['first_dragon']['totals'].append(get_diffed_rank(rank_id, player_game['tier_diff_team_first_dragon_kill_time_in_minutes']))
        # stats_key_factors['match_time']['totals'].append(get_diffed_rank(rank_id, player_game['tier_diff_match_time_in_minutes']))
        stats_key_factors['damage_done_to_champions']['totals'].append(get_diffed_rank(rank_id, player_game['tier_diff_damage_done_to_champions']))

    return match_stats


# fetches api matches and stores the ones not yet stored
def api_pull_match_history(region, summoner, begin_index):
    database = get_connection(DATABASE_HOST, DATABASE_PORT, DATABASE_USERNAME, DATABASE_PASSWORD, DATABASE_NAME)

    # always try getting 15 matches (max) at a time
    end_index = begin_index + 15

    # fetch matches from the api
    logger.warning('[api_pull_match_history] adding request for match history of {}'.format(summoner['id']))
    response = request(API_URL_MATCH_HISTORY, region, summonerId=summoner['id'], beginIndex=begin_index, endIndex=end_index)

    if response:
        logger.warning('[api_pull_match_history] got {} matches: [{}]'.format(len(response.get('matches', [])), [str(match['matchId']) for match in response.get('matches', [])]))
        matches = response.get('matches', [])
        if matches:
            # see which matches we already have recorded
            sql = u"""
                SELECT
                    match_id
                FROM
                    matches
                WHERE 1
                    AND match_region = {region}
                    AND summoner_id = {summoner_id}
                    AND match_id IN ({match_ids})
                    {missing_item_temp_fix_sql}
                """.format(
                    region=database.escape(region),
                    summoner_id=summoner['id'],
                    match_ids=','.join(str(match['matchId']) for match in matches),
                    missing_item_temp_fix_sql=MISSING_ITEM_TEMP_FIX_SQL,
                )
            recorded_match_ids = database.fetch_all_value(sql)

            logger.warning('[api_pull_match_history] sql: {}'.format(sql))
            logger.warning('[api_pull_match_history] recorded match ids: {}'.format(recorded_match_ids))

            match_stats = []
            for match in matches:
                # if the match is not already recorded and in this season, then record it
                if match['matchId'] not in recorded_match_ids and match['season'] == SEASON_NAME:
                    logger.warning('[api_pull_match_history] getting stats for match {}'.format(match['matchId']))
                    match_stats.append(match_helper.get_stats(match, detailed=False))

            if match_stats:
                logger.warning('[api_pull_match_history] doing player_helper.get_stats()')
                player_stats = player_helper.get_stats(match_stats, database)

                logger.warning('[api_pull_match_history] inserting player {}'.format(summoner['id']))
                player_helper.insert(player_stats, database, summoner['id'])

                for match_stat in match_stats:
                    try:
                        logger.warning('[api_pull_match_history] inserting match stats for match {}'.format(match_stat['match']['id']))
                        match_helper.insert(match_stat, player_stats, database, detailed=False)
                    except Exception, e:
                        logger.warning('[api_pull_match_history] FAILED inserting match stats for match {}: {}'.format(match_stat['match']['id'], e))
                        pass


def api_pull_match(match_id, region):
    database = get_connection(DATABASE_HOST, DATABASE_PORT, DATABASE_USERNAME, DATABASE_PASSWORD, DATABASE_NAME)

    # see if this match has already been recorded
    sql = u"""
        SELECT
            match_id
        FROM
            matches
        WHERE 1
            AND match_region = {}
            AND match_id = {}
            AND details_pulled = 1
        """.format(
            database.escape(region),
            match_id,
        )
    logger.warning('[api_pull_match] sql: {}'.format(sql))
    recorded_match_ids = database.fetch_all_value(sql)

    # don't record the match if it has already been recorded
    if match_id not in recorded_match_ids:
        logger.warning('adding request for match {}'.format(match_id))
        match = request(API_URL_MATCH, region, matchId=match_id, includeTimeline=True)

        if match and 'timeline' in match:
            logger.warning('doing match_helper.get_stats()')
            match_stats = [match_helper.get_stats(match, detailed=True)]

            if match_stats:
                logger.warning('doing player_helper.get_stats()')
                player_stats = player_helper.get_stats(match_stats, database)

                logger.warning('inserting player stats')
                player_helper.insert(player_stats, database)

                for match_stat in match_stats:
                    try:
                        logger.warning('inserting match')
                        match_helper.insert(match_stat, player_stats, database, detailed=True)
                    except Exception:
                        pass


# retrieve a paged list of matches for a summoner in a region
class Matches(restful.Resource):
    def get(self):
        database = get_connection(DATABASE_HOST, DATABASE_PORT, DATABASE_USERNAME, DATABASE_PASSWORD, DATABASE_NAME)

        # process args
        parser.add_argument('region', type=str_trimmed, required=True)
        parser.add_argument('summoner_name', type=str_trimmed, required=True)
        parser.add_argument('page', type=int)
        args = parser.parse_args()
        region = args['region'].lower()
        summoner_name = args['summoner_name'].replace(' ', '').lower()
        page = args['page']
        if not page:
            page = 1

        # set begin and end indexes
        begin_index = (page - 1) * MATCHES_PER_PAGE
        end_index = begin_index + MATCHES_PER_PAGE

        # get summoner
        summoner = get_summoner(region, summoner_name)
        if not summoner:
            abort(404, error_key='SUMMONER_NOT_FOUND')

        # find match ids
        match_ids = find_match_ids(region, summoner, begin_index, end_index)
        logger.warning('going to ultimately pull: {}'.format(match_ids))

        sql = u"""
            SELECT
                m.*,
                c.image_icon_url as summoner_champion_image_icon_url,
                ss1.image_icon_url as summoner_spell_1_image_icon_url,
                ss2.image_icon_url as summoner_spell_2_image_icon_url,
                i0.image_icon_url as summoner_item_0_image_icon_url,
                i1.image_icon_url as summoner_item_1_image_icon_url,
                i2.image_icon_url as summoner_item_2_image_icon_url,
                i3.image_icon_url as summoner_item_3_image_icon_url,
                i4.image_icon_url as summoner_item_4_image_icon_url,
                i5.image_icon_url as summoner_item_5_image_icon_url,
                i6.image_icon_url as summoner_item_6_image_icon_url,
                s.name as summoner_name
            FROM
                matches m
            LEFT JOIN champions c ON c.id = m.summoner_champion_id
            LEFT JOIN summoner_spells ss1 ON ss1.id = m.summoner_spell_1_id
            LEFT JOIN summoner_spells ss2 ON ss2.id = m.summoner_spell_2_id
            LEFT JOIN items i0 ON i0.id = m.summoner_item_0_id
            LEFT JOIN items i1 ON i1.id = m.summoner_item_1_id
            LEFT JOIN items i2 ON i2.id = m.summoner_item_2_id
            LEFT JOIN items i3 ON i3.id = m.summoner_item_3_id
            LEFT JOIN items i4 ON i4.id = m.summoner_item_4_id
            LEFT JOIN items i5 ON i5.id = m.summoner_item_5_id
            LEFT JOIN items i6 ON i6.id = m.summoner_item_6_id
            LEFT JOIN summoners s ON m.summoner_id = s.id AND m.match_region = s.region
            WHERE 1
                AND m.match_region = {}
                AND m.summoner_id = {}
            GROUP BY
                m.match_id
            ORDER BY
                m.match_create_datetime DESC
            LIMIT {}
            OFFSET {}
        """.format(
            database.escape(region),
            summoner['id'],
            (end_index - begin_index),
            begin_index,
        )

        rows = database.fetch_all_dict(sql)

        if not rows:
            abort(404, error_key='NO_MATCHES_FOUND')

        matches = []
        for row in rows:
            match = {
                'id': '{}-{}-{}'.format(region, summoner['id'], row['match_id']),
                'match_id': row['match_id'],
                'create_datetime': row['match_create_datetime'].isoformat(),
                'match_total_time_in_minutes': row['match_total_time_in_minutes'],
                'player': {
                    'summoner_name': row['summoner_name'],
                    'summoner_kills': row['summoner_kills_total'],
                    'summoner_deaths': row['summoner_deaths'],
                    'summoner_assists': row['summoner_assists'],
                    'summoner_cs': row['summoner_minions_killed'] + row['summoner_neutral_minions_killed_team_jungle'] + row['summoner_neutral_minions_killed_enemy_jungle'],
                    'summoner_minions_killed': row['summoner_minions_killed'],
                    'summoner_neutral_minions_killed': row['summoner_neutral_minions_killed_team_jungle'] + row['summoner_neutral_minions_killed_enemy_jungle'],
                    'summoner_spell_1_icon_url': row['summoner_spell_1_image_icon_url'],
                    'summoner_spell_2_icon_url': row['summoner_spell_2_image_icon_url'],
                    'summoner_item_0_icon_url': row['summoner_item_0_image_icon_url'],
                    'summoner_item_1_icon_url': row['summoner_item_1_image_icon_url'],
                    'summoner_item_2_icon_url': row['summoner_item_2_image_icon_url'],
                    'summoner_item_3_icon_url': row['summoner_item_3_image_icon_url'],
                    'summoner_item_4_icon_url': row['summoner_item_4_image_icon_url'],
                    'summoner_item_5_icon_url': row['summoner_item_5_image_icon_url'],
                    'summoner_item_6_icon_url': row['summoner_item_6_image_icon_url'],
                    'summoner_champion': {
                        'image_icon_url': row['summoner_champion_image_icon_url'],
                        'level': row['summoner_champion_level'],
                    },
                    'summoner_is_winner': row['summoner_is_winner'],
                }
            }

            # match history url
            if region == 'kr':
                match['match_history_url'] = 'http://matchhistory.leagueoflegends.co.kr/ko/#match-details/KR/{}/{}'.format(row['match_id'], summoner['id'])
            else:
                match['match_history_url'] = 'http://matchhistory.{}.leagueoflegends.com/en/#match-details/{}/{}/{}'.format(region, summoner['platform'], row['match_id'], summoner['id'])

            # stats
            if row['details_pulled']:
                match['stats'] = db_get_match_stats(row['match_id'], row['match_region'], summoner)

            matches.append(match)

        close_connections()

        return {
            'page': page,
            'matches': matches,
        }


# retrieve the stats for a specific match
class MatchStats(restful.Resource):
    def get(self, match_id):
        # process args
        parser.add_argument('region', type=str_trimmed, required=True)
        parser.add_argument('summoner_name', type=str_trimmed, required=True)
        args = parser.parse_args()
        region = args['region'].lower()
        summoner_name = args['summoner_name'].replace(' ', '').lower()

        summoner = get_summoner(region, summoner_name)

        # make sure the stats are in our database
        api_pull_match(match_id, region)

        # get the stats
        match_stats = db_get_match_stats(match_id, region, summoner)

        close_connections()

        return {
            'stats': match_stats,
        }


def db_get_matches_stats(region, summoner):
    # need at least 10 games to see aggregate stats??
    database = get_connection(DATABASE_HOST, DATABASE_PORT, DATABASE_USERNAME, DATABASE_PASSWORD, DATABASE_NAME)

    matches_stats = database.fetch_all_dict("""
        SELECT
            q2.*,
            summoners.name as summoner_name,
            champions.name as champion_name,
            champions.id as champion_id,
            champions.image_icon_url as champion_icon_url,
            ROUND((tier_diff_cs + tier_diff_vision_wards_placed + tier_diff_assists + tier_diff_deaths + tier_diff_kills + tier_diff_sight_wards_placed + tier_diff_team_first_dragon_kill_time_in_minutes + tier_diff_match_time_in_minutes + tier_diff_damage_done_to_champions)/9) AS overall
        FROM
            (
                SELECT
                        q1.summoner_champion_id,
                        q1.match_region,
                        q1.match_id,
                        q1.role,
                        q1.summoner_id,
                        q1.summoner_team_id,
                        q1.summoner_rank_tier,
                        q1.match_create_datetime,
                        q1.match_total_time_in_minutes,
                        q1.summoner_is_winner,
                        q1.summoner_minions_killed,
                        q1.summoner_neutral_minions_killed,
                        q1.summoner_assists,
                        q1.summoner_deaths,
                        q1.summoner_kills,
                        q1.summoner_champion_level,

                        CEIL((q1.cs - afd.average_cs) / afd.freelo_dev_cs) AS tier_diff_cs,
                        CEIL((q1.vision_wards_placed - afd.average_vision_wards_placed) / afd.freelo_dev_vision_wards_placed) AS tier_diff_vision_wards_placed,
                        CEIL((q1.assists - afd.average_assists) / afd.freelo_dev_assists) AS tier_diff_assists,
                        CEIL((q1.deaths - afd.average_deaths) / afd.freelo_dev_deaths) AS tier_diff_deaths,
                        CEIL((q1.kills - afd.average_kills) / afd.freelo_dev_kills) AS tier_diff_kills,
                        CEIL((q1.sight_wards_placed - afd.average_sight_wards_placed) / afd.freelo_dev_sight_wards_placed) AS tier_diff_sight_wards_placed,
                        GREATEST(IFNULL(CEIL((q1.team_first_dragon_kill_time_in_minutes - afd.average_cs_first_dragon_time_in_minutes) / afd.freelo_dev_first_dragon_time_in_minutes), -3), -3) AS tier_diff_team_first_dragon_kill_time_in_minutes,
                        CEIL((q1.match_total_time_in_minutes - afd.average_match_time_in_minutes) / afd.freelo_dev_match_time_in_minutes) AS tier_diff_match_time_in_minutes,
                        CEIL((q1.damage_done_to_champions - afd.average_damage_done_to_champions) / afd.freelo_dev_damage_done_to_champions) AS tier_diff_damage_done_to_champions
                FROM
                    (
                        SELECT
                        CASE
                                WHEN summoner_lane = 'JUNGLE' THEN 'JUNGLE'
                                WHEN summoner_role = 'DUO_CARRY' THEN 'CARRY'
                                WHEN summoner_role = 'DUO_SUPPORT' THEN 'SUPPORT'
                                WHEN
                                    summoner_lane = 'MIDDLE'
                                        AND summoner_role IN ('NONE' , 'SOLO')
                                THEN
                                    'MIDDLE'
                                WHEN
                                    summoner_role = 'SOLO'
                                        AND summoner_lane != 'MIDDLE'
                                THEN
                                    'TOP'
                                WHEN summoner_minions_killed < 50 THEN 'SUPPORT'
                                WHEN summoner_role = 'DUO' THEN 'CARRY'
                                ELSE 'UNKNOWN'
                            END AS role,
                            match_region,
                            match_id,
                            summoner_champion_id,
                            summoner_id,
                            summoner_team_id,
                            summoner_rank_tier,
                            match_create_datetime,
                            (summoner_minions_killed + summoner_neutral_minions_killed_team_jungle + summoner_neutral_minions_killed_enemy_jungle) / match_total_time_in_minutes * 32 AS cs,
                            summoner_vision_wards_placed / match_total_time_in_minutes * 32 AS vision_wards_placed,
                            summoner_minions_killed,
                            (summoner_neutral_minions_killed_team_jungle + summoner_neutral_minions_killed_enemy_jungle) as summoner_neutral_minions_killed,
                            summoner_assists,
                            summoner_deaths,
                            summoner_kills_total as summoner_kills,
                            summoner_champion_level,
                            summoner_assists / match_total_time_in_minutes * 32 AS assists,
                            summoner_deaths / match_total_time_in_minutes * 32 AS deaths,
                            summoner_kills_total / match_total_time_in_minutes * 32 AS kills,
                            summoner_sight_wards_placed / match_total_time_in_minutes * 32 AS sight_wards_placed,
                            team_first_dragon_kill_time_in_minutes,
                            match_total_time_in_minutes,
                            summoner_is_winner,
                            summoner_damage_done_to_champions / match_total_time_in_minutes * 32 AS damage_done_to_champions
                        FROM
                            matches
                        WHERE
                            summoner_id = {summoner_id}
                            AND match_region = {region}
                            AND details_pulled = 1
                    ) q1
                LEFT JOIN aggregate_freelo_deviations afd ON afd.champion_role = q1.role
                    AND afd.champion_id = (CASE q1.summoner_champion_id WHEN 245 THEN 92 ELSE q1.summoner_champion_id END)
            ) q2
        INNER JOIN
            `champions`
            ON q2.summoner_champion_id = champions.id
        INNER JOIN
            `summoners`
            ON q2.summoner_id = summoners.id
            AND q2.match_region = summoners.region
        LIMIT 30
    """.format(
        region=database.escape(region),
        summoner_id=summoner['id'],
    ))
    #TODO: disable the Ekko/Riven quick fix in the "LEFT JOIN aggregate_freelo_deviations" section above (swapping 92 for 245 on q1.summoner_champion_id check)

    overall = {}
    for match_stats in matches_stats:
        rank_id = RANK_NAME_TO_ID[match_stats['summoner_rank_tier']]

        league = get_diffed_rank(rank_id, match_stats['overall'])
        if league['name'] not in overall:
            overall[league['name']] = 0
        overall[league['name']] += 1

    overall['total'] = len(matches_stats)

    return {
        'overall': overall,
    }


# looks at the detailed stats of up to the last 30 games and returns a sum of each overall deviation league score which will then be used in a visual chart
class MatchesStats(restful.Resource):
    def get(self):
        # process args
        parser.add_argument('region', type=str_trimmed, required=True)
        parser.add_argument('summoner_name', type=str_trimmed, required=True)
        args = parser.parse_args()
        region = args['region'].lower()
        summoner_name = args['summoner_name'].replace(' ', '').lower()

        summoner = get_summoner(region, summoner_name)

        aggregate_stats = db_get_matches_stats(region, summoner)

        close_connections()

        return {
            'stats': aggregate_stats,
        }


api.add_resource(Matches, '/1.0/matches')
api.add_resource(MatchStats, '/1.0/matches/<int:match_id>/stats')
api.add_resource(MatchesStats, '/1.0/matches/stats')
