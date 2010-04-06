"""Wrappers to get actually replaceable DBAPI2 compliant modules and
database connection whatever the database and client lib used.

Currently support:

- postgresql (pgdb, psycopg, psycopg2, pyPgSQL)
- mysql (MySQLdb)
- sqlite (pysqlite2, sqlite, sqlite3)

just use the `get_connection` function from this module to get a
wrapped connection.  If multiple drivers for a database are available,
you can control which one you want to use using the
`set_prefered_driver` function.

Additional helpers are also provided for advanced functionalities such
as listing existing users or databases, creating database... Get the
helper for your database using the `get_db_helper` function.

:copyright: 2002-2010 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: General Public License version 2 - http://www.gnu.org/licenses
"""
__docformat__ = "restructuredtext en"

import sys
import logging

from logilab.common.modutils import load_module_from_name

_LOGGER = logging.getLogger('logilab.database')

USE_MX_DATETIME = False

_PREFERED_DRIVERS = {}
_ADV_FUNC_HELPER_DIRECTORY = {}

def _ensure_module_loaded(driver):
    if driver in ('postgres', 'sqlite', 'mysql', 'sqlserver2005'):
        __import__('logilab.database.%s' % driver)
# main functions ###############################################################

def get_db_helper(driver):
    """returns an advanced function helper for the given driver"""
    _ensure_module_loaded(driver)
    return _ADV_FUNC_HELPER_DIRECTORY[driver]()

def get_dbapi_compliant_module(driver, prefered_drivers=None, quiet=False,
                               pywrap=False):
    """returns a fully dbapi compliant module"""
    _ensure_module_loaded(driver)
    try:
        mod = _ADAPTER_DIRECTORY.adapt(driver, prefered_drivers, pywrap=pywrap)
    except NoAdapterFound, err:
        if not quiet:
            msg = 'No Adapter found for %s, returning native module'
            print >> sys.stderr, msg % err.objname
        mod = err.adapted_obj
    return mod

def get_connection(driver='postgres', host='', database='', user='',
                  password='', port='', quiet=False, drivers=_PREFERED_DRIVERS,
                  pywrap=False, extra_args=None):
    """return a db connection according to given arguments"""
    _ensure_module_loaded(driver)
    module, modname = _import_driver_module(driver, drivers)
    try:
        adapter = _ADAPTER_DIRECTORY.get_adapter(driver, modname)
    except NoAdapterFound, err:
        if not quiet:
            msg = 'No Adapter found for %s, using default one' % err.objname
            print >> sys.stderr, msg
        adapted_module = DBAPIAdapter(module, pywrap)
    else:
        adapted_module = adapter(module, pywrap)
    if host and not port:
        try:
            host, port = host.split(':', 1)
        except ValueError:
            pass
    if port:
        port = int(port)
    return adapted_module.connect(host, database, user, password,
                                  port=port, extra_args=extra_args)

def set_prefered_driver(driver, module, _drivers=_PREFERED_DRIVERS):
    """sets the preferred driver module for driver
    driver is the name of the db engine (postgresql, mysql...)
    module is the name of the module providing the connect function
    syntax is (params_func, post_process_func_or_None)
    _drivers is a optional dictionary of drivers
    """
    _ensure_module_loaded(driver)
    try:
        modules = _drivers[driver]
    except KeyError:
        raise UnknownDriver('Unknown driver %s' % driver)
    # Remove module from modules list, and re-insert it in first position
    try:
        modules.remove(module)
    except ValueError:
        raise UnknownDriver('Unknown module %s for %s' % (module, driver))
    modules.insert(0, module)


# unified db api ###############################################################

class UnknownDriver(Exception):
    """raised when a unknown driver is given to get connection"""

class NoAdapterFound(Exception):
    """Raised when no Adapter to DBAPI was found"""
    def __init__(self, obj, objname=None, protocol='DBAPI'):
        if objname is None:
            objname = obj.__name__
        Exception.__init__(self, "Could not adapt %s to protocol %s" %
                           (objname, protocol))
        self.adapted_obj = obj
        self.objname = objname
        self._protocol = protocol


