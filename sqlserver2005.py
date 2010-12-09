# copyright 2003-2010 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
# contact http://www.logilab.fr/ -- mailto:contact@logilab.fr
#
# This file is part of logilab-database.
#
# logilab-database is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 2.1 of the License, or (at your
# option) any later version.
#
# logilab-database is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License
# for more details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with logilab-database. If not, see <http://www.gnu.org/licenses/>.
"""Sqlserver 2005 RDBMS support

Supported drivers, in order of preference:
- pyodbc (recommended, others are not well tested)
- adodbapi
"""

import os
import sys
import shutil

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
        'SizeConstrainedString': 'nvarchar(%s)',
        }

    def list_tables(self, cursor):
        """return the list of tables of a database"""
        cursor.execute('''sys.sp_tables @table_type = "'TABLE'"''')
        return [row[2] for row in cursor.fetchall()]
        # cursor.tables()
        # return  [row.table_name for row in cursor.fetchall()]

    def list_indices(self, cursor, table=None):
        """return the list of indices of a database, only for the given table if specified"""
        sql = "SELECT name FROM sys.indexes"
        if table:
            sql = ("SELECT ind.name FROM sys.indexes as ind, sys.objects as obj WHERE "
                   "obj.object_id = ind.object_id AND obj.name = '%s'"
                   % table)
        cursor.execute(sql)
        return [r[0] for r in cursor.fetchall()]

    def backup_commands(self, backupfile, keepownership=True,
                        dbname=None, dbhost=None, dbport=None, dbuser=None):
        return [[sys.executable, os.path.normpath(__file__),
                 "_SqlServer2005FuncHelper._do_backup", dbhost or self.dbhost,
                 dbname or self.dbname, backupfile]]

    def restore_commands(self, backupfile, keepownership=True, drop=True,
                         dbname=None, dbhost=None, dbport=None, dbuser=None,
                         dbencoding=None):
        return [[sys.executable, os.path.normpath(__file__),
                "_SqlServer2005FuncHelper._do_restore", dbhost or self.dbhost,
                 dbname or self.dbname, backupfile],
                ]

    def _index_names(self, cursor, table, column):
        """
        return the list of index_information for table.column
        index_information is a tuple:
        (name, index_type, is_unique, is_unique_constraint)

        See http://msdn.microsoft.com/en-us/library/ms173760.aspx for more
        information
        """
        has_index_sql = """\
SELECT i.name AS index_name,
       i.type_desc,
       i.is_unique,
       i.is_unique_constraint
FROM sys.indexes AS i, sys.index_columns as j, sys.columns as k
WHERE is_hypothetical = 0 AND i.index_id <> 0
AND i.object_id = j.object_id
AND i.index_id = j.index_id
AND i.object_id = OBJECT_ID('%(table)s')
AND k.name = '%(col)s'
AND k.object_id=i.object_id
AND j.column_id = k.column_id;"""
        cursor.execute(has_index_sql % {'table': table, 'col': column})
        return cursor.fetchall()

    def index_exists(self, cursor, table, column, unique=False):
        indexes = self._index_names(cursor, table, column)
        return len(indexes) > 0

    def sql_concat_string(self, lhs, rhs):
        return '%s + %s' % (lhs, rhs)

    def sql_temporary_table(self, table_name, table_schema,
                            drop_on_commit=True):
        table_name = self.temporary_table_name(table_name)
        return "CREATE TABLE %s (%s);" % (table_name, table_schema)

    def sql_change_col_type(self, table, column, coltype, null_allowed):
        raise NotImplementedError('use .change_col_type()')

    def sql_set_null_allowed(self, table, column, coltype, null_allowed):
        raise NotImplementedError('use .set_null_allowed()')

    def sql_rename_table(self, oldname, newname):
        return  'EXEC sp_rename %s, %s' % (oldname, newname)

    def sqls_create_multicol_unique_index(self, table, columns):
        columns = sorted(columns)
        view = 'utv_%s_%s' % (table, '_'.join(columns))
        where = ' AND '.join(['%s IS NOT NULL' % c for c in columns])
        idx = 'unique_%s_%s_idx' % (table, '_'.join(columns))
        sql = ['CREATE VIEW %s WITH SCHEMABINDING AS SELECT %s FROM dbo.%s WHERE %s ;'%(view.lower(), 
                                                      ', '.join(columns),
                                                      table,
                                                      where),
               'CREATE UNIQUE CLUSTERED INDEX %s ON %s(%s);' % (idx.lower(),
                                                                view.lower(),
                                                                ','.join(columns))
            ]
        return sql

    def sqls_drop_multicol_unique_index(self, table, columns):
        columns = sorted(columns)
        view = 'utv_%s_%s' % (table, '_'.join(columns))
        sql = 'DROP VIEW %s' % (view.lower()) # also drops the index
        return [sql]

    def sql_drop_index(self, table, column, unique=False):
        if unique:
            return super(_SqlServer2005FuncHelper, self).sql_drop_index(table, column, unique)
        else:
            idx = self._index_name(table, column, unique)
            return 'DROP INDEX %s ON %s;' % (idx, table)


    def change_col_type(self, cursor, table, column, coltype, null_allowed):
        alter = []
        drops = []
        creates = []
        print "change col type for %s.%s to %s %s" % (table, column, coltype, null_allowed and 'NULL' or 'NOT NULL')

        for idx_name, idx_type, is_unique, is_unique_cstr in self._index_names(cursor, table, column):
            if is_unique_cstr:
                drops.append('ALTER TABLE %s DROP CONSTRAINT %s' % (table, idx_name))
                creates.append('ALTER TABLE %s ADD CONSTRAINT %s UNIQUE (%s)' % (table, idx_name, column))
            else:
                drops.append('DROP INDEX %s ON %s' % (idx_name, table))
                if is_unique:
                    unique = 'UNIQUE'
                else:
                    unique = ''
                creates.append('CREATE %s %s INDEX %s ON %s(%s)' % (unique, idx_type, idx_name, table, column))

        if null_allowed:
            null = 'NULL'
        else:
            null = 'NOT NULL'
        alter.append('ALTER TABLE %s ALTER COLUMN %s %s %s' % (table, column, coltype, null))
        for stmt in drops + alter + creates:
            cursor.execute(stmt)

    def set_null_allowed(self, cursor, table, column, coltype, null_allowed):
        return self.change_col_type(cursor, table, column, coltype, null_allowed)

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
        cnx = get_connection(driver='sqlserver2005',
                             host=dbhost, database=dbname,
                             extra_args='autocommit;trusted_connection')
        cursor = cnx.cursor()
        sql_server_local_filename = r"C:\Backups\%s" % dbname
        file_share_filename = r"\\%s\Backups\%s" % (dbhost, dbname)
        cursor.execute("BACKUP DATABASE %(db)s TO DISK= %(path)s ",
                       {'db':dbname,
                        'path':sql_server_local_filename,
                        })
        prev_size = -1
        err_count = 0
        same_size_count = 0
        while err_count < 10 and same_size_count < 10:
            time.sleep(1)
            try:
                size = os.path.getsize(file_share_filename)
            except OSError, exc:
                err_count += 1
                print exc
            if size > prev_size:
                same_size_count = 0
                prev_size = size
            else:
                same_size_count += 1
        shutil.copy(file_share_filename, filename)
        os.remove(file_share_filename)
        cnx.close()
        sys.exit(0)

    @staticmethod
    def _do_restore():
        """return the SQL statement to restore a backup of the given database"""
        from logilab.database import get_connection
        dbhost = sys.argv[2]
        dbname = sys.argv[3]
        filename = sys.argv[4]
        sql_server_local_filename = r"C:\Backups\%s" % dbname
        file_share_filename = r"\\%s\Backups\%s" % (dbhost, dbname)
        shutil.copy(filename, file_share_filename)
        cnx = get_connection(driver='sqlserver2005',
                             host=dbhost, database='master',
                             extra_args='autocommit;trusted_connection')

        cursor = cnx.cursor()
        cursor.execute("RESTORE DATABASE %(db)s FROM DISK= %(path)s WITH REPLACE",
                       {'db':dbname,
                        'path':sql_server_local_filename,
                        })
        import time
        sleeptime = 10
        while True:
            time.sleep(sleeptime)
            try:
                cnx = get_connection(driver='sqlserver2005',
                                     host=dbhost, database=dbname,
                                     extra_args='trusted_connection')
                break
            except:
                sleeptime = min(sleeptime*2, 300)
        os.remove(file_share_filename)
        sys.exit(0)


db._ADV_FUNC_HELPER_DIRECTORY['sqlserver2005'] = _SqlServer2005FuncHelper




if __name__ == "__main__": # used to backup sql server db
    func_call = sys.argv[1]
    eval(func_call+'()')
