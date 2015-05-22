App.Router.reopen({
    location: 'auto'
});

App.Router.map(function() {
    this.resource('index', { path: '/' });
    this.resource('stats', { path: '/summoner/:region/:summoner_name' });
});