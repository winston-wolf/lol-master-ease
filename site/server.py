# +----------------------------------------------------------------------+
# | Copyright (c) 2015 Winston Wolf                                      |
# +----------------------------------------------------------------------+
# | This source file is bound by United States copyright law.            |
# +----------------------------------------------------------------------+
# | Author: Winston Wolf <winston.the.cleaner@gmail.com>                 |
# +----------------------------------------------------------------------+

# ---------------------------------------------------- #
# Include shared code
# ---------------------------------------------------- #

import os
import sys

sys.path.append("{}/../".format(os.path.dirname(os.path.realpath(__file__))))

# ---------------------------------------------------- #
# App
# ---------------------------------------------------- #

DEBUG = True

from flask import Flask
from front_end.views import front_end_app
from api.views import api_app
from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop

app = Flask(__name__)
app.config.update()

app.register_blueprint(front_end_app)
app.register_blueprint(api_app)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80)

    http_server = HTTPServer(WSGIContainer(app))
    http_server.bind(port=80, address='0.0.0.0')
    http_server.start(num_processes=8)

    IOLoop.instance().start()