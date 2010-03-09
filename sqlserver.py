"""Sqlserver RDBMS support

Supported drivers, in order of preference:
- pyodbc (recommended, others are not well tested)
- adodbapi

:copyright: 2002-2010 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: General Public License version 2 - http://www.gnu.org/licenses
"""
__docformat__ = "restructuredtext en"

import os
import sys
import datetime
import re
import threading
import StringIO

from logilab import database as db

class _BaseSqlServerAdapter(db.DBAPIAdapter):
    driver = 'Override in subclass'
    _use_trusted_connection = False
    _use_autocommit = False
    _fetch_lock = threading.Lock()

    @classmethod
    def use_trusted_connection(cls, use_trusted=False):
        """
        pass True to this class method to enable Windows
        Authentication (i.e. passwordless auth)
        """
        cls._use_trusted_connection = use_trusted

    @classmethod
    def use_autocommit(cls, use_autocommit=False):
        """
        pass True to this class method to enable autocommit (required
        for backup and restore)
        """
        cls._use_autocommit = use_autocommit

    @classmethod
    def _process_extra_args(cls, arguments):
        arguments = arguments.lower().split(';')
        if 'trusted_connection' in arguments:
            cls.use_trusted_connection(True)
        if 'autocommit' in arguments:
            cls.use_autocommit(True)

    def connect(self, host='', database='', user='', password='', port=None, extra_args=None):
        """Handles pyodbc connection format

        If extra_args is not None, it is expected to be a string
        containing a list of semicolon separated keywords. The only
        keyword currently supported is Trusted_Connection : if found
        the connection string to the database will include
        Trusted_Connection=yes (which for SqlServer will trigger using
        Windows Authentication, and therefore no login/password is
        required.
        """
        lock = self._fetch_lock
        class SqlServerCursor(object):
            """cursor adapting usual dict format to pyodbc/adobdapi format
            in SQL queries
            """
            def __init__(self, cursor):
                self._cursor = cursor
                self._fetch_lock = lock
            def _replace_parameters(self, sql, kwargs, _date_class=datetime.date):
                if isinstance(kwargs, dict):
                    new_sql = re.sub(r'%\(([^\)]+)\)s', r'?', sql)
                    key_order = re.findall(r'%\(([^\)]+)\)s', sql)
                    args = []
                    for key in key_order:
                        arg = kwargs[key]
                        if arg.__class__ == _date_class:
                            arg = datetime.datetime.combine(arg, datetime.time(0))
                        args.append(arg)

                    return new_sql, tuple(args)

                # XXX dumb
                return re.sub(r'%s', r'?', sql), kwargs

            def execute(self, sql, kwargs=None):
                if kwargs is None:
                    self._cursor.execute(sql)
                else:
                    final_sql, args = self._replace_parameters(sql, kwargs)
                    self._cursor.execute(final_sql , args)
            def executemany(self, sql, kwargss):
                if not isinstance(kwargss, (list, tuple)):
                    kwargss = tuple(kwargss)
                self._cursor.executemany(self, self._replace_parameters(sql, kwargss[0]), kwargss)

            def _get_smalldate_columns(self):
                cols = []
                for i, coldef in enumerate(self._cursor.description):
                    if coldef[1] is datetime.datetime and coldef[3] == 16:
                        cols.append(i)
                return cols

            def fetchone(self):
                smalldate_cols = self._get_smalldate_columns()
                self._fetch_lock.acquire()
                try:
                    row = self._cursor.fetchone()
                finally:
                    self._fetch_lock.release()
                return self._replace_smalldate(row, smalldate_cols)

            def fetchall (self):
                smalldate_cols = self._get_smalldate_columns()
                rows = []
                while True:
                    self._fetch_lock.acquire()
                    try:
                        batch = self._cursor.fetchmany(1024)
                    finally:
                        self._fetch_lock.release()
                    if not batch:
                        break
                    for row in batch:
                        rows.append(self._replace_smalldate(row, smalldate_cols))
                return rows

            def _replace_smalldate(self, row, smalldate_cols):
                if smalldate_cols:
                    new_row = row[:]
                    for col in smalldate_cols:
                        new_row[col] = new_row[col].date()
                    return new_row
                else:
                    return row
            def __getattr__(self, attrname):
                return getattr(self._cursor, attrname)

        class SqlServerCnxWrapper:
            def __init__(self, cnx):
                self._cnx = cnx
            def cursor(self):
                return SqlServerCursor(self._cnx.cursor())
            def __getattr__(self, attrname):
                return getattr(self._cnx, attrname)
        cnx = self._connect(host=host, database=database, user=user, password=password, port=port, extra_args=extra_args)
        return self._wrap_if_needed(SqlServerCnxWrapper(cnx))

    def process_value(self, value, description, encoding='utf-8', binarywrap=None):
        # if the dbapi module isn't supporting type codes, override to return value directly
        typecode = description[1]
        assert typecode is not None, self
        if typecode == self.STRING:
            if isinstance(value, str):
                return unicode(value, encoding, 'replace')
        elif typecode == self.BINARY:  # value is a python buffer
            if binarywrap is not None:
                return binarywrap(value[:])
            else:
                return value[:]
        elif typecode == self.UNKNOWN:
            # may occurs on constant selection for instance (e.g. SELECT 'hop')
            # with postgresql at least
            if isinstance(value, str):
                return unicode(value, encoding, 'replace')
        return value


