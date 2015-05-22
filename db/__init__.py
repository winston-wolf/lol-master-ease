# +----------------------------------------------------------------------+
# | Copyright (c) 2015 Winston Wolf                                      |
# +----------------------------------------------------------------------+
# | This source file is bound by United States copyright law.            |
# +----------------------------------------------------------------------+
# | Author: Winston Wolf <winston.the.cleaner@gmail.com>                 |
# +----------------------------------------------------------------------+

import MySQLdb
import mysql as util_mysql

class Connection(object):
    cursor = None
    driver = None
    connection = None
    collection = None
    host = None
    port = None
    username = None
    password = None
    connect_timeout = None
    query_timeout = None

    def __init__(self, host, port, username, password, database=None, timeout=10, query_timeout=600.0):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.connect_timeout = timeout
        self.query_timeout = query_timeout
        self.collection = database

        super(Connection, self).__init__()

    def connect(self):
        self.close()

        self.connection = MySQLdb.connect (
            host            = self.host,
            user            = self.username,
            passwd          = self.password,
            db              = self.collection,
            charset         = 'utf8',
            connect_timeout = self.connect_timeout,
        )
        self.connection.autocommit(True)

        if not self.cursor:
            self.cursor = util_mysql.MySQLCursorWrapper(self)
        else:
            self.cursor.init(self)

        return True

    def commit(self, *args, **kwargs):
        return self.connection.commit(*args, **kwargs)

    def reconnect_if_closed(self):
        if not self.connection or not self.connection.open:
            self.connect()
            return True

        return None

    def close(self):
        if self.connection:
            try:
                return self.connection.close()
            except:
                pass

    # ---------------------------------------------------- #
    # Utility fetching functions
    # ---------------------------------------------------- #

    def fetch_all_dict(self, *args, **kwargs):
        self.cursor.execute(*args, **kwargs)
        return util_mysql.fetch_all_dict(self.cursor)

    def fetch_all_value(self, *args, **kwargs):
        self.cursor.execute(*args, **kwargs)
        return util_mysql.fetch_all_value(self.cursor)

    def fetch_one_dict(self, *args, **kwargs):
        self.cursor.execute(*args, **kwargs)
        return util_mysql.fetch_one_dict(self.cursor)

    def fetch_one_value(self, *args, **kwargs):
        self.cursor.execute(*args, **kwargs)
        return util_mysql.fetch_one_value(self.cursor)

    def execute(self, *args, **kwargs):
        return self.cursor.execute(*args, **kwargs)

    @staticmethod
    def escape(*args, **kwargs):
        return util_mysql.escape(*args, **kwargs)


# Handles
database_connections = {}
def get_connection(host='127.0.0.1', port=3306, username='root', password='', database=None, cache=True, timeout=10, query_timeout=600.0):
    global database_connections

    connection_name = u'{}|{}|{}'.format(host, port, database)
    connection = database_connections.get(connection_name) if cache else None

    if connection:
        connection.reconnect_if_closed()
    else:
        connection = Connection(host, port, username, password, database, timeout, query_timeout)
        connection.connect()
        if cache:
            database_connections[connection_name] = connection

    return connection