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
"""Help to generate SQL strings usable by the Python DB-API.

"""
__docformat__ = "restructuredtext en"

from six.moves import range

# SQLGenerator ################################################################

class SQLExpression(object):
    """Use this class when you need direct SQL expression in statements
    generated by SQLGenerator. Arguments:

    - a sqlstring that defines the SQL expression to be used, e.g. 'YEARS(%(date)s)'

    - kwargs that define the values to be substituted in the SQL expression,
      e.g. date='2013/01/01'

    E.g. the SQL expression SQLExpression('YEARS(%(date)s)', date='2013/01/01')
    will yield:

    '..., age = YEARS(%(date)s), ...' in a SQL statement

    and will modify accordingly the parameters:

    {'date': '2013/01/01', ...}
    """

    def __init__(self, sqlstring, **kwargs):
        self.sqlstring = sqlstring
        self.kwargs = kwargs


class SQLGenerator :
    """
    Helper class to generate SQL strings to use with python's DB-API.
    """
    def _iterate_params(self, params):
        """ Iterate a parameters dictionnary and yield the correct column name
        and value (base types or SQL functions) """
        # sort for predictability
        for column, value in sorted(params.items()):
            if isinstance(value, SQLExpression):
                # In this case the value that should be substitued
                # is not anymore the one in params, but is passed as kwargs
                # in the SQLExpression
                # E.g. 'age': SQLExpression('YEARS(%(date)s)', date='2013/01/01')
                # will create the statement
                # age = YEARS(%(date)s)
                # and thus, the params dictionnary should have a 'date': '2013/01/01'
                # for correct substitution
                params.update(value.kwargs)
                params.pop(column)
                yield column, value.sqlstring
            else:
                yield column, "%%(%s)s" % column

    def where(self, keys, addon=None):
        """
        :param keys: list of keys
        :param addon: additional sql statement

        >>> s = SQLGenerator()
        >>> s.where(['nom'])
        'nom = %(nom)s'
        >>> s.where(['nom','prenom'])
        'nom = %(nom)s AND prenom = %(prenom)s'
        >>> s.where(['nom','prenom'], 'x.id = y.id')
        'x.id = y.id AND nom = %(nom)s AND prenom = %(prenom)s'
        """
        # Do not need SQLExpression here, as we have the addon argument.
        if isinstance(keys, dict):
            restriction = ["%s = %s" % (col, val) for col, val in self._iterate_params(keys)]
        else:
            restriction = ["%s = %%(%s)s" % (x, x) for x in keys]
        if addon:
            restriction.insert(0, addon)
        return " AND ".join(restriction)

    def set(self, keys):
        """
        :param keys: list of keys

        >>> s = SQLGenerator()
        >>> s.set(['nom'])
        'nom = %(nom)s'
        >>> s.set(['nom','prenom'])
        'nom = %(nom)s, prenom = %(prenom)s'
        """
        if isinstance(keys, dict):
            set_parts = ["%s = %s" % (col, val) for col, val in self._iterate_params(keys)]
        else:
            set_parts = ["%s = %%(%s)s" % (x, x) for x in keys]
        return ", ".join(set_parts)

    def insert(self, table, params):
        """
        :param table: name of the table
        :param params:  dictionary that will be used as in cursor.execute(sql,params)
        >>> s = SQLGenerator()
        >>> s.insert('test',{'nom':'dupont'})
        'INSERT INTO test ( nom ) VALUES ( %(nom)s )'
        >>> params = {'nom':'dupont', 'prenom':'jean',
        ...          'age': SQLExpression('YEARS(%(date)s)', date='2013/01/01')}
        >>> s.insert('test', params)
        'INSERT INTO test ( age, nom, prenom ) VALUES ( YEARS(%(date)s), %(nom)s, %(prenom)s )'
        >>> params['date'] # params has been modified
        '2013/01/01'
        """
        columns = []
        values = []
        # sort for predictability
        for column, value in self._iterate_params(params):
            columns.append(column)
            values.append(value)
        sql = 'INSERT INTO %s ( %s ) VALUES ( %s )' % (table, ', '.join(columns), ', '.join(values))
        return sql

    def select(self, table, params=None, selection=None):
        """
        :param table: name of the table
        :param params:  dictionary that will be used as in cursor.execute(sql,params)

        >>> s = SQLGenerator()
        >>> s.select('test',{})
        'SELECT * FROM test'
        >>> s.select('test',{'nom':'dupont'})
        'SELECT * FROM test WHERE nom = %(nom)s'
        >>> s.select('test',{'nom':'dupont','prenom':'jean'})
        'SELECT * FROM test WHERE nom = %(nom)s AND prenom = %(prenom)s'
        """
        if selection is None:
            sql = 'SELECT * FROM %s' % table
        else:
            sql = 'SELECT %s FROM %s' % (','.join(col for col in selection), table)
        if params is not None:
            where = self.where(params)
            if where :
                sql = sql + ' WHERE %s' % where
        return sql

    def adv_select(self, model, tables, params, joins=None) :
        """
        :param model:  list of columns to select
        :param tables: list of tables used in from
        :param params: dictionary that will be used as in cursor.execute(sql, params)
        :param joins:  optional list of restriction statements to insert in the
          where clause. Usually used to perform joins.

        >>> s = SQLGenerator()
        >>> s.adv_select(['column'],[('test', 't')], {})
        'SELECT column FROM test AS t'
        >>> s.adv_select(['column'],[('test', 't')], {'nom':'dupont'})
        'SELECT column FROM test AS t WHERE nom = %(nom)s'
        """
        table_names = ["%s AS %s" % (k, v) for k, v in tables]
        sql = 'SELECT %s FROM %s' % (', '.join(model), ', '.join(table_names))
        if joins and type(joins) != type(''):
            joins = ' AND '.join(joins)
        where = self.where(params, joins)
        if where :
            sql = sql + ' WHERE %s' % where
        return sql

    def delete(self, table, params, addon=None) :
        """
        :param table: name of the table
        :param params: dictionary that will be used as in cursor.execute(sql,params)

        >>> s = SQLGenerator()
        >>> s.delete('test',{'nom':'dupont'})
        'DELETE FROM test WHERE nom = %(nom)s'
        >>> s.delete('test',{'nom':'dupont','prenom':'jean'})
        'DELETE FROM test WHERE nom = %(nom)s AND prenom = %(prenom)s'
        """
        where = self.where(params, addon=addon)
        sql = 'DELETE FROM %s WHERE %s' % (table, where)
        return sql

    def delete_many(self, table, params):
        """ Delete many using the IN clause
        """
        addons = []
        for key, value in params.items():
            if not isinstance(value, SQLExpression) and value.startswith('('): # we want IN
                addons.append('%s IN %s' % (key, value))
                # The value is pop as it is not needed for substitution
                # (the value is directly written in the SQL IN statement)
                params.pop(key)
        return self.delete(table, params, addon=' AND '.join(addons))

    def update(self, table, params, unique) :
        """
        :param table: name of the table
        :param params: dictionary that will be used as in cursor.execute(sql,params)

        >>> s = SQLGenerator()
        >>> s.update('test', {'id':'001','nom':'dupont'}, ['id'])
        'UPDATE test SET nom = %(nom)s WHERE id = %(id)s'
        >>> s.update('test',{'id':'001','nom':'dupont','prenom':'jean'},['id'])
        'UPDATE test SET nom = %(nom)s, prenom = %(prenom)s WHERE id = %(id)s'
        """
        where = self.where(unique)
        # Remove the unique keys from the params dictionnary
        unique_params = {}
        for key, value in params.items():
            if key in unique:
                params.pop(key)
                unique_params[key] = value
        set = self.set(params)
        # Add the removed unique params to the (now possibly updated)
        # params dict (if there were some SQLExpressions)
        params.update(unique_params)
        sql = 'UPDATE %s SET %s WHERE %s' % (table, set, where)
        return sql


