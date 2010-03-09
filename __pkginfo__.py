"""logilab.database packaging information.

:copyright: 2002-2010 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: General Public License version 2 - http://www.gnu.org/licenses
"""
__docformat__ = "restructuredtext en"

distname = 'logilab-database'
modname = 'database'
numversion = (1, 0, 0)
version = '.'.join([str(num) for num in numversion])
copyright = '2000-2010 LOGILAB S.A. (Paris, FRANCE), all rights reserved.'
license = 'GPL'

author = "Logilab"
author_email = "devel@logilab.fr"

short_desc = "true unified database access"

long_desc = """logilab-database provides some classes to make unified access
to different RDBMS possible:
  * actually compatible db-api from different drivers to postgres, mysql,
    sqlite and sqlserver
  * additional api for full text search
  * extensions functions for common tasks such as creating database, index,
    users, dump and restore, etc...
  * sql generation for INSERT/UPDATE/DELETE (in sqlgen.py)
"""


web = "http://www.logilab.org/project/%s" % distname
ftp = "ftp://ftp.logilab.org/pub/%s" % modname
mailinglist = "mailto://python-projects@lists.logilab.org"

subpackage_of = 'logilab'
subpackage_master = True

from os.path import join
include_dirs = [join('test', 'data')]
pyversions = ['2.4', '2.5', '2.6']
