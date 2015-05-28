from flask.ext import restful
from flask.ext.restful import reqparse, abort
from flask import Blueprint
from time import sleep

from db import get_connection
from settings import API_URL_SUMMONER_SEARCH, API_URL_MATCH_HISTORY, API_URL_MATCH
from settings import SEASON_NAME, RANK_TIERS
from settings import DATABASE_HOST, DATABASE_PORT, DATABASE_USERNAME, DATABASE_PASSWORD, DATABASE_NAME

import player
import match
from request import request, Request

api_app = Blueprint('api_app', __name__, url_prefix='/api')
api = restful.Api(api_app)

parser = reqparse.RequestParser()


# returns a trimmed string value as an argument type
def str_trimmed(value):
    return value.strip()


class Stats(restful.Resource):
    def get(self):
        parser.add_argument('region', type=str_trimmed, required=True)
        parser.add_argument('summoner_name', type=str_trimmed, required=True)
        args = parser.parse_args()

        database = get_connection(DATABASE_HOST, DATABASE_PORT, DATABASE_USERNAME, DATABASE_PASSWORD, DATABASE_NAME)

        region = args['region'].lower()
        region_escaped = database.escape(region)
        summoner_name = args['summoner_name']
        summoner_name_searchable = player.sanitize_name(summoner_name)

        # ---------------------------------------------------- #
        # Find if user exists
        # ---------------------------------------------------- #

        fetch_match = True
        summoner_id = None
        summoner = database.fetch_one_dict("""
                SELECT
                  id,
                  last_update_datetime < UTC_TIMESTAMP() - INTERVAL 20 MINUTE as `fetch_match`
                FROM summoners
                WHERE
                  region={}
                  AND searchable_name={}
                  AND last_update_datetime > UTC_TIMESTAMP() - INTERVAL 7 DAY
            """.format(
            region_escaped,
            database.escape(summoner_name_searchable),
        ))
        if summoner:
            summoner_id = summoner['id']
            fetch_match = summoner['fetch_match']

        # ---------------------------------------------------- #
        # Fetch User if needed
        # ---------------------------------------------------- #

        if not summoner_id:
            try:
                response = request(API_URL_SUMMONER_SEARCH, region, summonerName=summoner_name_searchable)
                if response is None:
                    raise Exception("BUTTMAD LEVELS RISING")

                summoner_id = response.values()[0]['id']
            except:
                abort(404, message="Summoner not found")

        # ---------------------------------------------------- #
        # Fetch Match if needed
        # ---------------------------------------------------- #

        match_id = None
        if fetch_match:
            recent_matches = request(API_URL_MATCH_HISTORY, region, summonerId=summoner_id, beginIndex=0, endIndex=15).get('matches', [])

            for _match in recent_matches:
                if _match['season'] == SEASON_NAME:
                    match_id = _match['matchId']

            if match_id is None:
                abort(404, message="Recent game not found")



            match_exists = database.fetch_one_value("""
                SELECT
                    1
                FROM
                    `matches`
                WHERE
                    match_region = {}
                    AND match_id = {}
            """.format(region_escaped, match_id))
            if not match_exists:
                response = request(API_URL_MATCH, region, matchId=match_id, includeTimeline=True)

                if not response:
                    abort(404, message="Match not found")

                match_stats = match.get_stats(response)

                if not match_stats:
                    abort(404, message="Match stats unavailable")

                # ---------------------------------------------------- #
                # Get Match Stats
                # ---------------------------------------------------- #

                player_stats = player.get_stats([match_stats], database)

                try:
                    match.insert(match_stats, player_stats, database)
                    player.insert(player_stats, database, summoner_id)
                except Exception, e:
                    abort(404, message="Cannot insert match into database: {}".format(e))
        else:
            match_id = database.fetch_one_value("""
                SELECT
                    match_id
                FROM
                    `matches`
                WHERE
                    match_region = {}
                    AND summoner_id = {}
                ORDER BY match_create_datetime DESC
                LIMIT 1
            """.format(region_escaped, summoner_id))

            if not match_id:
                abort(404, message="Cached match is missing, try again in 20 minutes")


        # ---------------------------------------------------- #
        # Fetch Match IDs
        # ---------------------------------------------------- #

        # Find match IDs that have not been touched yet
        # And are in this season
        match_ids_to_fetch = []
        response = request(API_URL_MATCH_HISTORY, region, summonerId=summoner_id, beginIndex=0, endIndex=15)
        if not response:
            abort(404, 'No matches found')

        recent_matches = response.get('matches', [])
        recent_matches.reverse() # reverse since results are backwards
        match_history_index = {}
        match_ids = []
        for _match in recent_matches:
            if _match['season'] == SEASON_NAME:
                match_ids.append(_match['matchId'])
                match_history_index[_match['matchId']] = {
                    'region': _match['region'],
                    'platformId': _match['platformId'],
                }
        match_ids = match_ids[:3]
        match_id_strs = [str(match_id) for match_id in match_ids]

        # if we found no matches this season, BAIL
        if not match_ids:
            abort(404, 'No matches found (after filtering)')

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

        # ---------------------------------------------------- #
        # Fetch Matches
        # ---------------------------------------------------- #

        if match_ids_to_fetch:
            match_requests = []
            for match_id in match_ids_to_fetch:
                match_requests.append((match_id, Request(API_URL_MATCH, region, matchId=match_id, includeTimeline=True)))

            match_stats = []
            for match_id, match_request in match_requests:
                _match = match_request.response()
                if not _match or not 'timeline' in _match:
                    continue

                match_stats.append(match.get_stats(_match))

                if match_stats:
                    player_stats = player.get_stats(match_stats, database)
                    player.insert(player_stats, database, summoner_id)

                    for match_stat in match_stats:
                        try:
                            match.insert(match_stat, player_stats, database)
                        except Exception, e:
                            pass




        # ---------------------------------------------------- #
        # Pull Game
        # ---------------------------------------------------- #

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
                                q1.summoner_assists,
                                q1.summoner_deaths,
                                q1.summoner_kills,

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
                                    summoner_assists,
                                    summoner_deaths,
                                    summoner_kills_total as summoner_kills,
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
                        INNER JOIN aggregate_freelo_deviations afd ON afd.champion_role = q1.role
                            AND afd.champion_id = q1.summoner_champion_id
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
                region=region_escaped,
                summoner_id=summoner_id,
            ))

            # due to the ordering, the current player is either 1st or 5th
            # if the current player isn't 1st, then swap the last 5 with the first 5
            if player_game_data[0]['summoner_id'] != summoner_id:
                player_game_data = player_game_data[5:] + player_game_data[:5]

            # ---------------------------------------------------- #
            # Predefine Stats
            # ---------------------------------------------------- #

            stats = {
                'id': match_id,
                'game_id': match_id,
                'create_datetime': player_game_data[0]['match_create_datetime'].isoformat(),
                'match_total_time_in_minutes': player_game_data[0]['match_total_time_in_minutes'],
                'current_player_team_red': player_game_data[0]['summoner_team_id'] == 200,
                'current_player_won': player_game_data[0]['summoner_is_winner'] == 1,
                'match_history_url': 'http://matchhistory.{}.leagueoflegends.com/en/#match-details/{}/{}/{}'.format(match_history_index[match_id]['region'], match_history_index[match_id]['platformId'], match_id, summoner_id),
                'players': [],
                'key_factors': [
                    {
                        'id': 'overall',
                        'name': 'Overall',
                        'totals': [],
                        'sets': [],
                    },
                    {
                        'id': 'cs',
                        'name': 'CS',
                        'totals': [],
                        'sets': [],
                    },
                    {
                        'id': 'wards_vision',
                        'name': 'Vision Wards',
                        'totals': [],
                        'sets': [],
                    },
                    {
                        'id': 'assists',
                        'name': 'Assists',
                        'totals': [],
                        'sets': [],
                    },
                    {
                        'id': 'deaths',
                        'name': 'Deaths',
                        'totals': [],
                        'sets': [],
                    },
                    {
                        'id': 'kills',
                        'name': 'Kills',
                        'totals': [],
                        'sets': [],
                    },
                    {
                        'id': 'wards_sight',
                        'name': 'Sight Wards',
                        'totals': [],
                        'sets': [],
                    },
                    {
                        'id': 'first_dragon',
                        'name': 'First Dragon',
                        'totals': [],
                        'sets': [],
                    },
                    {
                        'id': 'match_time',
                        'name': 'Game Length',
                        'totals': [],
                        'sets': [],
                    },
                    {
                        'id': 'damage_done_to_champions',
                        'name': 'Damage to Champions',
                        'totals': [],
                        'sets': [],
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
                    'summoner_kills': player_game['summoner_kills'],
                    'summoner_deaths': player_game['summoner_deaths'],
                    'summoner_assists': player_game['summoner_assists'],
                    'summoner_minions_killed': player_game['summoner_minions_killed'],
                })

                rank_id = player_game['summoner_rank_tier_id'] or average_rank
                def get_diffed_rank(offset):
                    diffed_rank = rank_id + int(offset)

                    if diffed_rank > RANK_MAX:
                        return 'GOD'
                    elif diffed_rank < 1:
                        return 'WOOD'
                    else:
                        return RANK_ID_TO_NAME[diffed_rank]

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

        return {'stats':stats_combined}


api.add_resource(Stats, '/1.0/stats')
