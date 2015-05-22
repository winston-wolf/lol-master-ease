App.IndexRoute = Ember.Route.extend({
    beforeModel: function(transition) {
        // disable the summoner search in the header
        this.controllerFor('application').set('header_summoner_search', false);
    },
    setupController: function(controller, model) {
        controller.generated_slogan = controller.slogans[Math.floor(Math.random()*controller.slogans.length)]
    }
});

App.IndexController = Ember.Controller.extend({
    needs: ['summonerSearch'],
    slogans: [
        'Stop feeding, today!',
        'Tips so good, you\'ll swear it\'s elo boosting.',
        'Find out why you suck.',
        'So simple. No skill involved at all.',
        'Master yourself, master your elo.',
        'The first rule of LoL is "don\'t die".',
        'The second rule of LoL is "don\'t die"!',
        'We\'ll turn your challenjour into challenger.'
    ]
});