# _AdapterDirectory could be more generic by adding a 'protocol' parameter
# This one would become an adapter for 'DBAPI' protocol
class _AdapterDirectory(dict):
    """A simple dict that registers all adapters"""
    def register_adapter(self, adapter, driver, modname):
        """Registers 'adapter' in directory as adapting 'mod'"""
        try:
            driver_dict = self[driver]
        except KeyError:
            self[driver] = {}
        driver_dict[modname] = adapter

    def adapt(self, driver, prefered_drivers=None, pywrap=False):
        """Returns an dbapi-compliant object based for driver"""
        prefered_drivers = prefered_drivers or _PREFERED_DRIVERS
        module, modname = _import_driver_module(driver, prefered_drivers)
        try:
            return self[driver][modname](module, pywrap=pywrap)
        except KeyError:
            raise NoAdapterFound(obj=module)

    def get_adapter(self, driver, modname):
        try:
            return self[driver][modname]
        except KeyError:
            raise NoAdapterFound(None, modname)

_ADAPTER_DIRECTORY = _AdapterDirectory()
del _AdapterDirectory


def _import_driver_module(driver, drivers, quiet=True):
    """Imports the first module found in 'drivers' for 'driver'

    :rtype: tuple
    :returns: the tuple module_object, module_name where module_object
              is the dbapi module, and modname the module's name
    """
    if not driver in drivers:
        raise UnknownDriver(driver)
    for modname in drivers[driver]:
        try:
            if not quiet:
                print >> sys.stderr, 'Trying %s' % modname
            module = load_module_from_name(modname, use_sys=False)
            break
        except ImportError:
            if not quiet:
                print >> sys.stderr, '%s is not available' % modname
            continue
    else:
        raise ImportError('Unable to import a %s module' % driver)
    return module, modname


## base connection and cursor wrappers #####################

class _SimpleConnectionWrapper(object):
    """A simple connection wrapper in python to decorated C-level connections
    with additional attributes
    """
    def __init__(self, cnx):
        """Wraps the original connection object"""
        self._cnx = cnx

    # XXX : Would it work if only __getattr__ was defined
    def cursor(self):
        """Wraps cursor()"""
        return self._cnx.cursor()

    def commit(self):
        """Wraps commit()"""
        return self._cnx.commit()

    def rollback(self):
        """Wraps rollback()"""
        return self._cnx.rollback()

    def close(self):
        """Wraps close()"""
        return self._cnx.close()

    def __getattr__(self, attrname):
        return getattr(self._cnx, attrname)


class PyConnection(_SimpleConnectionWrapper):
    """A simple connection wrapper in python, generating wrapper for cursors as
    well (useful for profiling)
    """
    def __init__(self, cnx):
        """Wraps the original connection object"""
        self._cnx = cnx

    def cursor(self):
        """Wraps cursor()"""
        return PyCursor(self._cnx.cursor())


class PyCursor(object):
    """A simple cursor wrapper in python (useful for profiling)"""
    def __init__(self, cursor):
        self._cursor = cursor

    def close(self):
        """Wraps close()"""
        return self._cursor.close()

    def execute(self, *args, **kwargs):
        """Wraps execute()"""
        return self._cursor.execute(*args, **kwargs)

    def executemany(self, *args, **kwargs):
        """Wraps executemany()"""
        return self._cursor.executemany(*args, **kwargs)

    def fetchone(self, *args, **kwargs):
        """Wraps fetchone()"""
        return self._cursor.fetchone(*args, **kwargs)

    def fetchmany(self, *args, **kwargs):
        """Wraps execute()"""
        return self._cursor.fetchmany(*args, **kwargs)

    def fetchall(self, *args, **kwargs):
        """Wraps fetchall()"""
        return self._cursor.fetchall(*args, **kwargs)

    def __getattr__(self, attrname):
        return getattr(self._cursor, attrname)


## abstract class for dbapi adapters #######################

