App.Match = DS.Model.extend({
    create_datetime: DS.attr(),
    match_total_time_in_minutes: DS.attr(),
    player: DS.attr(),
    stats: DS.attr(),
    stats_showing: DS.attr()
});

App.MatchesController = Ember.ArrayController.extend({
    needs: ['summonerSearch'],
    actions: {
        show_more: function() {
            this.fetch_more_matches();
        }
    },
    fetch_match_stats: function(match) {
        var self = this,
            region = this.get('region'),
            summoner_name = this.get('summoner_name'),
            aggregate_analysis = this.get('aggregate_analysis');

        match.set('loading_stats', true);

        jQuery.getJSON('/api/1.0/matches/'+match.get('match_id')+'/stats?region='+region+'&summoner_name='+summoner_name).done(function(resp) {
            match.set('stats', resp.stats);
            match.set('loading_stats', false);

            var key_factors = resp.stats['key_factors'],
                league_name = key_factors[0]['totals'][0]['name'].toLowerCase();

            // update overall league counts
            aggregate_analysis.incrementProperty('overall_league_counts.'+league_name);

            // update highlights
            self.update_highlights(key_factors);

            // update games loading and loaded count
            aggregate_analysis.decrementProperty('games_loading');
            aggregate_analysis.incrementProperty('games_loaded');
        }).fail(function(resp) {
            match.set('loading_stats', false);
        });
    },
    update_highlights: function(key_factors) {
        var aggregate_analysis = this.get('aggregate_analysis');

        var ignore_key_factors = ['Overall', 'First Dragon'];
        for(var i=0, n=key_factors.length; i<n; ++i) {
            var key_factor_name = key_factors[i]['name'],
                league_id = key_factors[i]['totals'][0]['id'];

            // skip those we are ignoring
            if(ignore_key_factors.indexOf(key_factor_name) != -1) continue;

            // adjust offset total for key factor
            if(typeof aggregate_analysis.get('highlights.key_factor_league_id_totals.'+key_factor_name) == 'undefined') {
                aggregate_analysis.set('highlights.key_factor_league_id_totals.'+key_factor_name, 0);
            }
            aggregate_analysis.incrementProperty('highlights.key_factor_league_id_totals.'+key_factor_name, parseInt(league_id, 10));

            // set best key factor
            if(aggregate_analysis.get('highlights.key_factor_league_id_totals.'+key_factor_name) > aggregate_analysis.get('highlights.best_key_factor.value') || aggregate_analysis.get('highlights.best_key_factor.name') == key_factor_name) {
                aggregate_analysis.set('highlights.best_key_factor.name', key_factor_name);
                aggregate_analysis.set('highlights.best_key_factor.value', parseInt(aggregate_analysis.get('highlights.key_factor_league_id_totals.'+key_factor_name), 10));

            }

            // set worst key factor
            if(aggregate_analysis.get('highlights.key_factor_league_id_totals.'+key_factor_name) < aggregate_analysis.get('highlights.worst_key_factor.value') || aggregate_analysis.get('highlights.worst_key_factor.name') == key_factor_name) {
                aggregate_analysis.set('highlights.worst_key_factor.name', key_factor_name);
                aggregate_analysis.set('highlights.worst_key_factor.value', aggregate_analysis.get('highlights.key_factor_league_id_totals.'+key_factor_name));
            }
        }
    },
    fetch_more_matches: function() {
        var self = this,
            region = this.get('region'),
            summoner_name = this.get('summoner_name'),
            page = this.get('page') + 1,
            aggregate_analysis = this.get('aggregate_analysis');

        this.set('page', page);
        this.set('loading_more', true);

        // when loading past the 1st page, we are "loading more"
        if(page > 1) {
            this.set('loading_more', true);
        }

        return jQuery.getJSON('/api/1.0/matches?region='+region+'&summoner_name='+summoner_name+'&page='+page).done(function(resp) {
            var new_matches = [];
            var matches_needing_stats = [];
            for(var i=0, n=resp.matches.length; i<n; ++i) {
                var new_match = self.store.createRecord('match', resp.matches[i]);

                // record which matches to pull stats for
                if(!new_match.get('stats')) {
                    matches_needing_stats.push(new_match);
                }
                else {
                    var key_factors = new_match.get('stats.key_factors'),
                        league_name = key_factors[0]['totals'][0]['name'].toLowerCase();

                    // update overall league counts
                    aggregate_analysis.incrementProperty('overall_league_counts.'+league_name);

                    // update highlights
                    self.update_highlights(key_factors);
                }

                new_matches.push(new_match);
            }

            var matches = self.get('matches');
            self.set('matches', matches.concat(new_matches));
            self.set('loading', false);
            self.set('loading_more', false);

            // update games loaded and loading count
            aggregate_analysis.incrementProperty('games_loaded', new_matches.length - matches_needing_stats.length);
            aggregate_analysis.incrementProperty('games_loading', matches_needing_stats.length);
            aggregate_analysis.incrementProperty('games_total', new_matches.length);

            // get stats for matches that need them
            for(var i=0, n=matches_needing_stats.length; i<n; ++i) {
                self.fetch_match_stats(matches_needing_stats[i]);
            }
        }).fail(function(resp) {
            // show error
            if(isset(resp, 'responseJSON', 'error_key')) {
                var error_key = resp.responseJSON.error_key;
                if(page > 1 && error_key == 'NO_MATCHES_FOUND') {
                    self.set('no_more_matches', true);
                }
                else {
                    self.set('error', get_error(resp.responseJSON.error_key));
                }
                self.set('loading', false);
                self.set('loading_more', false);
            }
        });
    }
});

