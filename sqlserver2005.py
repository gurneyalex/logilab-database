"""Sqlserver 2005 RDBMS support

Supported drivers, in order of preference:
- pyodbc (recommended, others are not well tested)
- adodbapi

:copyright: 2009-2010 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: General Public License version 2 - http://www.gnu.org/licenses
"""
import os
import sys

from logilab import database as db
from logilab.database.sqlserver import _PyodbcAdapter, _AdodbapiAdapter
import StringIO

class _PyodbcSqlServer2005Adapter(_PyodbcAdapter):
    driver = "SQL Server Native Client 10.0"

class _AdodbapiSqlServer2005Adapter(_AdodbapiAdapter):
    driver = "SQL Server Native Client 10.0"

db._PREFERED_DRIVERS.update({
    'sqlserver2005' : ['pyodbc', 'adodbapi', ],
    })
db._ADAPTER_DIRECTORY.update({
    'sqlserver2005' : {'adodbapi': _AdodbapiSqlServer2005Adapter,
                       'pyodbc': _PyodbcSqlServer2005Adapter},
    })


class _SqlServer2005FuncHelper(db._GenericAdvFuncHelper):
    backend_name = 'sqlserver2005'
    ilike_support = False
    TYPE_MAPPING = {
        'String' :   'nvarchar(max)',
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
        cursor.execute('''sys.sp_tables @table_type = "'TABLE'"''')
        return [row[2] for row in cursor.fetchall()]
#        cursor.tables()
#        return  [row.table_name for row in cursor.fetchall()]

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



    def sql_temporary_table(self, table_name, table_schema,
                            drop_on_commit=True):
        table_name = self.temporary_table_name(table_name)
        return "CREATE TABLE %s (%s);" % (table_name, table_schema)

    def temporary_table_name(self, table_name):
        if not table_name.startswith('#'):
            table_name = '#' + table_name
        return table_name



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




if __name__ == "__main__": # used to backup sql server db
    func_call = sys.argv[1]
    eval(func_call+'()')
