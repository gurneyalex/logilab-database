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

    def test_fulltext_search(self):
        self.helper.fulltext_search(u'ginco-jpl')
        self.assertEquals(self.cnx.received,
                          [("SELECT 1, uid FROM appears WHERE words @@ to_tsquery(%(config)s, %(words)s)",
                            {'config': 'default', 'words': 'ginco&jpl'})])

    # def test_embedded_tsearch2_is_found(self):
    #     # just make sure that something is found
    #     fullpath = self.helper.find_tsearch2_schema()

if __name__ == '__main__':
    unittest.main()
