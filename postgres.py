"""Postgres RDBMS support

Supported drivers, in order of preference:
- psycopg2 (recommended, others are not well tested)
- psycopg
- pgdb
- pyPgSQL

Full-text search based on the tsearch2 extension from the openfts project
(see http://openfts.sourceforge.net/)

Warning: you will need to run the tsearch2.sql script with super user privileges
on the database.

:copyright: 2002-2010 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: General Public License version 2 - http://www.gnu.org/licenses
"""
__docformat__ = "restructuredtext en"

from os.path import join, dirname, isfile
from warnings import warn

from logilab import database as db
from logilab.database.fti import normalize_words, tokenize


TSEARCH_SCHEMA_PATH = ('/usr/share/postgresql/?.?/contrib/tsearch2.sql', # current debian
                       '/usr/lib/postgresql/share/contrib/tsearch2.sql',
                       '/usr/share/postgresql/contrib/tsearch2.sql',
                       '/usr/lib/postgresql-?.?/share/contrib/tsearch2.sql',
                       '/usr/share/postgresql-?.?/contrib/tsearch2.sql',
                       join(dirname(__file__), 'tsearch2.sql'),
                       'tsearch2.sql')


class _PgdbAdapter(db.DBAPIAdapter):
    """Simple PGDB Adapter to DBAPI (pgdb modules lacks Binary() and NUMBER)
    """
    def __init__(self, native_module, pywrap=False):
        db.DBAPIAdapter.__init__(self, native_module, pywrap)
        self.NUMBER = native_module.pgdbType('int2', 'int4', 'serial',
                                             'int8', 'float4', 'float8',
                                             'numeric', 'bool', 'money')

    def connect(self, host='', database='', user='', password='', port='', extra_args=None):
        """Wraps the native module connect method"""
        if port:
            warn("pgdb doesn't support 'port' parameter in connect()", UserWarning)
        kwargs = {'host' : host, 'database' : database,
                  'user' : user, 'password' : password}
        cnx = self._native_module.connect(**kwargs)
        return self._wrap_if_needed(cnx)


class _PsycopgAdapter(db.DBAPIAdapter):
    """Simple Psycopg Adapter to DBAPI (cnx_string differs from classical ones)
    """
    def connect(self, host='', database='', user='', password='', port='', extra_args=None):
        """Handles psycopg connection format"""
        if host:
            cnx_string = 'host=%s  dbname=%s  user=%s' % (host, database, user)
        else:
            cnx_string = 'dbname=%s  user=%s' % (database, user)
        if port:
            cnx_string += ' port=%s' % port
        if password:
            cnx_string = '%s password=%s' % (cnx_string, password)
        cnx = self._native_module.connect(cnx_string)
        cnx.set_isolation_level(1)
        return self._wrap_if_needed(cnx)


class _Psycopg2Adapter(_PsycopgAdapter):
    """Simple Psycopg2 Adapter to DBAPI (cnx_string differs from classical ones)
    """
    # not defined in psycopg2.extensions
    # "select typname from pg_type where oid=705";
    UNKNOWN = 705

    def __init__(self, native_module, pywrap=False):
        from psycopg2 import extensions
        self.BOOLEAN = extensions.BOOLEAN
        db.DBAPIAdapter.__init__(self, native_module, pywrap)
        self._init_psycopg2()

    def _init_psycopg2(self):
        """initialize psycopg2 to use mx.DateTime for date and timestamps
        instead for datetime.datetime"""
        psycopg2 = self._native_module
        if hasattr(psycopg2, '_lc_initialized'):
            return
        psycopg2._lc_initialized = 1
        # use mxDateTime instead of datetime if available
        if db.USE_MX_DATETIME:
            from psycopg2 import extensions
            extensions.register_type(psycopg2._psycopg.MXDATETIME)
            extensions.register_type(psycopg2._psycopg.MXINTERVAL)
            extensions.register_type(psycopg2._psycopg.MXDATE)
            extensions.register_type(psycopg2._psycopg.MXTIME)
            # StringIO/cStringIO adaptation
            # XXX (syt) todo, see my december discussion on the psycopg2 list
            # for a working solution
            #def adapt_stringio(stringio):
            #    print 'ADAPTING', stringio
            #    return psycopg2.Binary(stringio.getvalue())
            #import StringIO
            #extensions.register_adapter(StringIO.StringIO, adapt_stringio)
            #import cStringIO
            #extensions.register_adapter(cStringIO.StringIO, adapt_stringio)


