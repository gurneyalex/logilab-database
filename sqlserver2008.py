"""Sqlserver 2008 RDBMS support

Mostly untested, use at your own risks. 

Supported drivers, in order of preference:
- pyodbc (recommended, others are not well tested)
- adodbapi

:copyright: 2009-2010 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: General Public License version 2 - http://www.gnu.org/licenses
"""

from logilab import database as db
from logilab.database.sqlserver import _PyodbcAdapter, _AdodbapiAdapter

class _PyodbcSqlServer2008Adapter(_PyodbcAdapter):
    driver = "SQL Server Native Client 10.0"


class _AdodbapiSqlServer2008Adapter(_AdodbapiAdapter):
    driver = "SQL Server Native Client 10.0"

db._PREFERED_DRIVERS.update({
    'sqlserver2008' : ['pyodbc', 'adodbapi', ],
    })

db._ADAPTER_DIRECTORY.update({
    'sqlserver2008' : {'adodbapi': _AdodbapiSqlServer2008Adapter,
                       'pyodbc': _PyodbcSqlServer2008Adapter},
    })
