from flask.ext import restful
from flask.ext.restful import reqparse, abort
from flask import Blueprint
from time import sleep

from db import get_connection
from settings import API_URL_SUMMONER_SEARCH, API_URL_MATCH_HISTORY, API_URL_MATCH
from settings import SEASON_NAME, RANK_TIERS, MATCHES_PER_PAGE
from settings import DATABASE_HOST, DATABASE_PORT, DATABASE_USERNAME, DATABASE_PASSWORD, DATABASE_NAME

import player
import match
from request import request, Request

api_app = Blueprint('api_app', __name__, url_prefix='/api')
api = restful.Api(api_app)

parser = reqparse.RequestParser()
import logging
logger = logging.getLogger('freelo')

# returns a trimmed string value as an argument type
def str_trimmed(value):
    return value.strip()


class Stats(restful.Resource):
    # fetches api matches and stores the ones not yet stored, returning a list of match ids
    def _fetch_api_matches(self, region, summoner, begin_index):
        database = get_connection(DATABASE_HOST, DATABASE_PORT, DATABASE_USERNAME, DATABASE_PASSWORD, DATABASE_NAME)

        # always pull in chunks of 15
        end_index = begin_index + 15

        # fetch matches from the api
        logger.warning('getting match history')
        response = request(API_URL_MATCH_HISTORY, region, summonerId=summoner['id'], beginIndex=begin_index, endIndex=end_index)
        logger.warning('got {} matches'.format(len(response.get('matches', []))))

        if response:
            match_id_strs = []
            # only include those from this season
            # NOTE: reverse since results are backwards
            matches = response.get('matches', [])
            matches.reverse()
            for _match in matches:
                if _match['season'] == SEASON_NAME:
                    match_id_strs.append(str(_match['matchId']))

            # see which matches are not already in our database
            match_ids_prerecorded = database.fetch_all_value(u"""
                SELECT
                    match_id
                FROM
                    matches
                WHERE 1
                    AND match_region = {}
                    AND match_id IN ({})
            """.format(
                database.escape(region),
                ",".join(match_id_strs),
            ))

            match_ids_prerecorded_dict = {int(match_id): True for match_id in match_ids_prerecorded}
            match_ids_to_fetch = []
            for match_id_str in match_id_strs:
                if not int(match_id_str) in match_ids_prerecorded_dict:
                    match_ids_to_fetch.append(int(match_id_str))

            logger.warning('match ids to fetch: {}'.format(match_ids_to_fetch))

            # fetch match data and store it
            if match_ids_to_fetch:
                match_requests = []
                for match_id in match_ids_to_fetch:
                    logger.warning('adding request for match {}'.format(match_id))
                    match_requests.append((match_id, Request(API_URL_MATCH, region, matchId=match_id, includeTimeline=True)))

                match_stats = []
                for match_id, match_request in match_requests:
                    logger.warning('waiting for response from match {}'.format(match_id))
                    _match = match_request.response()
                    if not _match or not 'timeline' in _match:
                        logger.warning('match was bad or no timeline')
                        continue

                    logger.warning('doing match.get_stats()')
                    match_stats.append(match.get_stats(_match))

                    if match_stats:
                        logger.warning('doing player.get_stats()')
                        player_stats = player.get_stats(match_stats, database)
                        logger.warning('inserting player {}'.format(summoner['id']))
                        player.insert(player_stats, database, summoner['id'])

                        for match_stat in match_stats:
                            try:
                                logger.warning('inserting match')
                                match.insert(match_stat, player_stats, database)
                            except Exception:
                                pass

        # set the refresh datetime
        database.execute(u"""
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
        ))

    def _get_match_ids(self, region, summoner, begin_index, end_index):
        database = get_connection(DATABASE_HOST, DATABASE_PORT, DATABASE_USERNAME, DATABASE_PASSWORD, DATABASE_NAME)

        # if loading a fresh page and a refresh is possible, pull new data from the api
        if begin_index == 0 and summoner['can_refresh']:
            self._fetch_api_matches(region, summoner, begin_index)

        # fetch matches from the database
        match_ids = database.fetch_all_value(u"""
            SELECT
                match_id
            FROM
                matches
            WHERE 1
                AND match_region = {}
                AND summoner_id = {}
            ORDER BY
                match_create_datetime DESC
            LIMIT {}
            OFFSET {}
        """.format(
            database.escape(region),
            summoner['id'],
            (end_index - begin_index),
            begin_index,
        ))

        return match_ids

    def _get_summoner(self, region, summoner_name):
        database = get_connection(DATABASE_HOST, DATABASE_PORT, DATABASE_USERNAME, DATABASE_PASSWORD, DATABASE_NAME)

        summoner = database.fetch_one_dict(u"""
            SELECT
                id,
                platform,
                last_refresh_datetime < UTC_TIMESTAMP() - INTERVAL 20 MINUTE as `can_refresh`
            FROM
                summoners
            WHERE 1
                AND region = {}
                AND searchable_name = {}
                AND last_update_datetime > UTC_TIMESTAMP() - INTERVAL 7 DAY
                AND last_refresh_datetime IS NOT NULL
        """.format(
            database.escape(region),
            database.escape(summoner_name)
        ))

        logger.warning('summoner: {}'.format(summoner))

        if not summoner:
            try:
                response = request(API_URL_SUMMONER_SEARCH, region, summonerName=summoner_name)
                logger.warning('api url summoner search response: {}'.format(response))

                if response is None:
                    return False

                data = response.get(summoner_name)

                summoner = {
                    'id': data.get('summonerId'),
                    'platform': data.get('currentUser').get('platformId'),
                    'can_refresh': True,
                }
            except Exception, e:
                logger.warning('BAM: {}'.format(e))
                return False

        return summoner

    def get(self):
        database = get_connection(DATABASE_HOST, DATABASE_PORT, DATABASE_USERNAME, DATABASE_PASSWORD, DATABASE_NAME)

        # process args
        parser.add_argument('region', type=str_trimmed, required=True)
        parser.add_argument('summoner_name', type=str_trimmed, required=True)
        parser.add_argument('page', type=int)
        args = parser.parse_args()
        region = args['region'].lower()
        summoner_name = args['summoner_name']
        page = args['page']
        if not page:
            page = 1

        # set begin and end indexes
        begin_index = (page - 1) * MATCHES_PER_PAGE
        end_index = begin_index + MATCHES_PER_PAGE

        # get the summoner
        summoner = self._get_summoner(region, player.sanitize_name(summoner_name))
        if not summoner:
            abort(404, error_key='SUMMONER_NOT_FOUND')

        # get match ids
        match_ids = self._get_match_ids(region, summoner, begin_index, end_index)

        # ---------------------------------------------------- #
        # Pull Game
        # ---------------------------------------------------- #

        if not match_ids:
            abort(404, error_key='NO_MATCHES_FOUND')

        stats_combined = []
        for match_id in match_ids:
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
                            AND afd.champion_id = q1.summoner_champion_id
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

            # due to the ordering, the current player is either 1st or 5th
            # if the current player isn't 1st, then swap the last 5 with the first 5
            if player_game_data[0]['summoner_id'] != summoner['id']:
                player_game_data = player_game_data[5:] + player_game_data[:5]

            # ---------------------------------------------------- #
            # Predefine Stats
            # ---------------------------------------------------- #
            """
            Platform correction queries:

            UPDATE `lol_master_ease`.`summoners` SET `platform` = 'RU' WHERE `region` = 'ru';
            UPDATE `lol_master_ease`.`summoners` SET `platform` = 'BR1' WHERE `region` = 'br';
            UPDATE `lol_master_ease`.`summoners` SET `platform` = 'OC1' WHERE `region` = 'oce';
            UPDATE `lol_master_ease`.`summoners` SET `platform` = 'EUW1' WHERE `region` = 'euw';
            UPDATE `lol_master_ease`.`summoners` SET `platform` = 'EUN1' WHERE `region` = 'eune';
            UPDATE `lol_master_ease`.`summoners` SET `platform` = 'KR' WHERE `region` = 'kr';
            UPDATE `lol_master_ease`.`summoners` SET `platform` = 'LA1' WHERE `region` = 'lan';
            UPDATE `lol_master_ease`.`summoners` SET `platform` = 'LA2' WHERE `region` = 'las';
            UPDATE `lol_master_ease`.`summoners` SET `platform` = 'TR1' WHERE `region` = 'tr';
            """

            if player_game_data[0]['match_region'] == 'kr':
                match_history_url = 'http://matchhistory.leagueoflegends.co.kr/ko/#match-details/KR/{}/{}'.format(match_id, summoner['id'])
            else:
                match_history_url = 'http://matchhistory.{}.leagueoflegends.com/en/#match-details/{}/{}/{}'.format(player_game_data[0]['match_region'], summoner['platform'], match_id, summoner['id'])

            stats = {
                'id': match_id,
                'game_id': match_id,
                'create_datetime': player_game_data[0]['match_create_datetime'].isoformat(),
                'match_total_time_in_minutes': player_game_data[0]['match_total_time_in_minutes'],
                'current_player_team_red': player_game_data[0]['summoner_team_id'] == 200,
                'current_player_won': player_game_data[0]['summoner_is_winner'] == 1,
                'match_history_url': match_history_url,
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
                    {
                        'id': 'match_time',
                        'name': 'Game Length',
                        'totals': [],
                    },
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

            RANK_MAX = len(RANK_TIERS) - 1
            RANK_ID_TO_NAME = {_id: name for _id, name in enumerate(RANK_TIERS)}
            RANK_NAME_TO_ID = {name: _id for _id, name in RANK_ID_TO_NAME.items()}

            stats_players = stats['players']
            stats_key_factors = {_factor['id']: _factor for _factor in stats['key_factors']}

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
                    'champion': {
                        'id': player_game['champion_id'],
                        'name': player_game['champion_name'],
                        'image_icon_url': player_game['champion_icon_url'],
                    },
                    'summoner_name': player_game['summoner_name'],
                    'summoner_rank_tier': player_game['summoner_rank_tier'],
                    'team_id': player_game['summoner_team_id'],
                    'summoner_champion_level': player_game['summoner_champion_level'],
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
                def get_diffed_rank(offset):
                    if offset is None:
                        return {'id': -1, 'name': 'unranked', 'offset': 0}

                    diffed_rank = rank_id + int(offset)

                    if diffed_rank > RANK_MAX:
                        rank_name = 'GOD'
                        diffed_rank = RANK_MAX
                    elif diffed_rank < 1:
                        rank_name = 'WOOD'
                        diffed_rank = 0
                    else:
                        rank_name = RANK_ID_TO_NAME[diffed_rank]

                    return {'id': diffed_rank, 'name': rank_name, 'offset': int(offset)}

                stats_key_factors['overall']['totals'].append(get_diffed_rank(player_game['overall']))
                stats_key_factors['cs']['totals'].append(get_diffed_rank(player_game['tier_diff_cs']))
                stats_key_factors['wards_vision']['totals'].append(get_diffed_rank(player_game['tier_diff_vision_wards_placed']))
                stats_key_factors['wards_sight']['totals'].append(get_diffed_rank(player_game['tier_diff_sight_wards_placed']))
                stats_key_factors['assists']['totals'].append(get_diffed_rank(player_game['tier_diff_assists']))
                stats_key_factors['deaths']['totals'].append(get_diffed_rank(player_game['tier_diff_deaths']))
                stats_key_factors['kills']['totals'].append(get_diffed_rank(player_game['tier_diff_kills']))
                stats_key_factors['first_dragon']['totals'].append(get_diffed_rank(player_game['tier_diff_team_first_dragon_kill_time_in_minutes']))
                stats_key_factors['match_time']['totals'].append(get_diffed_rank(player_game['tier_diff_match_time_in_minutes']))
                stats_key_factors['damage_done_to_champions']['totals'].append(get_diffed_rank(player_game['tier_diff_damage_done_to_champions']))

            stats_combined.append(stats)

        if not stats_combined:
            abort(404, error_key='NO_MATCHES_FOUND')

        return {'page': page, 'stats':stats_combined}


api.add_resource(Stats, '/1.0/stats')
