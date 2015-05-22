from flask import Flask, Blueprint, send_file

front_end_app = Blueprint('front_end_app', __name__,
                          static_url_path='/front_end',
                          static_folder='static',
                          template_folder='templates')


@front_end_app.route('/')
def index():
    return send_file('front_end/templates/index.html', cache_timeout=600)

@front_end_app.route('/<path:path>')
def catch_all(path):
    return send_file('front_end/templates/index.html', cache_timeout=600)