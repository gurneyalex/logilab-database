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
import unittest

from logilab.common.testlib import MockConnection

from unittest_fti import IndexableObject

from logilab.database import get_db_helper


class PGHelperTC(TestCase):
    def setUp(self):
        self.helper = get_db_helper('postgres')
        self.cnx = MockConnection( () )
        self.helper._cnx = self.cnx

    def test_type_map(self):
        self.assertEquals(self.helper.TYPE_MAPPING['Datetime'], 'timestamp')
        self.assertEquals(self.helper.TYPE_MAPPING['String'], 'text')
        self.assertEquals(self.helper.TYPE_MAPPING['Password'], 'bytea')
        self.assertEquals(self.helper.TYPE_MAPPING['Bytes'], 'bytea')

    def test_index_object(self):
        self.helper.index_object(1, IndexableObject())
        self.assertEquals(self.cnx.received,
                          [("INSERT INTO appears(uid, words) VALUES (%(uid)s,to_tsvector(%(config)s, %(wrds)s));",
                            {'config': 'default', 'wrds': 'ginco jpl bla blip blop blap', 'uid': 1})])

    def test_fulltext_search_base(self):
        self.helper.fulltext_search(u'ginco-jpl')
        self.assertEquals(self.cnx.received,
                          [("SELECT 1, uid FROM appears WHERE words @@ to_tsquery(%(config)s, %(words)s)",
                            {'config': 'default', 'words': 'ginco&jpl'})])

    def test_fulltext_search_prefix_1(self):
        self.helper.fulltext_search(u'ginco*')
        self.assertEquals(self.cnx.received,
                          [("SELECT 1, uid FROM appears WHERE words @@ to_tsquery(%(config)s, %(words)s)",
                            {'config': 'default', 'words': 'ginco:*'})])

    def test_fulltext_search_prefix_2(self):
        self.helper.fulltext_search(u'ginc*o')
        self.assertEquals(self.cnx.received,
                          [("SELECT 1, uid FROM appears WHERE words @@ to_tsquery(%(config)s, %(words)s)",
                            {'config': 'default', 'words': 'ginc:*o'})])

    # def test_embedded_tsearch2_is_found(self):
    #     # just make sure that something is found
    #     fullpath = self.helper.find_tsearch2_schema()

if __name__ == '__main__':
    unittest.main()
