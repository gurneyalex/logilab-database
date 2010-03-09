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
        self.assertEquals(self.helper.TYPE_MAPPING['Datetime'], 'datetime')
        self.assertEquals(self.helper.TYPE_MAPPING['String'], 'mediumtext')
        self.assertEquals(self.helper.TYPE_MAPPING['Password'], 'tinyblob')
        self.assertEquals(self.helper.TYPE_MAPPING['Bytes'], 'longblob')

    def test_index_object(self):
        self.helper.index_object(1, IndexableObject())
        self.assertEquals(self.cnx.received,
                          [('INSERT INTO appears(uid, words) VALUES (%(uid)s, %(wrds)s);',
                            {'wrds': 'ginco jpl bla blip blop blap', 'uid': 1})])

    def test_fulltext_search(self):
        self.helper.fulltext_search(u'ginco-jpl')
        self.assertEquals(self.cnx.received,
                          [('SELECT 1, uid FROM appears WHERE MATCH (words) AGAINST (%(words)s IN BOOLEAN MODE)',
                            {'words': 'ginco jpl'})])


if __name__ == '__main__':
    unittest.main()
