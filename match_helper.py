# +----------------------------------------------------------------------+
# | Copyright (c) 2015 Winston Wolf                                      |
# +----------------------------------------------------------------------+
# | This source file is bound by United States copyright law.            |
# +----------------------------------------------------------------------+
# | Author: Winston Wolf <winston.the.cleaner@gmail.com>                 |
# +----------------------------------------------------------------------+

from datetime import datetime
import logging

from settings import ITEM_TRINKET_PINK, ITEM_TRINKET_UPGRADES, MATCH_DELTA_TIMES

ITEM_TRINKET_UPGRADES_DICT = { _id: True for _id in ITEM_TRINKET_UPGRADES }

logger = logging.getLogger('freelo')

def get_stats(match, detailed=False):
    match_total_time_in_minutes = int(float(match['matchDuration'])/60)
    match_stats = {
        "id": match['matchId'],
        "region": match['region'].lower(),
        "platform": match['platformId'],
        "season": match['season'],
        "queue_type": match['queueType'],
        "total_time_in_minutes": match_total_time_in_minutes,
        "create_datetime": datetime.fromtimestamp(int(match['matchCreation']/1000))
    }

    delta_frames = []
    participant_stats = {}
    players_dict = {participant['participantId']: participant['player'] for participant in match.get('participantIdentities', [])}

    for participant in match.get('participants', []):
        _participant_stats = participant['stats']
        participant_timeline = participant['timeline']
        participant_id = participant['participantId']
        participant_identity = players_dict[participant_id]
        summoner_id = participant_identity['summonerId']

        participant_stats[participant_id] = {
            'id': summoner_id,
            'name': participant_identity['summonerName'],
            'rank_tier_last': participant['highestAchievedSeasonTier'],
            'team_id': participant['teamId'],
            'role': participant_timeline['role'],
            'lane': participant_timeline['lane'],
            'champion_id': participant['championId'],
            'champion_level': _participant_stats['champLevel'],
            'spell_1_id': participant['spell1Id'],
            'spell_2_id': participant['spell2Id'],
            'item_0_id': _participant_stats['item0'],
            'item_1_id': _participant_stats['item1'],
            'item_2_id': _participant_stats['item2'],
            'item_3_id': _participant_stats['item3'],
            'item_4_id': _participant_stats['item4'],
            'item_5_id': _participant_stats['item5'],
            'item_6_id': _participant_stats['item6'],
            'is_winner': _participant_stats['winner'],
            'kills_total': _participant_stats['kills'],
            'kills_double': _participant_stats['doubleKills'],
            'kills_triple': _participant_stats['tripleKills'],
            'kills_quadra': _participant_stats['quadraKills'],
            'kills_penta': _participant_stats['pentaKills'],
            'killing_sprees': _participant_stats['killingSprees'],
            'deaths': _participant_stats['deaths'],
            'assists': _participant_stats['assists'],
            'inhibitor_kills': _participant_stats['inhibitorKills'],
            'tower_kills': _participant_stats['towerKills'],
            'tower_kills_in_lane': _participant_stats['inhibitorKills'],
            'sight_wards_purchased': _participant_stats['sightWardsBoughtInGame'],
            'sight_wards_placed': 0,
            'sight_wards_killed': 0,
            'vision_wards_purchased': _participant_stats['visionWardsBoughtInGame'],
            'vision_wards_placed': 0,
            'vision_wards_killed': 0,
            'damage_done_to_champions': _participant_stats['totalDamageDealtToChampions'],
            'damage_taken': _participant_stats['totalDamageTaken'],
            'xp_earned': 0,
            'minions_killed': _participant_stats['minionsKilled'],
            'neutral_minions_killed_enemy_jungle': _participant_stats['neutralMinionsKilledEnemyJungle'],
            'neutral_minions_killed_team_jungle': _participant_stats['neutralMinionsKilledTeamJungle'],
            'healing_done_total': _participant_stats['totalHeal'],
            'gold_spent': _participant_stats['goldSpent'],
            'gold_earned': _participant_stats['goldEarned'],
            'crowd_control_time_dealt_in_seconds': float(_participant_stats['totalTimeCrowdControlDealt'])/1000,
            'trinket_upgraded': False,
        }

        # Some people cannot be identified
        if not 'csDiffPerMinDeltas' in participant_timeline:
            continue

        cs_diff_per_min = participant_timeline['csDiffPerMinDeltas']
        xp_diff_per_min = participant_timeline['xpDiffPerMinDeltas']
        damage_taken_diff_per_min = participant_timeline['damageTakenDiffPerMinDeltas']
        for time_name, (time_start, time_end) in MATCH_DELTA_TIMES.items():
            if not time_name in cs_diff_per_min:
                continue

            if time_end is None:
                time_end = match_total_time_in_minutes

            delta_frames.append({
                'summoner_id': summoner_id,
                'frame_start_minutes': time_start,
                'frame_end_minutes': time_end,
                'creeps_per_minute': cs_diff_per_min[time_name],
                'xp_per_minute': xp_diff_per_min[time_name],
                'damage_taken_per_minute': damage_taken_diff_per_min[time_name],
            })


    # Build team stats
    team_stats = {}
    frame_stats = []
    if detailed:
        for team in match['teams']:
            team_stats[team['teamId']] = {
                'killed_first_dragon': team['firstDragon'],
                'killed_first_baron': team['firstBaron'],
                'killed_first_tower': team['firstTower'],
                'killed_first_inhibitor': team['firstInhibitor'],
                'killed_first_champion': team['firstBlood'],
                'dragon_kills': 0,
                'baron_kills': 0,
                'sight_wards_placed': 0,
                'vision_wards_placed': 0,
                'first_dragon_kill_time_in_minutes': None,
            }

        # XP Earned
        # Get last frame and read XP from there
        for participantFrame in match['timeline']['frames'][-1]['participantFrames'].values():
            participant_id = participantFrame['participantId']
            participant_stats[participant_id]['xp_earned'] = participantFrame['xp']

        # Ward Stats / Buff Stats
        participant_has_pink_trinket = { _id: False for _id in participant_stats.keys() }
        participant_assists_total = { _id: 0 for _id in participant_stats.keys() }
        participant_deaths_total = { _id: 0 for _id in participant_stats.keys() }
        participant_kills_total = { _id: 0 for _id in participant_stats.keys() }
        vision_wards_placed_total = { _id: 0 for _id in participant_stats.keys() }
        sight_wards_placed_total = { _id: 0 for _id in participant_stats.keys() }
        for frame in match['timeline']['frames']:
            participant_assists = {}
            participant_deaths = {}
            participant_kills = {}
            vision_wards_placed = {}
            sight_wards_placed = {}

            # ---------------------------------------------------- #
            # Track Events
            # ---------------------------------------------------- #

            for event in frame.get('events', []):
                event_type = event['eventType']

                # Track if they upgraded their trinket
                if event_type == 'ITEM_PURCHASED':
                    item_id = event['itemId']
                    if item_id in ITEM_TRINKET_UPGRADES_DICT:
                        participant_stats[event['participantId']]['trinket_upgraded'] = True
                    if item_id == ITEM_TRINKET_PINK:
                        participant_has_pink_trinket[event['participantId']] = True

                # Track player has pink trinket
                elif event_type == 'ITEM_DESTROYED':
                    if event['itemId'] == ITEM_TRINKET_PINK:
                        participant_has_pink_trinket[event['participantId']] = False

                # Track Ward Kills
                elif event_type == 'WARD_KILL':
                    killer_id = event['killerId']
                    if killer_id:
                        key = 'vision_wards_killed' if event['wardType'] == "VISION_WARD" else 'sight_wards_killed'
                        participant_stats[killer_id][key] += 1

                # Track Ward Placements
                elif event_type == 'WARD_PLACED':
                    ward_type = event['wardType']

                    # Some wards are not wards...sooooo bail out
                    if ward_type == 'UNDEFINED':
                        continue

                    # Upgraded trinkets can be vision or sight, need to figure it out
                    participant_id = event['creatorId']
                    is_vision_ward = (ward_type == 'VISION_WARD' or \
                                      ward_type == 'YELLOW_TRINKET_UPGRADE' and participant_has_pink_trinket[participant_id])

                    _key = 'vision_wards_placed' if is_vision_ward else 'sight_wards_placed'
                    _participant_stats = participant_stats[participant_id]

                    _participant_stats[_key] += 1
                    team_stats[_participant_stats['team_id']][_key] += 1

                    # Store frame totals
                    if is_vision_ward:
                        if not participant_id in vision_wards_placed:
                            vision_wards_placed[participant_id] = 0

                        vision_wards_placed[participant_id] += 1
                        vision_wards_placed_total[participant_id] += 1
                    else:
                        if not participant_id in sight_wards_placed:
                            sight_wards_placed[participant_id] = 0

                        sight_wards_placed[participant_id] += 1
                        sight_wards_placed_total[participant_id] += 1

                # Champion kills
                elif event_type == 'CHAMPION_KILL':
                    killer_id = event['killerId']
                    victim_id = event['victimId']

                    # Could be a neutral kill
                    if killer_id:
                        if not killer_id in participant_kills:
                            participant_kills[killer_id] = 0

                        participant_kills[killer_id] += 1
                        participant_kills_total[killer_id] += 1

                    if not victim_id in participant_deaths:
                        participant_deaths[victim_id] = 0

                    participant_deaths[victim_id] += 1
                    participant_deaths_total[victim_id] += 1

                    for assistant_id in event.get('assistingParticipantIds', []):
                        if not assistant_id in participant_assists:
                            participant_assists[assistant_id] = 0

                        participant_assists[assistant_id] += 1
                        participant_assists_total[assistant_id] += 1

                # Buff, Dragon, Baron
                elif event_type == 'ELITE_MONSTER_KILL':
                    monster_type = event['monsterType']
                    killer_id = event['killerId']
                    if not killer_id:
                        logger.warning("Elite is kill by ??? Game: {}".format(match['matchId']))
                        continue

                    killer_team_id = participant_stats[killer_id]['team_id']
                    _team_stats = team_stats[killer_team_id]

                    if monster_type == 'DRAGON':
                        if _team_stats['first_dragon_kill_time_in_minutes'] is None:
                            _team_stats['first_dragon_kill_time_in_minutes'] = frame_start_time_in_minutes

                        _team_stats['dragon_kills'] += 1
                    elif monster_type == 'BARON_NASHOR':
                        _team_stats['baron_kills'] += 1

            # ---------------------------------------------------- #
            # Track Frame
            # ---------------------------------------------------- #

            frame_start_time_in_minutes = int(float(frame['timestamp']) / 60000)
            for participant_frame in frame['participantFrames'].values():
                participant_id = participant_frame['participantId']
                frame_stats.append({
                    'summoner_id': participant_stats[participant_id]['id'],
                    'frame_start_time_in_minutes': frame_start_time_in_minutes,
                    'xp_earned_total': participant_frame['xp'],
                    'gold_earned_total': participant_frame['totalGold'],
                    'gold_unused': participant_frame['currentGold'],
                    'deaths_total': participant_deaths_total[participant_id],
                    'deaths_this_frame': participant_deaths.get(participant_id, 0),
                    'assists_total': participant_assists_total[participant_id],
                    'assists_this_frame': participant_assists.get(participant_id, 0),
                    'kills_total': participant_kills_total[participant_id],
                    'kills_this_frame': participant_kills.get(participant_id, 0),
                    'minion_kills_total': participant_frame['minionsKilled'],
                    'jungle_minion_kills_total': participant_frame['jungleMinionsKilled'],
                    'vision_wards_placed_this_frame': vision_wards_placed.get(participant_id, 0),
                    'vision_wards_placed_total': vision_wards_placed_total[participant_id],
                    'sight_wards_placed_this_frame': sight_wards_placed.get(participant_id, 0),
                    'sight_wards_placed_total': sight_wards_placed_total[participant_id],
                })

    return {
        "match": match_stats,
        "players": participant_stats.values(),
        "frames": frame_stats,
        "deltas": delta_frames,
        "teams": team_stats,
    }


