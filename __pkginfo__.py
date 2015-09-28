# copyright 2003-2014 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
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
"""logilab.database packaging information."""

distname = 'logilab-database'
modname = 'database'
numversion = (1, 13, 4)
version = '.'.join([str(num) for num in numversion])
license = 'LGPL'

author = "Logilab"
author_email = "contact@logilab.fr"

description = "true unified database access"

web = "http://www.logilab.org/project/%s" % distname
ftp = "ftp://ftp.logilab.org/pub/%s" % modname
mailinglist = "mailto://python-projects@lists.logilab.org"

subpackage_of = 'logilab'
subpackage_master = True

install_requires = [
    'logilab-common >= 0.63.2',
    'six >= 1.4.0',
    ]