class _PgsqlAdapter(db.DBAPIAdapter):
    """Simple pyPgSQL Adapter to DBAPI
    """
    def connect(self, host='', database='', user='', password='', port='', extra_args=None):
        """Handles psycopg connection format"""
        kwargs = {'host' : host, 'port': port or None,
                  'database' : database,
                  'user' : user, 'password' : password or None}
        cnx = self._native_module.connect(**kwargs)
        return self._wrap_if_needed(cnx)


    def Binary(self, string):
        """Emulates the Binary (cf. DB-API) function"""
        return str

    def __getattr__(self, attrname):
        # __import__('pyPgSQL.PgSQL', ...) imports the toplevel package
        return getattr(self._native_module, attrname)


db._PREFERED_DRIVERS['postgres'] = [
    #'logilab.database._pyodbcwrap',
    'psycopg2', 'psycopg', 'pgdb', 'pyPgSQL.PgSQL',
    ]
db._ADAPTER_DIRECTORY['postgres'] = {
    'pgdb' : _PgdbAdapter,
    'psycopg' : _PsycopgAdapter,
    'psycopg2' : _Psycopg2Adapter,
    'pyPgSQL.PgSQL' : _PgsqlAdapter,
    }



class _PGAdvFuncHelper(db._GenericAdvFuncHelper):
    """Postgres helper, taking advantage of postgres SEQUENCE support
    """
    backend_name = 'postgres'

    def pgdbcmd(self, cmd, dbhost, dbport, dbuser, *args):
        cmd = [cmd]
        cmd += args
        if dbhost or self.dbhost:
            cmd.append('--host=%s' % (dbhost or self.dbhost))
        if dbport or self.dbport:
            cmd.append('--port=%s' % (dbport or self.dbport))
        if dbuser or self.dbuser:
            cmd.append('--username=%s' % (dbuser or self.dbuser))
        return cmd

    def system_database(self):
        """return the system database for the given driver"""
        return 'template1'

    def backup_commands(self, backupfile, keepownership=True,
                        dbname=None, dbhost=None, dbport=None, dbuser=None):
        cmd = self.pgdbcmd('pg_dump', dbhost, dbport, dbuser, '-Fc')
        if not keepownership:
            cmd.append('--no-owner')
        cmd.append('--file')
        cmd.append(backupfile)
        cmd.append(dbname or self.dbname)
        return [cmd]

    def restore_commands(self, backupfile, keepownership=True, drop=True,
                         dbname=None, dbhost=None, dbport=None, dbuser=None,
                         dbencoding=None):
        dbname = dbname or self.dbname
        cmds = []
        if drop:
            cmd = self.pgdbcmd('dropdb', dbhost, dbport, dbuser)
            cmd.append(dbname)
            cmds.append(cmd)
        cmd = self.pgdbcmd('createdb', dbhost, dbport, dbuser,
                           '-T', 'template0',
                           '-E', dbencoding or self.dbencoding)
        cmd.append(dbname)
        cmds.append(cmd)
        cmd = self.pgdbcmd('pg_restore', dbhost, dbport, dbuser, '-Fc')
        cmd.append('--dbname')
        cmd.append(dbname)
        if not keepownership:
            cmd.append('--no-owner')
        cmd.append(backupfile)
        cmds.append(cmd)
        return cmds

    def sql_create_sequence(self, seq_name):
        return 'CREATE SEQUENCE %s;' % seq_name

    def sql_drop_sequence(self, seq_name):
        return 'DROP SEQUENCE %s;' % seq_name

    def sqls_increment_sequence(self, seq_name):
        return ("SELECT nextval('%s');" % seq_name,)

    def sql_temporary_table(self, table_name, table_schema,
                            drop_on_commit=True):
        if not drop_on_commit:
            return "CREATE TEMPORARY TABLE %s (%s);" % (table_name,
                                                        table_schema)
        return "CREATE TEMPORARY TABLE %s (%s) ON COMMIT DROP;" % (table_name,
                                                                   table_schema)

    def create_database(self, cursor, dbname, owner=None, dbencoding=None):
        """create a new database"""
        sql = "CREATE DATABASE %(dbname)s"
        if owner:
            sql += " WITH OWNER=%(owner)s"
        dbencoding = dbencoding or self.dbencoding
        if dbencoding:
            sql += " ENCODING='%(dbencoding)s'"
        cursor.execute(sql % locals())

    def create_language(self, cursor, extlang):
        """postgres specific method to install a procedural language on a database"""
        # make sure plpythonu is not directly in template1
        cursor.execute("SELECT * FROM pg_language WHERE lanname='%s';" % extlang)
        if cursor.fetchall():
            print '%s language already installed' % extlang
        else:
            cursor.execute('CREATE LANGUAGE %s' % extlang)
            print '%s language installed' % extlang

    def list_users(self, cursor):
        """return the list of existing database users"""
        cursor.execute("SELECT usename FROM pg_user")
        return [r[0] for r in cursor.fetchall()]

    def list_databases(self, cursor):
        """return the list of existing databases"""
        cursor.execute('SELECT datname FROM pg_database')
        return [r[0] for r in cursor.fetchall()]

    def list_tables(self, cursor):
        """return the list of tables of a database"""
        cursor.execute("SELECT tablename FROM pg_tables")
        return [r[0] for r in cursor.fetchall()]

    def list_indices(self, cursor, table=None):
        """return the list of indices of a database, only for the given table if specified"""
        sql = "SELECT indexname FROM pg_indexes"
        if table:
            sql += " WHERE LOWER(tablename)='%s'" % table.lower()
        cursor.execute(sql)
        return [r[0] for r in cursor.fetchall()]

    # full-text search customization ###########################################

    fti_table = 'appears'
    fti_need_distinct = False
    config = 'default'
    max_indexed = 500000 # 500KB, avoid "string is too long for tsvector"

    def has_fti_table(self, cursor):
        if super(_PGAdvFuncHelper, self).has_fti_table(cursor):
            cursor.execute('SELECT version()')
            version = cursor.fetchone()[0].split()[1].split(',')[0]
            version = [int(i) for i in version.split('.')]
            if version >= [8, 3, 0]:
                self.config = 'simple'
            else:
                self.config = 'default'
        return self.fti_table in self.list_tables(cursor)

    def cursor_index_object(self, uid, obj, cursor):
        """Index an object, using the db pointed by the given cursor.
        """
        uid = int(uid)
        words = normalize_words(obj.get_words())
        size = 0
        for i, word in enumerate(words):
            size += len(word) + 1
            if size > self.max_indexed:
                words = words[:i]
                break
        if words:
            cursor.execute("INSERT INTO appears(uid, words) "
                           "VALUES (%(uid)s,to_tsvector(%(config)s, %(wrds)s));",
                           {'config': self.config, 'uid':uid, 'wrds': ' '.join(words)})

    def fulltext_search(self, querystr, cursor=None):
        """Execute a full text query and return a list of 2-uple (rating, uid).
        """
        if isinstance(querystr, str):
            querystr = unicode(querystr, self.dbencoding)
        words = normalize_words(tokenize(querystr))
        cursor = cursor or self._cnx.cursor()
        cursor.execute('SELECT 1, uid FROM appears '
                       "WHERE words @@ to_tsquery(%(config)s, %(words)s)",
                       {'config': self.config, 'words': '&'.join(words)})
        return cursor.fetchall()

    def fti_restriction_sql(self, tablename, querystr, jointo=None, not_=False):
        """Execute a full text query and return a list of 2-uple (rating, uid).
        """
        if isinstance(querystr, str):
            querystr = unicode(querystr, self.dbencoding)
        words = normalize_words(tokenize(querystr))
        # XXX replace '%' since it makes tsearch fail, dunno why yet, should
        # be properly fixed
        searched = '&'.join(words).replace('%', '')
        sql = "%s.words @@ to_tsquery('%s', '%s')" % (tablename, self.config, searched)
        if not_:
            sql = 'NOT (%s)' % sql
        if jointo is None:
            return sql
        return "%s AND %s.uid=%s" % (sql, tablename, jointo)

    # XXX not needed with postgres >= 8.3 right?
    def find_tsearch2_schema(self):
        """Looks up for tsearch2.sql in a list of default paths.
        """
        import glob
        for path in TSEARCH_SCHEMA_PATH:
            for fullpath in glob.glob(path):
                if isfile(fullpath):
                    # tsearch2.sql found !
                    return fullpath
        raise RuntimeError("can't find tsearch2.sql")

    def init_fti_extensions(self, cursor, owner=None):
        """If necessary, install extensions at database creation time.

        For postgres, install tsearch2 if not installed by the template.
        """
        tstables = []
        for table in self.list_tables(cursor):
            if table.startswith('pg_ts'):
                tstables.append(table)
        if tstables:
            print 'pg_ts_dict already present, do not execute tsearch2.sql'
            if owner:
                print 'reset pg_ts* owners'
                for table in tstables:
                    cursor.execute('ALTER TABLE %s OWNER TO %s' % (table, owner))
        else:
            fullpath = self.find_tsearch2_schema()
            cursor.execute(open(fullpath).read())
            print 'tsearch2.sql installed'

    def sql_init_fti(self):
        """Return the sql definition of table()s used by the full text index.

        Require extensions to be already in.
        """
        # XXX create GIN or GIST index, see FTS wiki
        return """
CREATE table appears(
  uid     INTEGER PRIMARY KEY NOT NULL,
  words   tsvector
);
"""

    def sql_drop_fti(self):
        """Drop tables used by the full text index."""
        return 'DROP TABLE appears;'

    def sql_grant_user_on_fti(self, user):
        return 'GRANT ALL ON appears TO %s;' % (user)


db._ADV_FUNC_HELPER_DIRECTORY['postgres'] = _PGAdvFuncHelper
