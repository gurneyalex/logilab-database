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
import unittest

from logilab.common.testlib import MockConnection

from logilab.database import get_db_helper

from unittest_fti import IndexableObject


class MyHelperTC(unittest.TestCase):

    def setUp(self):
        self.cnx = MockConnection( () )
        self.helper = get_db_helper('mysql')
        self.helper._cnx = self.cnx

    def test_type_map(self):
        self.assertEqual(self.helper.TYPE_MAPPING['Datetime'], 'datetime')
        self.assertEqual(self.helper.TYPE_MAPPING['String'], 'mediumtext')
        self.assertEqual(self.helper.TYPE_MAPPING['Password'], 'tinyblob')
        self.assertEqual(self.helper.TYPE_MAPPING['Bytes'], 'longblob')

    def test_index_object(self):
        self.helper.index_object(1, IndexableObject())
        self.assertEqual(self.cnx.received,
                          [('INSERT INTO appears(uid, words) VALUES (%(uid)s, %(wrds)s);',
                            {'wrds': 'ginco jpl bla blip blop blap cubic 456', 'uid': 1})])

    def test_fulltext_search(self):
        self.helper.fulltext_search(u'ginco-jpl')
        self.assertEqual(self.cnx.received,
                          [('SELECT 1, uid FROM appears WHERE MATCH (words) AGAINST (%(words)s IN BOOLEAN MODE)',
                            {'words': 'ginco jpl'})])


if __name__ == '__main__':
    unittest.main()