class _PyodbcAdapter(_BaseSqlServerAdapter):
    def _connect(self, host='', database='', user='', password='', port=None, extra_args=None):
        if extra_args is not None:
            self._process_extra_args(extra_args)
        #cnx_string_bits = ['DRIVER={%(driver)s}']
        variables = {'host' : host,
                     'database' : database,
                     'user' : user, 'password' : password,
                     'driver': self.driver}
        if self._use_trusted_connection:
            variables['Trusted_Connection'] = 'yes'
            del variables['user']
            del variables['password']
        if self._use_autocommit:
            variables['autocommit'] = True
        return self._native_module.connect(**variables)


class _PyodbcAdapterMT(_PyodbcAdapter):
    def process_value(self, value, description, encoding='utf-8', binarywrap=None):
        # if the dbapi module isn't supporting type codes, override to return value directly
        typecode = description[1]
        assert typecode is not None, self
        if typecode == self.STRING:
            if isinstance(value, str):
                return unicode(value, encoding, 'replace')
        elif typecode == self.BINARY:  # value is a python buffer
            if binarywrap is not None:
                return binarywrap(value.getbinary())
            else:
                return value.getbinary()
        elif typecode == self.UNKNOWN:
            # may occurs on constant selection for instance (e.g. SELECT 'hop')
            # with postgresql at least
            if isinstance(value, str):
                return unicode(value, encoding, 'replace')

        return value

class _PyodbcSqlServer2000Adapter(_PyodbcAdapter):
    driver = "SQL Server"

class _PyodbcSqlServer2005Adapter(_PyodbcAdapter):
    driver = "SQL Server Native Client 10.0"

class _PyodbcSqlServer2008Adapter(_PyodbcAdapter):
    driver = "SQL Server Native Client 10.0"

class _PyodbcSqlServer2000AdapterMT(_PyodbcAdapterMT):
    driver = "SQL Server"

class _PyodbcSqlServer2005AdapterMT(_PyodbcAdapterMT):
    driver = "SQL Server Native Client 10.0"

class _PyodbcSqlServer2008AdapterMT(_PyodbcAdapterMT):
    driver = "SQL Server Native Client 10.0"

class _AdodbapiAdapter(_BaseSqlServerAdapter):

    def _connect(self, host='', database='', user='', password='', port=None, extra_args=None):
        if extra_args is not None:
            self._process_extra_args(extra_args)
        if self._use_trusted_connection:
            # this will open a MS-SQL table with Windows authentication
            auth = 'Integrated Security=SSPI'
        else:
            # this set opens a MS-SQL table with SQL authentication
            auth = 'user ID=%s; Password=%s;' % (user, password)
        constr = r"Initial Catalog=%s; Data Source=%s; Provider=SQLOLEDB.1; %s"\
                 % (database, host, auth)
        return self._native_module.connect(constr)

class _AdodbapiSqlServer2000Adapter(_AdodbapiAdapter):
    driver = "SQL Server"

class _AdodbapiSqlServer2005Adapter(_AdodbapiAdapter):
    driver = "SQL Server Native Client 10.0"

class _AdodbapiSqlServer2008Adapter(_AdodbapiAdapter):
    driver = "SQL Server Native Client 10.0"


db._PREFERED_DRIVERS.update({
    'sqlserver2000' : ['pyodbc', 'adodbapi', ],
    'sqlserver2005' : ['pyodbc', 'adodbapi', ],
    'sqlserver2008' : ['pyodbc', 'adodbapi', ],
    # for use in multithreaded applications, e.g. CubicWeb
    'sqlserver2000_mt' : ['logilab.database._pyodbcwrap'],
    'sqlserver2005_mt' : ['logilab.database._pyodbcwrap'],
    'sqlserver2008_mt' : ['logilab.database._pyodbcwrap'],
    })
