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

import logging
from flask import Flask
from front_end.views import front_end_app
from api.views import api_app

app = Flask(__name__)
app.config.update()

app.register_blueprint(front_end_app)
app.register_blueprint(api_app)

# ---------------------------------------------------- #
# Error Messages
# ---------------------------------------------------- #

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.ERROR)
logger = logging.getLogger('freelo')
def log_exception(sender, exception, **extra):
    logger.error(exception)

from flask import got_request_exception
got_request_exception.connect(log_exception, app)

# ---------------------------------------------------- #
# Start
# ---------------------------------------------------- #

if __name__ == "__main__":
#    handler = logging.handlers.RotatingFileHandler('/var/log/freelo/error.log', maxBytes=10000, backupCount=1)
#    handler.setLevel(logging.ERROR)
#    app.logger.addHandler(handler)

    app.run(port=8000)
