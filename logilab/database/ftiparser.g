""" yapps input grammar for indexer queries
"""

%%

parser IndexerQuery:

    ignore:         r'\s+'
    token WORD:     r'\w+'
    token STRING:      r"'([^\'\\]|\\.)*'|\"([^\\\"\\]|\\.)*\""

rule goal<<Q>> : all<<Q>> * '$'

rule all<<Q>>  : WORD    {{ Q.add_word(WORD) }}
               | STRING  {{ Q.add_phrase(STRING) }}