db._ADAPTER_DIRECTORY.update({
    'sqlserver2000' : {'adodbapi': _AdodbapiSqlServer2000Adapter,
                       'pyodbc': _PyodbcSqlServer2000Adapter},
    'sqlserver2005' : {'adodbapi': _AdodbapiSqlServer2005Adapter,
                       'pyodbc': _PyodbcSqlServer2005Adapter},
    'sqlserver2008' : {'adodbapi': _AdodbapiSqlServer2008Adapter,
                       'pyodbc': _PyodbcSqlServer2008Adapter},
    'sqlserver2000_mt' : {'logilab.database._pyodbcwrap': _PyodbcSqlServer2000AdapterMT},
    'sqlserver2005_mt' : {'logilab.database._pyodbcwrap': _PyodbcSqlServer2005AdapterMT},
    'sqlserver2008_mt' : {'logilab.database._pyodbcwrap': _PyodbcSqlServer2008AdapterMT},
    })


class _SqlServer2005FuncHelper(db._GenericAdvFuncHelper):
    backend_name = 'sqlserver2005'
    ilike_support = False
    TYPE_MAPPING = {
        'String' :   'ntext',
        'Int' :      'integer',
        'Float' :    'float',
        'Decimal' :  'decimal',
        'Boolean' :  'bit',
        'Date' :     'smalldatetime',
        'Time' :     'time',
        'Datetime' : 'datetime',
        'Interval' : 'interval',
        'Password' : 'varbinary(255)',
        'Bytes' :    'varbinary(max)',
        }

    def list_tables(self, cursor):
        """return the list of tables of a database"""
        cursor.tables()
        return  [row.table_name for row in cursor.fetchall()]

    def binary_value(self, value):
        return StringIO.StringIO(value)

    def backup_commands(self, backupfile, keepownership=True,
                        dbname=None, dbhost=None, dbport=None, dbuser=None):
        return [[sys.executable, os.path.normpath(__file__),
                 "_SqlServer2005FuncHelper._do_backup", dbhost or self.dbhost,
                 dbname or self.dbname, backupfile]
                ]

    def restore_commands(self, backupfile, keepownership=True, drop=True,
                         dbname=None, dbhost=None, dbport=None, dbuser=None,
                         dbencoding=None):
        return [[sys.executable, os.path.normpath(__file__),
                "_SqlServer2005FuncHelper._do_restore", dbhost or self.dbhost,
                 dbname or self.dbname, backupfile],
                ]

    @staticmethod
    def _do_backup():
        import time
        from logilab.database import get_connection
        dbhost = sys.argv[2]
        dbname = sys.argv[3]
        filename = sys.argv[4]
        cnx = get_connection(driver='sqlserver2005', host=dbhost, database=dbname, extra_args='autocommit;trusted_connection')
        cursor = cnx.cursor()
        cursor.execute("BACKUP DATABASE ? TO DISK= ? ", (dbname, filename,))
        prev_size = -1
        err_count = 0
        same_size_count = 0
        while err_count < 10 and same_size_count < 10:
            time.sleep(1)
            try:
                size = os.path.getsize(filename)
            except OSError, exc:
                err_count += 1
                print exc
            if size > prev_size:
                same_size_count = 0
                prev_size = size
            else:
                same_size_count += 1
        cnx.close()
        sys.exit(0)

    @staticmethod
    def _do_restore():
        """return the SQL statement to restore a backup of the given database"""
        from logilab.database import get_connection
        dbhost = sys.argv[2]
        dbname = sys.argv[3]
        filename = sys.argv[4]
        cnx = get_connection(driver='sqlserver2005', host=dbhost, database='master', extra_args='autocommit;trusted_connection')
        cursor = cnx.cursor()
        cursor.execute("RESTORE DATABASE ? FROM DISK= ? WITH REPLACE", (dbname, filename,))
        sys.exit(0)


db._ADV_FUNC_HELPER_DIRECTORY['sqlserver2005'] = _SqlServer2005FuncHelper
db._ADV_FUNC_HELPER_DIRECTORY['sqlserver2005_mt'] = _SqlServer2005FuncHelper


if __name__ == "__main__": # used to backup sql server db
    func_call = sys.argv[1]
    eval(func_call+'()')
