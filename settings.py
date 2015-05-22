# +----------------------------------------------------------------------+
# | Copyright (c) 2015 Winston Wolf                                      |
# +----------------------------------------------------------------------+
# | This source file is bound by United States copyright law.            |
# +----------------------------------------------------------------------+
# | Author: Winston Wolf <winston.the.cleaner@gmail.com>                 |
# +----------------------------------------------------------------------+


# ---------------------------------------------------- #
# Setup
# ---------------------------------------------------- #

API_KEY = ''
DATABASE_HOST = '127.0.0.1'
DATABASE_PORT = 3306
DATABASE_USERNAME = 'root'
DATABASE_PASSWORD = ''
DATABASE_NAME = 'lol_master_ease'

# ---------------------------------------------------- #
# Pre-configured
# ---------------------------------------------------- #

API_HOST = '{region}.api.pvp.net'
API_URL_SUMMONER_SEARCH = 'https://{region}.api.pvp.net/api/lol/{region}/v1.4/summoner/by-name/{summonerName}?api_key={apiKey}'
API_URL_CHAMPIONS = 'https://global.api.pvp.net/api/lol/static-data/na/v1.2/champion?champData=image&api_key={apiKey}'
API_URL_MATCH = 'https://{region}.api.pvp.net/api/lol/{region}/v2.2/match/{matchId}?includeTimeline={includeTimeline}&api_key={apiKey}'
API_URL_MATCH_HISTORY = 'https://{region}.api.pvp.net/api/lol/{region}/v2.2/matchhistory/{summonerId}?rankedQueues=RANKED_SOLO_5x5&beginIndex={beginIndex}&endIndex={endIndex}&api_key={apiKey}'
API_URL_LEAGUES_CHALLENGER = 'https://{region}.api.pvp.net/api/lol/{region}/v2.5/league/challenger?type=RANKED_SOLO_5x5&api_key={apiKey}'
API_URL_LEAGUES_MASTER = 'https://{region}.api.pvp.net/api/lol/{region}/v2.5/league/master?type=RANKED_SOLO_5x5&api_key={apiKey}'
API_URL_LEAGUES_RANK = 'https://{region}.api.pvp.net/api/lol/{region}/v2.5/league/by-summoner/{summonerId}/entry?api_key={apiKey}'

API_REGIONS = ['br','eune','euw','kr','lan','las','na','oce','ru','tr']
RANK_TIERS = ['UNRANKED','BRONZE','SILVER','GOLD','PLATINUM','DIAMOND','MASTER','CHALLENGER']
ITEM_TRINKET_UPGRADES = [ 3361, 3362, 3363, 3364 ]
ITEM_TRINKET_PINK = 3362
MATCH_DELTA_TIMES = {
    'zeroToTen': [0, 10],
    'tenToTwenty': [10, 20],
    'twentyToThirty': [20, 30],
    'thirtyToEnd': [30, None]
}
SEASON_NAME = 'SEASON2015'
