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
    needs: ['summonerSearch']
});

App.StatsRoute = Ember.Route.extend({
    beforeModel: function() {
        // enable the summoner search in the header
        this.controllerFor('application').set('header_summoner_search', true);
    },
    setupController: function(controller, model) {
        controller.set('stats', model);
    },
    model: function(params) {
        var self = this,
            controller = this.controllerFor('stats');

        var summonerSearchController = self.controllerFor('summonerSearch');
        summonerSearchController.set('summoner_name', params.summoner_name);
        summonerSearchController.set('region', params.region);

        return self.store.find('stat', { region: params.region, summoner_name: params.summoner_name }).then(function(resp) {
            localStorage.setItem('region', params.region);
            localStorage.setItem('summoner_name', params.summoner_name);

            controller.set('region', params.region);
            controller.set('summoner_name', params.summoner_name);

            return resp;
        }, function() {
            console.log('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!');
        });
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