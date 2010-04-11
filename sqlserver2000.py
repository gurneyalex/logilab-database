"""Sqlserver 2000 RDBMS support

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

class _PyodbcSqlServer2000Adapter(_PyodbcAdapter):
    driver = "SQL Server"


class _AdodbapiSqlServer2000Adapter(_AdodbapiAdapter):
    driver = "SQL Server"

db._PREFERED_DRIVERS.update({
    'sqlserver2000' : ['pyodbc', 'adodbapi', ],
    })

db._ADAPTER_DIRECTORY.update({
    'sqlserver2000' : {'adodbapi': _AdodbapiSqlServer2000Adapter,
                       'pyodbc': _PyodbcSqlServer2000Adapter},
    })