class BaseTable:
    """
    Another helper class to ease SQL table manipulation.
    """
    # table_name = "default"
    # supported types are s/i/d
    # table_fields = ( ('first_field','s'), )
    # primary_key = 'first_field'

    def __init__(self, table_name, table_fields, primary_key=None):
        if primary_key is None:
            self._primary_key = table_fields[0][0]
        else:
            self._primary_key = primary_key

        self._table_fields = table_fields
        self._table_name = table_name
        info = {
            'key' : self._primary_key,
            'table' : self._table_name,
            'columns' : ",".join( [ f for f,t in self._table_fields ] ),
            'values' : ",".join( [sql_repr(t, "%%(%s)s" % f)
                                  for f,t in self._table_fields] ),
            'updates' : ",".join( ["%s=%s" % (f, sql_repr(t, "%%(%s)s" % f))
                                   for f,t in self._table_fields] ),
            }
        self._insert_stmt = ("INSERT into %(table)s (%(columns)s) "
                             "VALUES (%(values)s) WHERE %(key)s=%%(key)s") % info
        self._update_stmt = ("UPDATE %(table)s SET (%(updates)s) "
                             "VALUES WHERE %(key)s=%%(key)s") % info
        self._select_stmt = ("SELECT %(columns)s FROM %(table)s "
                             "WHERE %(key)s=%%(key)s") % info
        self._delete_stmt = ("DELETE FROM %(table)s "
                             "WHERE %(key)s=%%(key)s") % info

        for k, t in table_fields:
            if hasattr(self, k):
                raise ValueError("Cannot use %s as a table field" % k)
            setattr(self, k, None)


    def as_dict(self):
        d = {}
        for k, t in self._table_fields:
            d[k] = getattr(self, k)
        return d

    def select(self, cursor):
        d = { 'key' : getattr(self, self._primary_key) }
        cursor.execute(self._select_stmt % d)
        rows = cursor.fetchall()
        if len(rows)!=1:
            msg = "Select: ambiguous query returned %d rows"
            raise ValueError(msg % len(rows))
        for (f, t), v in zip(self._table_fields, rows[0]):
            setattr(self, f, v)

    def update(self, cursor):
        d = self.as_dict()
        cursor.execute(self._update_stmt % d)

    def delete(self, cursor):
        d = { 'key' : getattr(self, self._primary_key) }
        cursor.execute(self._delete_stmt % d)


# Helper functions #############################################################

def name_fields(cursor, records) :
    """
    Take a cursor and a list of records fetched with that cursor, then return a
    list of dictionaries (one for each record) whose keys are column names and
    values are records' values.

    :param cursor: cursor used to execute the query
    :param records: list returned by fetch*()
    """
    result = []
    for record in records :
        record_dict = {}
        for i in range(len(record)) :
            record_dict[cursor.description[i][0]] = record[i]
        result.append(record_dict)
    return result

def sql_repr(type, val):
    if type == 's':
        return "'%s'" % (val,)
    else:
        return val


if __name__ == "__main__":
    import doctest
    from logilab.database import sqlgen
    print doctest.testmod(sqlgen)
