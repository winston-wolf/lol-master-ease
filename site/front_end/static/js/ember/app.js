Ember.deprecate = function(){};
App = Ember.Application.create();

var REGIONS = ['BR','EUNE','EUW','KR','LAN','LAS','NA','OCE','RU','TR'],
    LEAGUES = ['UNRANKED','BRONZE','SILVER','GOLD','PLATINUM','DIAMOND','MASTER','CHALLENGER'],
    DEFAULT_REGION = 'NA',
    ERROR_INDEX = {
        'SUMMONER_NOT_FOUND': {
            'message': 'We couldn\'t find the summoner you are looking for.',
            'tips': ['Misspelled summoner name?', 'Is the region right?', 'Did you fat finger something?', 'Maybe they don\'t exist.']
        },
        'NO_MATCHES_FOUND': {
            'message': 'No matches found for this summoner.',
            'tips': ['Maybe they should play more.', 'Have they played solo queue this season?', 'Do they even LoL?', 'Looks like they could use a duo partner.']
        }
    },
    TIPS = {
        'CS': 'Try practicing last hitting in a custom game or find a guide on minion control/jungle paths. This is THE most important factor in winning. If you are in a lane, try grabbing jungle camps after pushing to the enemy turret. Just don\'t steal from your jungler! Even as support try to pick up CS your partner can\'t get to.',
        'Vision Wards': 'Try and keep a vision ward on the map at all times, even if you just put it into a bush in your jungle. If you are support and doing well, don\'t be afraid to carry more than 1 pink so you are ready for any situation.',
        'Assists': 'Unless you got tons of kills or are a split pushing monster, you probably aren\'t participating in team fights enough. A good team is one where players anticipate and respond quickly to threats and opportunities. Look out for pings, keep an eye on your minimap, and avoid tunnel vision.',
        'Deaths': 'First rule of LoL, don\'t die. Second rule, DON\'T DIE! Pull back on that aggression cowboy. 1 kill for 1 death is rarely #worthit. Playing safe when outmatched or countered will win you more games than going HAM when you are behind. If a teammate is clearly going to die, don\'t feel like you have to jump in and die as well.',
        'Kills': 'Don\'t be afraid to be a little more aggressive and secure kills.  Try flash initiating more and make sure you know damage spikes and matchups with your champions.',
        'Sight Wards': 'If you\'re leaving base with 75g and an open inventory slot you are doing it wrong.  Every bit of vision counts and a sight ward can easily net you another 2 CS safely. If a ward saves you from a gank its already paid for 6 wards!',
        'Damage to Champions': 'Don\'t hang so far back in the fights.  Autoattacks matter even on support.  Every second you have a spell on CD or are out of range you\'re losing DPS.  In lane, make sure you aren\'t taking harass for free. Be more patient on skillshots to make sure they land. 1 that hits is better than 5 that miss!'
    };

function get_error(error_key) {
    var error = ERROR_INDEX[error_key];
    return {
        'message': error.message,
        'tip': error.tips[Math.floor(Math.random()*error.tips.length)]
    };
}

App.ApplicationRoute = Ember.Route.extend({
    model: function() {
//        return {
//            summoner_name: localStorage.getItem('summoner_name'),
//            region: localStorage.getItem('region') || DEFAULT_REGION
//        };
    },
    setupController: function(controller, model) {
        controller.current_year = (new Date()).getFullYear();
    }
});

App.ApplicationController = Ember.Controller.extend({
    needs: ['summonerSearch'],
    header_summoner_search: true
});

App.ApplicationAdapter = DS.RESTAdapter.extend({
    namespace: 'api/1.0'
});

// highlights and tips
App.HighlightsAndTipsComponent = Ember.Component.extend({
    classNames: [''],
    blah: function() {
        var aggregate_analysis = this.get('aggregate_analysis'),
            games_loaded = aggregate_analysis['games_loaded'],
            best_key_factor = aggregate_analysis['highlights']['best_key_factor'],
            best_league_id = Math.round(best_key_factor['value'] / games_loaded),
            best_league_name = LEAGUES[best_league_id],
            worst_key_factor = aggregate_analysis['highlights']['worst_key_factor'],
            worst_league_id = Math.round(worst_key_factor['value'] / games_loaded),
            worst_league_name = LEAGUES[worst_league_id],
            worst_league_tip = TIPS[worst_key_factor['name']];

        this.set('best_league_name', best_league_name);
        this.set('best_key_factor_name', best_key_factor['name']);
        this.set('worst_league_name', worst_league_name);
        this.set('worst_key_factor_name', worst_key_factor['name']);
        this.set('worst_league_tip', worst_league_tip);
    }.on('willInsertElement')
});

// summoner champion
App.SummonerChampionComponent = Ember.Component.extend({
    classNames: ['summoner-champion']
});

// summoner spell book
App.SummonerSpellBookComponent = Ember.Component.extend({
    classNames: ['summoner-spell-book']
});

// summoner name
App.SummonerNameComponent = Ember.Component.extend({
    classNames: ['summoner-name']
});

// summoner stats
App.SummonerStatsComponent = Ember.Component.extend({
    classNames: ['summoner-stats'],
    activatePopovers: function() {
        this.$('.stat-minions').popover({
            trigger: 'hover',
            placement: 'top',
            html: true,
            content: '' +
                '<div class="popover-nowrap">' +
                    'Minions: '+this.get('player.summoner_minions_killed')+'<br />' +
                    'Jungle: '+this.get('player.summoner_neutral_minions_killed') +
                '</div>'
        });
    }.on('didInsertElement'),
    championIdsObserver: function() {
        console.log('change?')
    }.observes('champion_ids')
});

