App.Router.reopen({
    location: 'auto'
});

App.Router.map(function() {
    this.resource('index', { path: '/' });
    this.resource('matches', { path: '/summoner/:region/:summoner_name' });
});