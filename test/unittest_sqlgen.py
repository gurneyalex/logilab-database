# copyright 2003-2013 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
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
from logilab.database.sqlgen import SQLGenerator, SQLExpression


class SQLGenTC(unittest.TestCase):

    def test_set_values(self):
        s = SQLGenerator()
        self.assertEqual(s.set(['nom']), 'nom = %(nom)s')
        self.assertEqual(s.set(['nom','prenom']), 'nom = %(nom)s, prenom = %(prenom)s')
        params = {'nom': 'dupont', 'prenom': 'jean'}
        self.assertEqual(s.set(params), 'nom = %(nom)s, prenom = %(prenom)s')
        self.assertEqual(params, {'nom': 'dupont', 'prenom': 'jean'})

    def test_set_functions(self):
        s = SQLGenerator()
        params = {'nom': 'dupont', 'prenom': 'jean', 'age': SQLExpression('YEARS(%(date)s)', date='2013/01/01')}
        self.assertEqual(s.set(params), 'age = YEARS(%(date)s), nom = %(nom)s, prenom = %(prenom)s')
        self.assertEqual(params, {'nom': 'dupont', 'prenom': 'jean', 'date': '2013/01/01'})

    def test_where_values(self):
        s = SQLGenerator()
        self.assertEqual(s.where(['nom']), 'nom = %(nom)s')
        self.assertEqual(s.where(['nom','prenom']), 'nom = %(nom)s AND prenom = %(prenom)s')
        self.assertEqual(s.where(['nom','prenom'], 'x.id = y.id'),
                         'x.id = y.id AND nom = %(nom)s AND prenom = %(prenom)s')
        params = {'nom': 'dupont', 'prenom': 'jean'}
        self.assertEqual(s.where(params), 'nom = %(nom)s AND prenom = %(prenom)s')
        self.assertEqual(s.where(params, 'x.id = y.id'),
                         'x.id = y.id AND nom = %(nom)s AND prenom = %(prenom)s')

    def test_where_functions(self):
        s = SQLGenerator()
        params = {'nom': 'dupont', 'prenom': 'jean', 'age': SQLExpression('YEARS(%(date)s)', date='2013/01/01')}
        self.assertEqual(s.where(params), 'age = YEARS(%(date)s) AND nom = %(nom)s AND prenom = %(prenom)s')
        self.assertEqual(params, {'nom': 'dupont', 'prenom': 'jean', 'date': '2013/01/01'})
        params = {'nom': 'dupont', 'prenom': 'jean', 'age': SQLExpression('YEARS(%(date)s)', date='2013/01/01')}
        self.assertEqual(s.where(params, 'x.id = y.id'),
                         'x.id = y.id AND age = YEARS(%(date)s) AND nom = %(nom)s AND prenom = %(prenom)s')
        self.assertEqual(params, {'nom': 'dupont', 'prenom': 'jean', 'date': '2013/01/01'})

    def test_insert_values(self):
        s = SQLGenerator()
        params = {'nom': 'dupont'}
        sqlstr = s.insert('test', params)
        self.assertEqual(sqlstr, 'INSERT INTO test ( nom ) VALUES ( %(nom)s )')
        self.assertEqual(params, {'nom': 'dupont'})

    def test_insert_functions(self):
        s = SQLGenerator()
        params = {'nom':'dupont', 'prenom':'jean',
                  'age': SQLExpression('YEARS(%(date)s)', date='2013/01/01')}
        sqlstr = s.insert('test', params)
        self.assertEqual(sqlstr,  'INSERT INTO test ( age, nom, prenom ) VALUES '
                         '( YEARS(%(date)s), %(nom)s, %(prenom)s )')
        self.assertEqual(params, {'nom':'dupont', 'prenom':'jean', 'date': '2013/01/01'})

    def test_select_values(self):
        s = SQLGenerator()
        self.assertEqual(s.select('test',{}), 'SELECT * FROM test')
        self.assertEqual(s.select('test',{'nom':'dupont'}),
                         'SELECT * FROM test WHERE nom = %(nom)s')
        self.assertEqual(s.select('test',{'nom':'dupont','prenom':'jean'}),
                         'SELECT * FROM test WHERE nom = %(nom)s AND prenom = %(prenom)s')

    def test_select_functions(self):
        s = SQLGenerator()
        params = {'nom':'dupont', 'prenom':'jean',
                  'age': SQLExpression('YEARS(%(date)s)', date='2013/01/01')}
        self.assertEqual(s.select('test', params),
                         'SELECT * FROM test WHERE age = YEARS(%(date)s) '
                         'AND nom = %(nom)s AND prenom = %(prenom)s')
        self.assertEqual(params, {'nom': 'dupont', 'prenom': 'jean', 'date': '2013/01/01'})

    def test_adv_select_values(self):
        s = SQLGenerator()
        self.assertEqual(s.adv_select(['column'],[('test', 't')], {}),
                         'SELECT column FROM test AS t')
        self.assertEqual( s.adv_select(['column'],[('test', 't')], {'nom':'dupont'}),
                          'SELECT column FROM test AS t WHERE nom = %(nom)s')

    def test_adv_select_functions(self):
        s = SQLGenerator()
        params = {'nom':'dupont', 'prenom':'jean',
                  'age': SQLExpression('YEARS(%(date)s)', date='2013/01/01')}
        self.assertEqual( s.adv_select(['column'],[('test', 't')], params),
                          'SELECT column FROM test AS t WHERE age = YEARS(%(date)s) '
                         'AND nom = %(nom)s AND prenom = %(prenom)s')
        self.assertEqual(params, {'nom': 'dupont', 'prenom': 'jean', 'date': '2013/01/01'})

    def test_delete_values(self):
        s = SQLGenerator()
        self.assertEqual(s.delete('test',{'nom':'dupont'}),
                         'DELETE FROM test WHERE nom = %(nom)s')
        self.assertEqual(s.delete('test',{'nom':'dupont','prenom':'jean'}),
                         'DELETE FROM test WHERE nom = %(nom)s AND prenom = %(prenom)s')

    def test_delete_functions(self):
        s = SQLGenerator()
        params = {'nom':'dupont', 'prenom':'jean',
                  'age': SQLExpression('YEARS(%(date)s)', date='2013/01/01')}
        self.assertEqual( s.delete('test', params),
                          'DELETE FROM test WHERE age = YEARS(%(date)s) '
                         'AND nom = %(nom)s AND prenom = %(prenom)s')
        self.assertEqual(params, {'nom': 'dupont', 'prenom': 'jean', 'date': '2013/01/01'})

    def test_delete_many_values(self):
        s = SQLGenerator()
        params = {'nom':'dupont', 'eid': '(1, 2, 3)'}
        self.assertEqual(s.delete_many('test', params),
                         'DELETE FROM test WHERE eid IN (1, 2, 3) AND nom = %(nom)s')
        self.assertEqual(params, {'nom':'dupont'})

    def test_delete_many_functions(self):
        s = SQLGenerator()
        params = {'nom':'dupont', 'prenom':'jean', 'eid': '(1, 2, 3)',
                  'age': SQLExpression('YEARS(%(date)s)', date='2013/01/01')}
        self.assertEqual( s.delete_many('test', params),
                          'DELETE FROM test WHERE eid IN (1, 2, 3) AND age = YEARS(%(date)s) '
                          'AND nom = %(nom)s AND prenom = %(prenom)s')
        self.assertEqual(params, {'nom': 'dupont', 'prenom': 'jean', 'date': '2013/01/01'})

    def test_update_values(self):
        s = SQLGenerator()
        self.assertEqual(s.update('test', {'id':'001','nom':'dupont'}, ['id']),
                         'UPDATE test SET nom = %(nom)s WHERE id = %(id)s')
        self.assertEqual(s.update('test',{'id':'001','nom':'dupont','prenom':'jean'},['id']),
                         'UPDATE test SET nom = %(nom)s, prenom = %(prenom)s WHERE id = %(id)s')

    def test_update_functions(self):
        s = SQLGenerator()
        params = {'id': '001', 'nom':'dupont', 'prenom':'jean',
                  'age': SQLExpression('YEARS(%(date)s)', date='2013/01/01')}
        self.assertEqual( s.update('test', params, ['id']),
                          'UPDATE test SET age = YEARS(%(date)s), nom = %(nom)s, '
                          'prenom = %(prenom)s WHERE id = %(id)s')
        self.assertEqual(params, {'nom': 'dupont', 'prenom': 'jean', 'date': '2013/01/01', 'id': '001'})

if __name__ == '__main__':
    unittest.main()