// summoner items
App.SummonerItemsComponent = Ember.Component.extend({
    classNames: ['summoner-items']
});

// summoner item
App.SummonerItemComponent = Ember.Component.extend({
    classNames: ['summoner-item']
});

// league decorator
App.LeagueDecoratorComponent = Ember.Component.extend({
    classNames: ['league-decorator'],
    setOffsetValues: function() {
        var league = this.get('league'),
            offset = league.offset,
            offset_icon_class = '',
            offset_class = 'played-normal';

        if(league.name == 'unranked') {
            offset = '?';
        }
        else {
            if(offset > 0) {
                offset_icon_class = 'sort-asc';
                offset_class = 'played-up';
            }
            else if(offset < 0) {
                offset_icon_class = 'sort-desc';
                offset_class = 'played-down';
            }

            offset = Math.abs(offset);
        }

        this.set('offset_icon_class', offset_icon_class);
        this.set('offset_class', offset_class);
        this.set('offset', offset);
    }.on('willInsertElement')
});

// champion filter
var champions_json_promise = $.getJSON('/front_end/data/champions.json');
App.ChampionFilterComponent = Ember.Component.extend({
    setup: function() {
        var self = this;

        champions_json_promise.done(function(champions) {
            var $menu = $(self.element).find('.menu');

            // add 'none' option to menu
            $menu.append('<div class="item" data-value="">All</div>');

            $.each(champions, function(champion_index, champion) {
                $menu.append('<div class="item" data-value="'+champion['id']+'"><img src="'+champion['image_icon_url']+'" /> '+champion['name']+'</div>');
            });

            var $dropdown = $(self.element).find('.ui.dropdown');
            $dropdown.dropdown();
        })
    }.on('didInsertElement')
});

// toggle match stats view
App.ToggleMatchStatsView = Ember.View.extend({
    click: function(e) {
        if(e.target.tagName == 'A') {
            return true;
        }
        else {
            var match = this.get('match');
            if(match.get('stats')) {
                if(match.get('stats_showing')) {
                    match.set('stats_showing', false);
                }
                else {
                    match.set('stats_showing', true);
                }
            }
        }
    }
});

// summoner search
App.SummonerSearchController = Ember.Controller.extend({
    regions: REGIONS,
    summoner_name: localStorage.getItem('summoner_name'),
    region: localStorage.getItem('region') || DEFAULT_REGION
});

App.SummonerSearchView = Ember.View.extend({
    tagName: 'form',
    templateName: 'summoner-search',
    classNames: ['form-inline'],

    submit: function(e) {
        e.preventDefault();

        var controller = this.get('controller.controllers.summonerSearch'),
            summoner_name = controller.get('summoner_name').trim(),
            region = controller.get('region');

        controller.transitionToRoute('matches', region, summoner_name);
    }
});

App.RegionDropdownView = Ember.View.extend({
    tagName: 'div',
    templateName: 'region-dropdown',
    classNames: ['input-group-btn']
});

App.RegionItemView = Ember.View.extend({
    tagName: 'a',
    attributeBindings: ['href'],
    href: '#',

    click: function() {
        this.get('controller.controllers.summonerSearch').set('region', this.get('region'));
    }
});

// handlebars helpers
Ember.Handlebars.registerBoundHelper('player_classes', function(current_player_team_red, options) {
    var index = options.hash.index,
        classes = [];

    if(index == 0) {
        classes.push('current-player');
    }

    // if same as current player (player 2-5)
    if((index < 5 && current_player_team_red) || (index >= 5 && !current_player_team_red)) {
        classes.push('team-red');
    }
    else {
        classes.push('team-blue');
    }

    return classes.join(' ');
});

Ember.Handlebars.registerBoundHelper('lowercase', function(str) {
    return str.toString().toLowerCase();
});

Ember.Handlebars.registerBoundHelper('uppercase', function(str) {
    return str.toString().toUpperCase();
});

Ember.Handlebars.registerHelper('ucwords', function(str) {
    str = str.toString().toLowerCase();
    return (str + '').replace(/^([a-z\u00E0-\u00FC])|\s+([a-z\u00E0-\u00FC])/g, function($1) {
        return $1.toUpperCase();
    });
});

Ember.Handlebars.registerBoundHelper('humandate', function(date_str) {
    var date = new Date(date_str);
    return (date.getMonth() + 1) + '/' + date.getDate() + '/' + date.getFullYear();
});

Ember.Handlebars.registerBoundHelper('percent', function(sum, options) {
    var total = options['hash']['total'];
    return (total == 0) ? 0 : (sum * 100 / total).toFixed(0);
});

Ember.Handlebars.registerBoundHelper('percent_width', function(sum, options) {
    var total = options['hash']['total'],
        percent = (10 + (total == 0 ? 0 : sum * 100 / total)) * .9;
    return percent.toFixed(0);
});

Ember.Handlebars.registerBoundHelper('pluralize', function(word, options) {
    var value = options['hash']['value'];

    // a value of one does not get pluralized
    if(value != 1) {
        var ending_letter = word.slice(-1);
        if(ending_letter == 'y') {
            word = word.slice(0, -1) + 'ies';
        }
        else {
            word = word + 's';
        }
    }

    return  word;
});