def insert(match_stats, player_stats, database, detailed=False):
    match = match_stats['match']
    match_region = database.escape(match['region'])
    match_id = match['id']

    # ---------------------------------------------------- #
    # Match Insertion
    # ---------------------------------------------------- #

    valid_summoner_insertion_data_keys = [
        'summoner_id',
        'summoner_rank_tier',
        'summoner_rank_division',
        'summoner_role',
        'summoner_lane',
        'summoner_champion_id',
        'summoner_champion_level',
        'summoner_spell_1_id',
        'summoner_spell_2_id',
        'summoner_item_0_id',
        'summoner_item_1_id',
        'summoner_item_2_id',
        'summoner_item_3_id',
        'summoner_item_4_id',
        'summoner_item_5_id',
        'summoner_item_6_id',
        'summoner_is_winner',
        'summoner_team_id',
        'summoner_kills_total',
        'summoner_kills_double',
        'summoner_kills_triple',
        'summoner_kills_quadra',
        'summoner_kills_penta',
        'summoner_killing_sprees',
        'summoner_deaths',
        'summoner_assists',
        'summoner_inhibitor_kills',
        'summoner_tower_kills',
        'summoner_tower_kills_in_lane',
        'summoner_sight_wards_purchased',
        'summoner_sight_wards_placed',
        'summoner_sight_wards_killed',
        'summoner_vision_wards_purchased',
        'summoner_vision_wards_placed',
        'summoner_vision_wards_killed',
        'summoner_damage_done_to_champions',
        'summoner_damage_taken',
        'summoner_xp_earned',
        'summoner_minions_killed',
        'summoner_neutral_minions_killed_enemy_jungle',
        'summoner_neutral_minions_killed_team_jungle',
        'summoner_healing_done_total',
        'summoner_gold_spent',
        'summoner_gold_earned',
        'summoner_crowd_control_time_dealt_in_seconds',
        'summoner_trinket_upgraded',
    ]
    valid_team_insertion_data_keys = [
        'team_first_dragon_kill_time_in_minutes',
        'team_killed_first_dragon',
        'team_killed_first_baron',
        'team_killed_first_tower',
        'team_killed_first_inhibitor',
        'team_killed_first_champion',
        'team_dragon_kills',
        'team_baron_kills',
        'team_sight_wards_placed',
        'team_vision_wards_placed',
    ]

    insertion_data = []
    for player in match_stats['players']:
        data = {}
        for stat, value in player.items():
            key = 'summoner_' + stat
            if key in valid_summoner_insertion_data_keys:
                data[key] = database.escape(value)

        if detailed:
            for stat, value in match_stats['teams'][player['team_id']].items():
                key = 'team_' + stat
                if key in valid_team_insertion_data_keys:
                    data[key] = database.escape(value)

        _player_stats = player_stats[player['id']]
        if 'summoner_rank_tier' in valid_summoner_insertion_data_keys:
            data['summoner_rank_tier'] = database.escape(_player_stats['rank_tier'])
        if 'summoner_rank_division' in valid_summoner_insertion_data_keys:
            data['summoner_rank_division'] = database.escape(_player_stats['rank_division'])

        if detailed:
            data['details_pulled'] = detailed

        data['match_id'] = match_id
        data['match_region'] = match_region
        data['match_season'] = database.escape(match['season'])
        data['match_queue_type'] = database.escape(match['queue_type'])
        data['match_total_time_in_minutes'] = match['total_time_in_minutes']
        data['match_create_datetime'] = database.escape(match['create_datetime'])

        insertion_data.append(data)

    if insertion_data:
        field_list = [u'`{}`'.format(key) for key in insertion_data[0].keys()]

        values_list = []
        for data in insertion_data:
            values_list.append(u'(' + u','.join([u'{}'.format(value) for value in data.values()]) + u')')

        sql = u"""
            INSERT INTO
                `matches` ({})
            VALUES {}
            ON DUPLICATE KEY UPDATE
                {}
        """.format(
            u','.join(field_list),
            u','.join(values_list),
            u','.join([u'{0} = VALUES({0})'.format(field) for field in field_list]),
        )

        database.execute(sql)

    if detailed and False:  # disabled match frame data from being recorded for now
        # ---------------------------------------------------- #
        # Frame Insertion
        # ---------------------------------------------------- #

        insertion_data = []
        for frame in match_stats['frames']:
            insertion_data.append(u"""
            (
                {match_id},
                {match_region},
                {summoner_id},
                {frame_start_time_in_minutes},
                {xp_earned_total},
                {gold_earned_total},
                {gold_unused},
                {deaths_total},
                {deaths_this_frame},
                {assists_total},
                {assists_this_frame},
                {kills_total},
                {kills_this_frame},
                {minion_kills_total},
                {jungle_minion_kills_total},
                {vision_wards_placed_this_frame},
                {vision_wards_placed_total},
                {sight_wards_placed_this_frame},
                {sight_wards_placed_total}
            )
            """.format(
                match_id=match_id,
                match_region=match_region,
                **frame
            ))

        insert_query = u"""
        INSERT INTO
            `match_frames`
            (
                `match_id`,
                `match_region`,
                `summoner_id`,
                `frame_start_time_in_minutes`,
                `xp_earned_total`,
                `gold_earned_total`,
                `gold_unused`,
                `deaths_total`,
                `deaths_this_frame`,
                `assists_total`,
                `assists_this_frame`,
                `kills_total`,
                `kills_this_frame`,
                `minion_kills_total`,
                `jungle_minion_kills_total`,
                `vision_wards_placed_this_frame`,
                `vision_wards_placed_total`,
                `sight_wards_placed_this_frame`,
                `sight_wards_placed_total`
            )
            VALUES {};
        """.format(u",".join(insertion_data))

        database.execute(insert_query)

        # ---------------------------------------------------- #
        # Frame Delta Insertion
        # ---------------------------------------------------- #

        insertion_data = []
        for delta in match_stats['deltas']:
            insertion_data.append(u"""
            (
                {match_id},
                {match_region},
                {summoner_id},
                {frame_start_minutes},
                {frame_end_minutes},
                {creeps_per_minute},
                {xp_per_minute},
                {damage_taken_per_minute}
            )
            """.format(
                match_id=match_id,
                match_region=match_region,
                **delta
            ))

        insert_query = u"""
        INSERT INTO
          `match_frame_delta_vs_enemy_laner`
          (
            `match_id`,
            `match_region`,
            `summoner_id`,
            `frame_start_minutes`,
            `frame_end_minutes`,
            `creeps_per_minute`,
            `xp_per_minute`,
            `damage_taken_per_minute`
          )
          VALUES {};
        """.format(u",".join(insertion_data))

        database.execute(insert_query)