App.MatchesRoute = Ember.Route.extend({
    beforeModel: function() {
        // enable the summoner search in the header
        this.controllerFor('application').set('header_summoner_search', true);
    },
    setupController: function(controller, model) {

    },
    afterModel: function() {

    },
    model: function(params) {
        var self = this,
            controller = this.controllerFor('matches');

        var summonerSearchController = self.controllerFor('summonerSearch');
        summonerSearchController.set('summoner_name', params.summoner_name);
        summonerSearchController.set('region', params.region);

        controller.set('error', false);
        controller.set('loading', true);
        controller.set('region', params.region);
        controller.set('summoner_name', params.summoner_name);
        controller.set('page', 0);
        controller.set('matches', []);
        this.store.unloadAll('match');

        controller.set('aggregate_analysis', Ember.Object.extend({
            'games_loaded': 0,
            'games_loading': 0,
            'games_total': 0,
            'overall_league_counts': {
                'wood': 0,
                'bronze': 0,
                'silver': 0,
                'gold': 0,
                'platinum': 0,
                'diamond': 0,
                'master': 0,
                'challenger': 0,
                'god': 0
            },
            'highlights': {
                'key_factor_league_id_totals': {},
                'best_key_factor': {'name': '', 'value': -999},
                'worst_key_factor': {'name': '', 'value': 999}
            }
        }).create());

        controller.fetch_more_matches();
    }
});

$(function() {
    function expand_group_td($group_td) {
        var $tr = $group_td.parent('tr'),
            $table = $($group_td.parents('.table-stats')[0]);

        var $next_trs = $($group_td.parents('tr')[0]).nextAll(),
            row_span = 1;
        for(var i=0, n=$next_trs.length; i<=n; ++i) {
            var $next_tr = $($next_trs[i]);

            // stop after a non-expandable is hit
            if(!$next_tr.hasClass('expandable')) {
                break;
            }

            $next_tr.addClass('expand');
            $('td.expandable', $next_tr).addClass('expand');
            ++row_span;
        }
        $('td.expandable', $tr).addClass('expand');

        $group_td.addClass('expanded');
        $group_td.attr('rowspan', row_span);

        update_expand_all($table);
    }

    function collapse_group_td($group_td) {
        var $tr = $group_td.parent('tr'),
            $table = $group_td.parents('.table-stats');

        var $expandable_trs = $group_td.parents('tr').nextAll();
        for(var i=0; i<=2; ++i) {
            $($expandable_trs[i]).removeClass('expand');
            $('td.expandable', $expandable_trs[i]).removeClass('expand');
        }
        $('td.expandable', $tr).removeClass('expand');

        $group_td.removeClass('expanded');
        $group_td.attr('rowspan', 1);

        update_expand_all($table);
    }

    function update_expand_all($table) {
        var expanded_count = $('td.group.expanded', $table).length;
        if(expanded_count) {
            $('.expand-all i', $table).removeClass('fa-plus-square-o');
            $('.expand-all i', $table).addClass('fa-minus-square-o');
        }
        else {
            $('.expand-all i', $table).addClass('fa-plus-square-o');
            $('.expand-all i', $table).removeClass('fa-minus-square-o');
        }
    }

    function toggle_group_td($group_td) {
        var expanded = $group_td.hasClass('expanded');

        if(!expanded) {
            expand_group_td($group_td);
        }
        else {
            collapse_group_td($group_td);
        }
    }

    $(document).on('click', '.expand-all', function(e) {
        var $expand_all = $(this),
            $icon = $('i', $expand_all),
            $table = $($expand_all.parents('.table-stats')[0]);

        if($icon.hasClass('fa-plus-square-o')) {
            $('td.group', $table).each(function(i, group_td) {
                expand_group_td($(group_td));
            });
        }
        else {
            $('td.group', $table).each(function(i, group_td) {
                collapse_group_td($(group_td));
            });
        }
    });

    $(document).on('click', 'td.group', function(e) {
        toggle_group_td($(e.target));
    });
});