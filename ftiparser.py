# copyright 2003-2011 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
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
"""Yapps input grammar for indexer queries.

"""
from __future__ import print_function

__docformat__ = "restructuredtext en"

# Begin -- grammar generated by Yapps
import sys, re
from yapps import runtime

class IndexerQueryScanner(runtime.Scanner):
    patterns = [
        ("'$'", re.compile('$')),
        ('\\s+', re.compile('\\s+')),
        ('WORD', re.compile('\\w+')),
        ('STRING', re.compile('\'([^\\\'\\\\]|\\\\.)*\'|\\"([^\\\\\\"\\\\]|\\\\.)*\\"')),
    ]
    def __init__(self, str,*args,**kw):
        runtime.Scanner.__init__(self,None,{'\\s+':None,},str,*args,**kw)

class IndexerQuery(runtime.Parser):
    Context = runtime.Context
    def goal(self, Q, _parent=None):
        _context = self.Context(_parent, self._scanner, 'goal', [Q])
        while self._peek( context=_context) != "'$'":
            all = self.all(Q, _context)
        self._scan("'$'", context=_context)

    def all(self, Q, _parent=None):
        _context = self.Context(_parent, self._scanner, 'all', [Q])
        _token = self._peek('WORD', 'STRING', context=_context)
        if _token == 'WORD':
            WORD = self._scan('WORD', context=_context)
            Q.add_word(WORD)
        else: # == 'STRING'
            STRING = self._scan('STRING', context=_context)
            Q.add_phrase(STRING)


def parse(rule, text):
    P = IndexerQuery(IndexerQueryScanner(text))
    return runtime.wrap_error_reporter(P, rule)

if __name__ == '__main__':
    from sys import argv, stdin
    if len(argv) >= 2:
        if len(argv) >= 3:
            f = open(argv[2],'r')
        else:
            f = stdin
        print(parse(argv[1], f.read()))
    else:
        print('Args:  <rule> [<filename>]', file=sys.stderr)
# End -- grammar generated by Yapps
