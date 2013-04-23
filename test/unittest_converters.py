# copyright 2013 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
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
from datetime import datetime, time, date

from logilab.database import get_db_helper


class TYPEConvertersTC(unittest.TestCase):

    def test_existing_converters(self):
        self.helper = get_db_helper('sqlite')
        self.assertEqual(len(self.helper.TYPE_CONVERTERS), 5)

    def test_convert_boolean(self):
        self.helper = get_db_helper('sqlite')
        self.assertEqual(self.helper.TYPE_CONVERTERS['Boolean'](False), False)
        self.assertEqual(self.helper.TYPE_CONVERTERS['Boolean'](True), True)
        self.assertEqual(self.helper.TYPE_CONVERTERS['Boolean'](0), False)
        self.assertEqual(self.helper.TYPE_CONVERTERS['Boolean'](1), True)
        self.assertEqual(self.helper.TYPE_CONVERTERS['Boolean'](''), False)
        self.assertEqual(self.helper.TYPE_CONVERTERS['Boolean']('1'), True)

    def test_convert_datetime(self):
        _date = date(1900,10,1)
        _datetime = datetime(1900, 10, 1, 0, 0)
        self.helper = get_db_helper('sqlite')
        self.assertEqual(self.helper.TYPE_CONVERTERS['Datetime'](_date), _datetime)

    def test_convert_date(self):
        _date = date(1900,10,1)
        _datetime = datetime(1900, 10, 1, 0, 0)
        self.helper = get_db_helper('sqlite')
        self.assertEqual(self.helper.TYPE_CONVERTERS['Date'](_datetime), _date)


if __name__ == '__main__':
    unittest.main()
