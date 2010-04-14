"""Sqlite RDBMS support

Supported drivers, in order of preference:
- pysqlite2 (recommended, others are not well tested)
- sqlite
- sqlite3

:copyright: 2002-2010 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: General Public License version 2 - http://www.gnu.org/licenses
"""
__docformat__ = "restructuredtext en"

from os.path import abspath
import os
import re

from logilab.common.date import strptime
from logilab import database as db

class _PySqlite2Adapter(db.DBAPIAdapter):
    """Simple pysqlite2 Adapter to DBAPI
    """
    # no type code in pysqlite2
    BINARY = 'XXX'
    STRING = 'XXX'
    DATETIME = 'XXX'
    NUMBER = 'XXX'
    BOOLEAN = 'XXX'

    def __init__(self, native_module, pywrap=False):
        db.DBAPIAdapter.__init__(self, native_module, pywrap)
        self._init_pysqlite2()

    def _init_pysqlite2(self):
        """initialize pysqlite2 to use mx.DateTime for date and timestamps"""
        sqlite = self._native_module
        if hasattr(sqlite, '_lc_initialized'):
            return
        sqlite._lc_initialized = 1

        # bytea type handling
        from StringIO import StringIO
        def adapt_bytea(data):
            return data.getvalue()
        sqlite.register_adapter(StringIO, adapt_bytea)
        def convert_bytea(data, Binary=sqlite.Binary):
            return Binary(data)
        sqlite.register_converter('bytea', convert_bytea)

        # boolean type handling
        def adapt_boolean(bval):
            return str(bval).upper()
        sqlite.register_adapter(bool, adapt_boolean)
        def convert_boolean(ustr):
            if ustr.upper() in ('F', 'FALSE'):
                return False
            return True
        sqlite.register_converter('boolean', convert_boolean)


        # decimal type handling
        from decimal import Decimal
        def adapt_decimal(data):
            return str(data)
        sqlite.register_adapter(Decimal, adapt_decimal)

        def convert_decimal(data):
            return Decimal(data)
        sqlite.register_converter('decimal', convert_decimal)

        # date/time types handling
        if db.USE_MX_DATETIME:
            from mx.DateTime import DateTimeType, DateTimeDeltaType, strptime
            def adapt_mxdatetime(mxd):
                return mxd.strftime('%Y-%m-%d %H:%M:%S')
            sqlite.register_adapter(DateTimeType, adapt_mxdatetime)
            def adapt_mxdatetimedelta(mxd):
                return mxd.strftime('%H:%M:%S')
            sqlite.register_adapter(DateTimeDeltaType, adapt_mxdatetimedelta)

            def convert_mxdate(ustr):
                return strptime(ustr, '%Y-%m-%d %H:%M:%S')
            sqlite.register_converter('date', convert_mxdate)
            def convert_mxdatetime(ustr):
                return strptime(ustr, '%Y-%m-%d %H:%M:%S')
            sqlite.register_converter('timestamp', convert_mxdatetime)
            def convert_mxtime(ustr):
                try:
                    return strptime(ustr, '%H:%M:%S')
                except:
                    # DateTime used as Time?
                    return strptime(ustr, '%Y-%m-%d %H:%M:%S')
            sqlite.register_converter('time', convert_mxtime)
        # else use datetime.datetime
        else:
            from datetime import time, timedelta
            # datetime.time
            def adapt_time(data):
                return data.strftime('%H:%M:%S')
            sqlite.register_adapter(time, adapt_time)
            def convert_time(data):
                return time(*[int(i) for i in data.split(':')])
            sqlite.register_converter('time', convert_time)
            # datetime.timedelta
            def adapt_timedelta(data):
                '''the sign in the result only refers to the number of days.  day
                fractions always indicate a positive offset.  this may seem strange,
                but it is the same that is done by the default __str__ method.  we
                redefine it here anyways (instead of simply doing "str") because we
                do not want any "days," string within the representation.
                '''
                days = data.days
                frac = data - timedelta(days)
                return "%d %s" % (data.days, frac)
            sqlite.register_adapter(timedelta, adapt_timedelta)
            def convert_timedelta(data):
                parts = data.split(" ")
                if len(parts) == 2:
                    daypart, timepart = parts
                    days = int(daypart)
                else:
                    days = 0
                    timepart = parts[-1]
                timepart_full = timepart.split(".")
                hours, minutes, seconds = map(int, timepart_full[0].split(":"))
                if len(timepart_full) == 2:
                    microseconds = int(float("0." + timepart_full[1]) * 1000000)
                else:
                    microseconds = 0
                data = timedelta(days,
                                 hours*3600 + minutes*60 + seconds,
                                 microseconds)
                return data
            sqlite.register_converter('interval', convert_timedelta)


    def connect(self, host='', database='', user='', password='', port=None, extra_args=None):
        """Handles sqlite connection format"""
        sqlite = self._native_module

        class PySqlite2Cursor(sqlite.Cursor):
            """cursor adapting usual dict format to pysqlite named format
            in SQL queries
            """
            def _replace_parameters(self, sql, kwargs):
                if isinstance(kwargs, dict):
                    return re.sub(r'%\(([^\)]+)\)s', r':\1', sql)
                # XXX dumb
                return re.sub(r'%s', r'?', sql)

            def execute(self, sql, kwargs=None):
                if kwargs is None:
                    self.__class__.__bases__[0].execute(self, sql)
                else:
                    final_sql = self._replace_parameters(sql, kwargs)
                    self.__class__.__bases__[0].execute(self, final_sql , kwargs)

            def executemany(self, sql, kwargss):
                if not isinstance(kwargss, (list, tuple)):
                    kwargss = tuple(kwargss)
                self.__class__.__bases__[0].executemany(self, self._replace_parameters(sql, kwargss[0]), kwargss)

        class PySqlite2CnxWrapper:
            def __init__(self, cnx):
                self._cnx = cnx

            def cursor(self):
                return self._cnx.cursor(PySqlite2Cursor)
            def __getattr__(self, attrname):
                return getattr(self._cnx, attrname)

        # abspath so we can change cwd without breaking further queries on the
        # database
        cnx = sqlite.connect(abspath(database), 
                             detect_types=sqlite.PARSE_DECLTYPES)
        return self._wrap_if_needed(PySqlite2CnxWrapper(cnx))

    def process_value(self, value, description, encoding='utf-8', binarywrap=None):
        if binarywrap is not None and isinstance(value, self._native_module.Binary):
            return binarywrap(value)
        return value # no type code support, can't do anything