class DBAPIAdapter(object):
    """Base class for all DBAPI adapters"""
    UNKNOWN = None

    def __init__(self, native_module, pywrap=False):
        """
        :type native_module: module
        :param native_module: the database's driver adapted module
        """
        self._native_module = native_module
        self._pywrap = pywrap
        # optimization: copy type codes from the native module to this instance
        # since the .process_value method may be heavily used
        for typecode in ('STRING', 'BOOLEAN', 'BINARY', 'DATETIME', 'NUMBER',
                         'UNKNOWN'):
            try:
                setattr(self, typecode, getattr(self, typecode))
            except AttributeError:
                print >>sys.stderr, 'WARNING: %s adapter has no %s type code' \
                      % (self, typecode)

    def connect(self, host='', database='', user='', password='', port='',
                extra_args=None):
        """Wraps the native module connect method"""
        kwargs = {'host' : host, 'port' : port, 'database' : database,
                  'user' : user, 'password' : password}
        return self._wrap_if_needed(self._native_module.connect(**kwargs))

    def _wrap_if_needed(self, cnx):
        """Wraps the connection object if self._pywrap is True, and returns it
        If false, returns the original cnx object
        """
        if self._pywrap:
            cnx = PyConnection(cnx)
        return cnx

    def __getattr__(self, attrname):
        return getattr(self._native_module, attrname)

    def process_value(self, value, description, encoding='utf-8',
                      binarywrap=None):
        # if the dbapi module isn't supporting type codes, override to return
        # value directly
        typecode = description[1]
        assert typecode is not None, self
        if typecode == self.STRING:
            if isinstance(value, str):
                return unicode(value, encoding, 'replace')
        elif typecode == self.BOOLEAN:
            return bool(value)
        elif typecode == self.BINARY and not binarywrap is None:
            return binarywrap(value)
        elif typecode == self.UNKNOWN:
            # may occurs on constant selection for instance (e.g. SELECT 'hop')
            # with postgresql at least
            if isinstance(value, str):
                return unicode(value, encoding, 'replace')
        return value

    def binary_to_str(self, value):
        """turn raw value returned by the db-api module into a python string"""
        return str(value)

# advanced database helper #####################################################

from logilab.database.fti import FTIndexerMixIn

class BadQuery(Exception):
    pass
class UnsupportedFunction(BadQuery):
    pass
class UnknownFunction(BadQuery):
    pass

# set of hooks that should be called at connection opening time.
# mostly for sqlite'stored procedures that have to be registered...
SQL_CONNECT_HOOKS = {}
ALL_BACKENDS = object()


class FunctionDescr(object):
    supported_backends = ALL_BACKENDS
    rtype = None # None <-> returned type should be the same as the first argument
    aggregat = False
    minargs = 1
    maxargs = 1
    name_mapping = {}

    def __init__(self, name=None):
        if name is not None:
            name = name.upper()
        else:
            name = self.__class__.__name__.upper()
        self.name = name

    def add_support(self, backend):
        if self.supported_backends is not ALL_BACKENDS:
            self.supported_backends += (backend,)

    def check_nbargs(cls, nbargs):
        if cls.minargs is not None and \
               nbargs < cls.minargs:
            raise BadQuery('not enough argument for function %s' % cls.name)
        if cls.maxargs is not None and \
               nbargs < cls.maxargs:
            raise BadQuery('too many arguments for function %s' % cls.name)
    check_nbargs = classmethod(check_nbargs)

    def as_sql(self, backend, args):
        try:
            return getattr(self, 'as_sql_%s' % backend)(args)
        except AttributeError:
            funcname = self.name_mapping.get(backend, self.name)
            return '%s(%s)' % (funcname, ', '.join(args))

    def supports(self, backend):
        if self.supported_backends is ALL_BACKENDS or backend in self.supported_backends:
            return True
        return False


class AggrFunctionDescr(FunctionDescr):
    aggregat = True
    rtype = None

class MAX(AggrFunctionDescr): pass
class MIN(AggrFunctionDescr): pass
class SUM(AggrFunctionDescr): pass
class COUNT(AggrFunctionDescr):
    rtype = 'Int'

