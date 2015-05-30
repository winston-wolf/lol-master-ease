App.Stat = DS.Model.extend({
    game_id: DS.attr(),
    current_player_team_red: DS.attr(),
    current_player_won: DS.attr(),
    match_total_time_in_minutes: DS.attr(),
    create_datetime: DS.attr(),
    match_history_url: DS.attr(),
    players: DS.attr(),
    key_factors: DS.attr()
});

App.StatsController = Ember.ArrayController.extend({
    needs: ['summonerSearch'],
    actions: {
        show_more: function() {
            this.fetch_more_stats();
        }
    },
    fetch_more_stats: function() {
        var self = this,
            region = this.get('region'),
            summoner_name = this.get('summoner_name'),
            page = this.get('page') + 1;

        this.set('page', page);
        this.set('loading_more', true);

        // when loading past the 1st page, we are "loading more"
        if(page > 1) {
            this.set('loading_more', true);
        }

        return jQuery.getJSON('/api/1.0/stats?region='+region+'&summoner_name='+summoner_name+'&page='+page).done(function(resp) {
            var stats = self.get('stats');
            self.set('stats', stats.concat(resp.stats));
            self.set('loading', false);
            self.set('loading_more', false);
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

App.StatsRoute = Ember.Route.extend({
    beforeModel: function() {
        // enable the summoner search in the header
        this.controllerFor('application').set('header_summoner_search', true);
        console.log('stats -- before model');
        console.log('loading = ', this.controllerFor('stats').get('loading'))
    },
    setupController: function(controller, model) {
        console.log('stats -- setupController')
    },
    afterModel: function() {
        console.log('stats -- after model');
    },
    model: function(params) {
        console.log('stats -- model');

        var self = this,
            controller = this.controllerFor('stats');

        var summonerSearchController = self.controllerFor('summonerSearch');
        summonerSearchController.set('summoner_name', params.summoner_name);
        summonerSearchController.set('region', params.region);

        controller.set('error', false);
        controller.set('loading', true);
        controller.set('region', params.region);
        controller.set('summoner_name', params.summoner_name);
        controller.set('page', 0);
        controller.set('stats', []);
        controller.fetch_more_stats();
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