class _SqliteAdapter(db.DBAPIAdapter):
    """Simple sqlite Adapter to DBAPI
    """
    def __init__(self, native_module, pywrap=False):
        db.DBAPIAdapter.__init__(self, native_module, pywrap)
        self.DATETIME = native_module.TIMESTAMP

    def connect(self, host='', database='', user='', password='', port='', extra_args=None):
        """Handles sqlite connection format"""
        return self._wrap_if_needed(self._native_module.connect(database))


db._PREFERED_DRIVERS['sqlite'] = ['pysqlite2.dbapi2', 'sqlite', 'sqlite3']
db._ADAPTER_DIRECTORY['sqlite'] = {
    'pysqlite2.dbapi2' : _PySqlite2Adapter,
    'sqlite' : _SqliteAdapter,
    'sqlite3' : _PySqlite2Adapter,
    }


class _SqliteAdvFuncHelper(db._GenericAdvFuncHelper):
    """Generic helper, trying to provide generic way to implement
    specific functionalities from others DBMS

    An exception is raised when the functionality is not emulatable
    """
    backend_name = 'sqlite'

    users_support = groups_support = False
    ilike_support = False
    union_parentheses_support = False
    intersect_all_support = False
    alter_column_support = False

    def backup_commands(self, backupfile, keepownership=True,
                        dbname=None, dbhost=None, dbport=None, dbuser=None):
        dbname = dbname or self.dbname
        return [['gzip', dbname], ['mv', dbname + '.gz', backupfile]]

    def restore_commands(self, backupfile, keepownership=True, drop=True,
                         dbname=None, dbhost=None, dbport=None, dbuser=None,
                         dbencoding=None):
        gunziped, ext = os.splitext(backupfile)
        assert ext.lower() in ('.gz', '.z') # else gunzip will fail anyway
        return [['gunzip', backupfile], ['mv', gunziped, dbname or self.dbname]]

    def sql_create_index(self, table, column, unique=False):
        idx = self._index_name(table, column, unique)
        if unique:
            return 'CREATE UNIQUE INDEX %s ON %s(%s);' % (idx, table, column)
        else:
            return 'CREATE INDEX %s ON %s(%s);' % (idx, table, column)

    def sql_drop_index(self, table, column, unique=False):
        return 'DROP INDEX %s' % self._index_name(table, column, unique)

    def list_tables(self, cursor):
        """return the list of tables of a database"""
        # filter type='table' else we get indices as well
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        return [r[0] for r in cursor.fetchall()]

    def list_indices(self, cursor, table=None):
        """return the list of indices of a database, only for the given table if specified"""
        sql = "SELECT name FROM sqlite_master WHERE type='index'"
        if table:
            sql += " AND LOWER(tbl_name)='%s'" % table.lower()
        cursor.execute(sql)
        return [r[0] for r in cursor.fetchall()]


db._ADV_FUNC_HELPER_DIRECTORY['sqlite'] = _SqliteAdvFuncHelper



def init_sqlite_connexion(cnx):
    def _parse_sqlite_date(date):
        if type(date) is unicode:
            try:
                date = strptime(date, '%Y-%m-%d %H:%M:%S')
            except:
                date = strptime(date, '%Y-%m-%d')
        return date

    def year(date):
        date = _parse_sqlite_date(date)
        return date.year
    def month(date):
        date = _parse_sqlite_date(date)
        return date.month
    def day(date):
        date = _parse_sqlite_date(date)
        return date.day
    def hour(date):
        date = _parse_sqlite_date(date)
        return date.hour
    def minute(date):
        date = _parse_sqlite_date(date)
        return date.minute
    def second(date):
        date = _parse_sqlite_date(date)
        return date.second
    cnx.create_function('MONTH', 1, month)
    cnx.create_function('YEAR', 1, year)
    cnx.create_function('DAY', 1, day)
    cnx.create_function('HOUR', 1, hour)
    cnx.create_function('MINUTE', 1, minute)
    cnx.create_function('SECOND', 1, second)

    from random import random
    cnx.create_function('RANDOM', 0, random)


sqlite_hooks = db.SQL_CONNECT_HOOKS.setdefault('sqlite', [])
sqlite_hooks.append(init_sqlite_connexion)

def register_sqlite_pyfunc(pyfunc, nb_params=None, funcname=None):
    if nb_params is None:
        nb_params = pyfunc.func_code.co_argcount
    if funcname is None:
        funcname = pyfunc.__name__.upper()
    def init_sqlite_connection(cnx):
        cnx.create_function(funcname, nb_params, pyfunc)
    sqlite_hooks = db.SQL_CONNECT_HOOKS.setdefault('sqlite', [])
    sqlite_hooks.append(init_sqlite_connection)
    funcdescr = db.SQL_FUNCTIONS_REGISTRY.get_function(funcname)
    funcdescr.add_support('sqlite')