class AVG(AggrFunctionDescr):
    rtype = 'Float'

class UPPER(FunctionDescr):
    rtype = 'String'
class LOWER(FunctionDescr):
    rtype = 'String'
class IN(FunctionDescr):
    """this is actually a 'keyword' function..."""
    maxargs = None
class LENGTH(FunctionDescr):
    rtype = 'Int'

class DATE(FunctionDescr):
    rtype = 'Date'

class RANDOM(FunctionDescr):
    rtype = 'Float'
    minargs = maxargs = 0
    name_mapping = {'postgres': 'RANDOM',
                    'mysql': 'RAND',
                    }
class SUBSTRING(FunctionDescr):
    rtype = 'String'
    minargs = maxargs = 3
    name_mapping = {'postgres': 'SUBSTR',
                    'mysql': 'SUBSTRING',
                    'sqlite': 'SUBSTR',
                    'sqlserver': 'SUBSTRING'}

class ExtractDateField(FunctionDescr):
    rtype = 'Int'
    minargs = maxargs = 1
    field = None # YEAR, MONTH, DAY, etc.

    def as_sql_mysql(self, args):
        return 'EXTRACT(%s from %s)' % (self.field, ', '.join(args))

    def as_sql_postgres(self, args):
        return 'CAST(EXTRACT(%s from %s) AS INTEGER)' % (self.field, ', '.join(args))

class MONTH(ExtractDateField):
    field = 'MONTH'

class YEAR(ExtractDateField):
    field = 'YEAR'

class DAY(ExtractDateField):
    field = 'DAY'

class HOUR(ExtractDateField):
    field = 'HOUR'

class MINUTE(ExtractDateField):
    field = 'MINUTE'

class SECOND(ExtractDateField):
    field = 'SECOND'


class _FunctionRegistry(object):
    def __init__(self, registry=None):
        if registry is None:
            self.functions = {}
        else:
            self.functions = registry.functions.copy

    def register_function(self, funcdef, funcname=None):
        try:
            if issubclass(funcdef, FunctionDescr):
                funcdef = funcdef()
        except TypeError: # issubclass is quite strict
            pass
        assert isinstance(funcdef, FunctionDescr)
        funcname = funcname or funcdef.name
        self.functions[funcname] = funcdef

    def get_function(self, funcname):
        try:
            return self.functions[funcname.upper()]
        except KeyError:
            raise UnknownFunction(funcname)

    def get_backend_function(self, funcname, backend):
        funcdef = self.get_function(funcname)
        if funcdef.supports(backend):
            return funcdef
        raise UnsupportedFunction(funcname)

    def copy(self):
        registry = _FunctionRegistry()
        for funcname, funcdef in self.functions.items():
            registry.register_function(funcdef, funcname=funcname)
        return registry

SQL_FUNCTIONS_REGISTRY = _FunctionRegistry()

for func_class in (
    # aggregate functions
    MIN, MAX, SUM, COUNT, AVG,
    # transformation functions
    UPPER, LOWER, LENGTH, DATE, RANDOM,
    YEAR, MONTH, DAY, HOUR, MINUTE, SECOND, SUBSTRING,
    # keyword function
    IN):
    SQL_FUNCTIONS_REGISTRY.register_function(func_class())

def register_function(funcdef):
    """register the function `funcdef` on supported backends"""
    SQL_FUNCTIONS_REGISTRY.register_function(funcdef)


