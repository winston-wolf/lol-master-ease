App = Ember.Application.create();

var REGIONS = ['BR','EUNE','EUW','KR','LAN','LAS','NA','OCE','RU','TR'],
    DEFAULT_REGION = 'NA';

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

// player info
App.PlayerInfoComponent = Ember.Component.extend({
    tooltipActivate: function() {
        this.$('[data-toggle="tooltip"]').tooltip({
            html: true
        });
    }.on('didInsertElement')
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

        controller.transitionToRoute('stats', region, summoner_name);
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