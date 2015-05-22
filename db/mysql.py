# +----------------------------------------------------------------------+
# | Copyright (c) 2015 Winston Wolf                                      |
# +----------------------------------------------------------------------+
# | This source file is bound by United States copyright law.            |
# +----------------------------------------------------------------------+
# | Author: Winston Wolf <winston.the.cleaner@gmail.com>                 |
# +----------------------------------------------------------------------+

import pytz
import json
import MySQLdb
from threading import Thread
from datetime import datetime

class QueryTimeoutException(Exception):
    pass

# Fetches all results from a cursor and returns a list of dictionaries
def fetch_all_dict(cursor):
    try:
        desc = cursor.description
        return [
            dict(zip([col[0] for col in desc], row))
            for row in cursor.fetchall()
        ]
    except:
        return None

# Fetches one result from a cursor and returns a list of dictionaries
def fetch_one_dict(cursor):
    try:
        return dict(zip([col[0] for col in cursor.description], cursor.fetchone()))
    except:
        return None

# Fetches all results from a cursor and returns a list of values
def fetch_all_value(cursor):
    return [
        row[0]
        for row in cursor.fetchall()
    ]

# Fetches all results from a cursor and returns a list of values
def fetch_one_value(cursor):
    try:
        return cursor.fetchone()[0]
    except:
        return None


def datetime_to_utc_timestamp(dt):
    if dt.tzinfo:
        return dt.astimezone(pytz.utc).strftime('%Y-%m-%d %H:%M:%S')
    else:
        return dt.strftime('%Y-%m-%d %H:%M:%S')

# Executes a query and returns the cursor
def escape(param):
    paramType = type(param)
    if paramType is unicode:
        return u"'" + param.replace(u"\\", u"\\\\").replace(u"'", u"\\'") + u"'"
    elif paramType is bool:
        return u"1" if param else u"0"
    elif paramType is datetime:
        return u"'" + datetime_to_utc_timestamp(param) + u"'"
    elif paramType is dict or paramType is list:
        return u"'" + json.dumps(param).replace(u"\\", u"\\\\").replace(u"'", u"\\'") + u"'"
    elif param is None:
        return u"NULL"
    else:
        return u"'" + unicode(param).replace(u"\\", u"\\\\").replace(u"'", u"\\'") + u"'"


class MySQLDummyCursor(object):
    rows = None
    description = None
    rowcount = None
    def fetchall(self):
        return self.rows
    def fetchone(self):
        return self.rows[0] if self.rows else None

class MySQLCursorWrapper(object):
    _connection = None
    _cursor_results = None
    needs_recovery = False

    def __init__(self, _connection):
        self.init(_connection)
        super(MySQLCursorWrapper, self).__init__()

    def init(self, _connection):
        self._connection = _connection

    def cursor(self):
        return self._connection.connection.cursor()

    # ---------------------------------------------------- #
    # Query Execution
    # ---------------------------------------------------- #

    def execute(self, *args, **kwargs):
        if 'timeout' in kwargs:
            timeout = kwargs['timeout']
            del kwargs['timeout']
        else:
            timeout = self._connection.query_timeout

        try:
            return self.execute_with_timeout(args, kwargs, timeout)
        except MySQLdb.OperationalError as error:
            # 2006 - Server went away
            # 2013 - Lost connection during query
            if error[0] in (2006, 2013):
                self._connection.connect()
                return self.execute_with_timeout(args, kwargs, timeout)
            else:
                raise error

    def execute_with_timeout(self, args, kwargs, timeout):
        if timeout:
            results = []
            thread = Thread(target=MySQLCursorWrapper.execute_against_connection,
                                 args=(self._connection.connection, args, kwargs, results))
            thread.start()
            thread.join(timeout)

            if thread.is_alive():
                raise QueryTimeoutException("MySQL query timed out")

            exception = results[0]
            if not exception is None:
                raise exception

            result = results[1]
            self._cursor_results = MySQLDummyCursor()
            self._cursor_results.description = results[2]
            self._cursor_results.rowcount = results[3]
            self._cursor_results.rows = results[4]

            return result
        else:
            cursor = self.cursor()
            result = cursor.execute(*args, **kwargs)
            self._cursor_results = MySQLDummyCursor()
            self._cursor_results.description = cursor.description
            self._cursor_results.rowcount = cursor.rowcount
            self._cursor_results.rows = cursor.rows
            cursor.close()

            return result

    @staticmethod
    def execute_against_connection(connection, args, kwargs, results):
        exception = None
        fetchall = None
        rowcount = None
        result = None
        description = None
        try:
            cursor = connection.cursor()
            result = cursor.execute(*args, **kwargs)
            rowcount = cursor.rowcount
            fetchall = cursor.fetchall()
            description = cursor.description
            cursor.close()
        except Exception as e:
            exception = e

        results.append(exception)
        results.append(result)
        results.append(description)
        results.append(rowcount)
        results.append(fetchall)

        return True

    # ---------------------------------------------------- #
    # Feed Through
    # ---------------------------------------------------- #

    def close(self, *args, **kwargs):
        return
    def fetchone(self, *args, **kwargs):
        return self._cursor_results.fetchone(*args, **kwargs)
    def fetchall(self, *args, **kwargs):
        return self._cursor_results.fetchall(*args, **kwargs)

    @property
    def description(self):
        return self._cursor_results.description
    @property
    def rowcount(self):
        return self._cursor_results.rowcount