class _GenericAdvFuncHelper(FTIndexerMixIn):
    """Generic helper, trying to provide generic way to implement
    specific functionalities from others DBMS

    An exception is raised when the functionality is not emulatable
    """
    # 'canonical' types are `yams` types. This dictionnary map those types to
    # backend specific types
    TYPE_MAPPING = {
        'String' :   'text',
        'Int' :      'integer',
        'Float' :    'float',
        'Decimal' :  'decimal',
        'Boolean' :  'boolean',
        'Date' :     'date',
        'Time' :     'time',
        'Datetime' : 'timestamp',
        'Interval' : 'interval',
        'Password' : 'bytea',
        'Bytes' :    'bytea',
        }

    # DBMS resources descriptors and accessors
    backend_name = None # overridden in subclasses ('postgres', 'sqlite', etc.)
    needs_from_clause = False
    union_parentheses_support = True
    intersect_all_support = True
    users_support = True
    groups_support = True
    ilike_support = True
    alter_column_support = True
    case_sensitive = False

    # allow call to [backup|restore]_commands without previous call to
    # record_connection_information but by specifying argument explicitly
    dbhost = dbport = dbuser = dbpassword = dbextraargs = dbencoding = None

    def __init__(self, encoding='utf-8', _cnx=None):
        self.dbencoding = encoding
        self._cnx = _cnx

    def record_connection_info(self, dbname, dbhost=None, dbport=None,
                               dbuser=None, dbpassword=None, dbextraargs=None,
                               dbencoding=None):
        self.dbname = dbname
        self.dbhost = dbhost
        self.dbport = dbport
        self.dbuser = dbuser
        self.dbpasswd = dbpassword
        self.dbextraargs = dbextraargs
        if dbencoding:
            self.dbencoding = dbencoding
        self.dbapi_module = get_dbapi_compliant_module(self.backend_name)

    def get_connection(self, initcnx=True):
        """open and return a connection to the database

        you should first call record_connection_info to set connection
        paramaters.
        """
        if self.dbuser:
            _LOGGER.info('connecting to %s@%s for user %s', self.dbname,
                         self.dbhost or 'localhost', self.dbuser)
        else:
            _LOGGER.info('connecting to %s@%s', self.dbname,
                         self.dbhost or 'localhost')
        cnx = self.dbapi_module.connect(self.dbhost, self.dbname,
                                        self.dbuser,self.dbpasswd,
                                        port=self.dbport,
                                        extra_args=self.dbextraargs)
        if initcnx:
            for hook in SQL_CONNECT_HOOKS.get(self.backend_name, ()):
                hook(cnx)
        return cnx

    def set_connection(self, initcnx=True):
        self._cnx = self.get_connection(initcnx)

    @classmethod
    def function_description(cls, funcname):
        """return the description (`FunctionDescription`) for a SQL function"""
        return SQL_FUNCTIONS_REGISTRY.get_backend_function(
            funcname, cls.backend_name)

    def func_as_sql(self, funcname, args):
        funcdef = SQL_FUNCTIONS_REGISTRY.get_backend_function(
            funcname, self.backend_name)
        return funcdef.as_sql(self.backend_name, args)

    def system_database(self):
        """return the system database for the given driver"""
        raise NotImplementedError('not supported by this DBMS')

    def backup_commands(self, backupfile, keepownership=True,
                        dbname=None, dbhost=None, dbport=None, dbuser=None):
        """return a list of commands to backup the given database.

        Each command may be given as a list or as a string. In the latter case,
        expected to be used with a subshell (for instance using `os.system(cmd)`
        or `subprocess.call(cmd, shell=True)`
        """
        raise NotImplementedError('not supported by this DBMS')

    def restore_commands(self, backupfile, keepownership=True, drop=True,
                         dbname=None, dbhost=None, dbport=None, dbuser=None,
                         dbencoding=None):
        """return a list of commands to restore a backup of the given database


        Each command may be given as a list or as a string. In the latter case,
        expected to be used with a subshell (for instance using `os.system(cmd)`
        or `subprocess.call(cmd, shell=True)`
        """
        raise NotImplementedError('not supported by this DBMS')

    # helpers to standardize SQL according to the database

    def sql_current_date(self):
        return 'CURRENT_DATE'

    def sql_current_time(self):
        return 'CURRENT_TIME'

    def sql_current_timestamp(self):
        return 'CURRENT_TIMESTAMP'

    def sql_create_index(self, table, column, unique=False):
        idx = self._index_name(table, column, unique)
        if unique:
            return 'ALTER TABLE %s ADD UNIQUE(%s)' % (table, column)
        else:
            return 'CREATE INDEX %s ON %s(%s);' % (idx, table, column)

    def sql_drop_index(self, table, column, unique=False):
        idx = self._index_name(table, column, unique)
        if unique:
            return 'ALTER TABLE %s DROP CONSTRAINT %s' % (table, idx)
        else:
            return 'DROP INDEX %s' % idx

    def sql_create_sequence(self, seq_name):
        return '''CREATE TABLE %s (last INTEGER);
INSERT INTO %s VALUES (0);''' % (seq_name, seq_name)

    def sql_drop_sequence(self, seq_name):
        return 'DROP TABLE %s;' % seq_name

    def sqls_increment_sequence(self, seq_name):
        return ('UPDATE %s SET last=last+1;' % seq_name,
                'SELECT last FROM %s;' % seq_name)

    def sql_rename_col(self, table, column, newname, coltype, null_allowed):
        return 'ALTER TABLE %s RENAME COLUMN %s TO %s' % (
            table, column, newname)

    def sql_change_col_type(self, table, column, coltype, null_allowed):
        return 'ALTER TABLE %s ALTER COLUMN %s TYPE %s' % (
            table, column, coltype)

    def sql_set_null_allowed(self, table, column, coltype, null_allowed):
        cmd = null_allowed and 'DROP' or 'SET'
        return 'ALTER TABLE %s ALTER COLUMN %s %s NOT NULL' % (
            table, column, cmd)

    def temporary_table_name(self, table_name):
        """
        return a temporary table name constructed from the table_name argument
        (e.g. for SQL Server, prepend a '#' to the name)
        Standard implementation returns the argument unchanged. 
        """
        return table_name


    def sql_temporary_table(self, table_name, table_schema,
                            drop_on_commit=True):
        table_name = self.temporary_table_name(table_name)
        return "CREATE TEMPORARY TABLE %s (%s);" % (table_name, table_schema)

    def boolean_value(self, value):
        if value:
            return 'TRUE'
        else:
            return 'FALSE'

    def binary_value(self, value):
        return value

    def increment_sequence(self, cursor, seq_name):
        for sql in self.sqls_increment_sequence(seq_name):
            cursor.execute(sql)
        return cursor.fetchone()[0]

    def create_user(self, cursor, user, password):
        """create a new database user"""
        if not self.users_support:
            raise NotImplementedError('not supported by this DBMS')
        cursor.execute("CREATE USER %(user)s "
                       "WITH PASSWORD '%(password)s'" % locals())

    def _index_name(self, table, column, unique=False):
        if unique:
            # note: this naming is consistent with indices automatically
            # created by postgres when UNIQUE appears in a table schema
            return '%s_%s_key' % (table.lower(), column.lower())
        else:
            return '%s_%s_idx' % (table.lower(), column.lower())

    def create_index(self, cursor, table, column, unique=False):
        if not self.index_exists(cursor, table, column, unique):
            cursor.execute(self.sql_create_index(table, column, unique))

    def drop_index(self, cursor, table, column, unique=False):
        if self.index_exists(cursor, table, column, unique):
            cursor.execute(self.sql_drop_index(table, column, unique))

    def index_exists(self, cursor, table, column, unique=False):
        idx = self._index_name(table, column, unique)
        return idx in self.list_indices(cursor, table)

    def user_exists(self, cursor, username):
        """return True if a user with the given username exists"""
        return username in self.list_users(cursor)

    def list_users(self, cursor):
        """return the list of existing database users"""
        raise NotImplementedError('not supported by this DBMS')

    def create_database(self, cursor, dbname, owner=None, dbencoding=None):
        """create a new database"""
        raise NotImplementedError('not supported by this DBMS')

    def list_databases(self):
        """return the list of existing databases"""
        raise NotImplementedError('not supported by this DBMS')

    def list_tables(self, cursor):
        """return the list of tables of a database"""
        raise NotImplementedError('not supported by this DBMS')

    def list_indices(self, cursor, table=None):
        """return the list of indices of a database, only for the given table if specified"""
        raise NotImplementedError('not supported by this DBMS')
