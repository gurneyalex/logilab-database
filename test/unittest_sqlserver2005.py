# copyright 2003-2011 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
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
from __future__ import print_function

import sys
import unittest

from logilab.common.testlib import TestCase, MockConnection

from logilab.database import get_db_helper

from logilab import database as db
def monkey_patch_import_driver_module(driver, drivers, quiet=True):
    if not driver in drivers:
        raise db.UnknownDriver(driver)
    for modname in drivers[driver]:
        try:
            if not quiet:
                print('Trying %s' % modname, file=sys.stderr)
            module = db.load_module_from_name(modname, use_sys=False)
            break
        except ImportError:
            if not quiet:
                print('%s is not available' % modname, file=sys.stderr)
            continue
    else:
        return None, drivers[driver][0]
    return module, modname

def setUpModule():
    db._backup_import_driver_module = db._import_driver_module
    db._import_driver_module = monkey_patch_import_driver_module

def tearDownModule():
    db._import_driver_module = db._backup_import_driver_module
    del db._backup_import_driver_module

class SqlServer2005HelperTC(TestCase):
    def setUp(self):
        self.helper = get_db_helper('sqlserver2005')
        self.cnx = MockConnection( () )
        self.helper._cnx = self.cnx

    def test_type_map(self):
        self.assertEqual(self.helper.TYPE_MAPPING['Datetime'], 'datetime')
        self.assertEqual(self.helper.TYPE_MAPPING['Date'], 'smalldatetime')
        self.assertEqual(self.helper.TYPE_MAPPING['String'], 'nvarchar(max)')
        self.assertEqual(self.helper.TYPE_MAPPING['Password'], 'varbinary(255)')
        self.assertEqual(self.helper.TYPE_MAPPING['Bytes'], 'varbinary(max)')

    def test_order_by_simple(self):
        sql = 'SELECT A, B, C FROM Table1, Table2 WHERE Table1.D = Table2.D'
        new_sql = self.helper.sql_add_order_by(sql, ['A', 'B'], None, False, False)
        self.assertEqual(new_sql,
                          'SELECT A, B, C FROM Table1, Table2 WHERE Table1.D = Table2.D\nORDER BY A,B')
    def test_order_by_wrapped(self):
        sql = 'SELECT A AS C0, B AS C1, C FROM Table1, Table2 WHERE Table1.D = Table2.D'
        new_sql = self.helper.sql_add_order_by(sql, ['1', '2'], [1, 2], True, False)
        self.assertEqual(new_sql,
                         'SELECT T1.C0,T1.C1 FROM (SELECT A AS C0, B AS C1, C FROM Table1, Table2 WHERE Table1.D = Table2.D) AS T1\nORDER BY T1.C0,T1.C1')

    def test_order_by_with_limit(self):
        sql = 'SELECT A AS C0, B AS C1, C FROM Table1, Table2 WHERE Table1.D = Table2.D'
        new_sql = self.helper.sql_add_order_by(sql, ['1', '2'], [1, 2], True, True)
        self.assertEqual(new_sql, sql)

    def test_limit_offset_with_order_by(self):
        sql = 'SELECT A AS C0, B AS C1, C FROM Table1, Table2 WHERE Table1.D = Table2.D'
        new_sql = self.helper.sql_add_limit_offset(sql, limit=10, offset=10,
                                                   orderby = ['1', '2'])
        self.assertEqual(new_sql, '''WITH orderedrows AS (\nSELECT \n C0,  C1, _L01\n, ROW_NUMBER() OVER (ORDER BY  C0,  C1) AS __RowNumber\nFROM (\nSELECT A  AS  C0, B  AS  C1, C AS _L01 FROM  Table1, Table2 WHERE Table1.D = Table2.D\n) AS _SQ1 )\nSELECT \n C0,  C1, _L01\nFROM orderedrows WHERE \n__RowNumber <= 20 AND __RowNumber > 10''')

if __name__ == '__main__':
    unittest.main()
