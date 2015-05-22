import MySQLdb
from config import *
# Variables list, this list will be the columns that we want to analyze for correlation to winnin a game

variables_to_analyze = []

# This takes in an array of variables that are column names, which will find the correlation, slope, and
# intercept of each variable in relation to winning a game.
def analyze_variables(variables):
    connection = MySQLdb.connect(host=HOST, db=DATABASE, user=USER, passwd=PASSWORD)
    cursor = connection.cursor(MySQLdb.cursors.DictCursor)
    results = {}
    sql = u"""
        SELECT
            *,
            (y_mean - (slope*x_mean)) AS intercept
        FROM
            (
                SELECT
                    *,
                    ((n*xy_sum) - (x_sum*y_sum)) / SQRT(((n*x_sum_squares) - (x_sum*x_sum)) * ((n*
                    y_sum_squares) - (y_sum*y_sum))) AS correlation,
                    ((n*xy_sum) - (x_sum*y_sum)) / ((n*x_sum_squares) - (x_sum*x_sum)) AS slope
                FROM
                    (
                        SELECT
                            COUNT({1}) AS n,
                            AVG({0}) AS "x_mean",
                            SUM({0}) AS "x_sum",
                            SUM({0}*{0}) AS "x_sum_squares",
                            AVG({1}) AS "y_mean",
                            SUM({1}) AS "y_sum",
                            SUM({1}*{1}) AS "y_sum_squares",
                            SUM({0}*{1}) AS "xy_sum"
                        FROM
                            (
                                SELECT
                                    {0},
                                    {1}
                                FROM
                                    lol_master_ease.matches
                            ) q1
                    ) q2
            ) q3
    """
    count = 0
    for x_variable in variables:
        count += 1
        print "working on variable {} of {}".format(count, len(variables))
        results[x_variable] = []
        for y_variable in variables:
            if x_variable == y_variable:
                pass
            else:
                cursor.execute(sql.format(x_variable, y_variable))
                result = list(cursor.fetchall())[0]
                results[x_variable].append({'y_variable': y_variable,
                                       'n': result['n'],
                                       'x_mean': result['x_mean'],
                                       'x_sum': result['x_sum'],
                                       'x_sum_squares': result['x_sum_squares'],
                                       'y_mean': result['y_mean'],
                                       'y_sum': result['y_sum'],
                                       'y_sum_squares': result['y_sum_squares'],
                                       'xy_sum': result['xy_sum'],
                                       'correlation': result['correlation'],
                                       'slope': result['slope'],
                                       'intercept': result['intercept']})
    connection.close()
    return results

if __name__ == '__main__':
    analyze = analyze_variables(variables_to_analyze)
    for variable in analyze:
        for test_variable in analyze[variable]:
            print "{} - {} - {}".format(variable, test_variable['y_variable'], test_variable['correlation'])
