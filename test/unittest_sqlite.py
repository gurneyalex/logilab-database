import unittest

from logilab.common.testlib import MockConnection

from logilab.database import get_db_helper


class SQLiteHelperTC(unittest.TestCase):

    def setUp(self):
        self.cnx = MockConnection( () )
        self.helper = get_db_helper('sqlite')
        self.helper._cnx = self.cnx

    def test_type_map(self):
        self.assertEquals(self.helper.TYPE_MAPPING['Datetime'], 'timestamp')
        self.assertEquals(self.helper.TYPE_MAPPING['String'], 'text')
        self.assertEquals(self.helper.TYPE_MAPPING['Password'], 'bytea')
        self.assertEquals(self.helper.TYPE_MAPPING['Bytes'], 'bytea')


if __name__ == '__main__':
    unittest.main()
