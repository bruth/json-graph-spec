#!/usr/bin/env python
from __future__ import print_function, unicode_literals, absolute_import

import json
import logging
import requests

logger = logging.getLogger(__name__)

# Default URI to Neo4j REST endpoint
DEFAULT_URI = 'http://localhost:7474/db/data/'

# Endpoint for the single transaction
TRANSACTION_URI_TMPL = '{}transaction/commit'

# Cypher statement template for creating a node.
CREATE_NODE_STMT = 'CREATE ({r}{labels} {props})'

# Cypher statement template for ensuring a node based.
MERGE_NODE_STMT = 'MERGE ({r}{labels} {props}) {oncreate} {onmatch}'

# Cypher statement template for creating a relationship between nodes.
CREATE_REL_STMT = 'CREATE ({r1})-[{r}:{rtype} {props}]->({r2})'

# Cypher statement template for ensuring a relationship between nodes.
MERGE_REL_STMT = 'MERGE ({r1})-[{r}:{rtype}]->({r2}) {oncreate} {onmatch}'


class MergeFactory(object):
    """Produces statements and tracks references to previously matched
    nodes and relationships.

    This enables constructing one large statement rather than doing many
    subsequent lookups which is optimized for bulk imports.
    """
    def __init__(self):
        self.rc = 0
        self.rm = {}

    def getref(self, key):
        if key not in self.rm:
            ref = 'x{}'.format(self.rc)
            self.rc += 1
            self.rm[key] = ref
        return self.rm[key]

    def hasref(self, key):
        return key in self.rm

    def deref(self):
        self.rm = {}
        self.rc = 0

    def _dict_props(self, props):
        "Converts a dict into a valid properties object in Cypher syntax."
        toks = []
        for key, value in props.iteritems():
            if value is None:
                continue
            if isinstance(value, (str, unicode)):
                s = "{}: '{}'"
            else:
                s = '{}: {}'
            toks.append(s.format(key, value))
        return '{{ {} }}'.format(', '.join(toks))

    def _keyword_props(self, ref, props):
        "Converts a dict into an array of valid assignments in Cypher syntax."
        toks = []
        for key, value in props.iteritems():
            if value is None:
                continue
            if isinstance(value, (str, unicode)):
                s = "{}.{} = '{}'"
            else:
                s = '{}.{} = {}'
            toks.append(s.format(ref, key, value))
        return ', '.join(toks)

    def _labels_stmt(self, labels):
        if not labels:
            return ''
        return ':' + ':'.join(labels)

    def _oncreate_stmt(self, ref, props):
        if not props:
            return ''
        props = self._dict_props(props)
        return 'ON CREATE SET {} = {}'.format(ref, props)

    def _onmatch_stmt(self, ref, props, replace):
        if not props:
            return ''
        if replace:
            props = self._dict_props(props)
            return 'ON MATCH SET {} = {}'.format(ref, props)
        props = self._keyword_props(ref, props)
        return 'ON MATCH SET {}'.format(props)

    def create_node(self, index, props, labels=None):
        ref = self.getref(index)
        labels = self._labels_stmt(labels)
        props = self._dict_props(props)
        return CREATE_NODE_STMT.format(r=ref, labels=labels, props=props)

    def merge_node(self, index, props, cprops=None, uprops=None, labels=None,
                   replace=False):

        ref = self.getref(index)
        labels = self._labels_stmt(labels)
        props = self._dict_props(props)

        oncreate = self._oncreate_stmt(ref, cprops)
        onmatch = self._onmatch_stmt(ref, uprops, replace)

        return MERGE_NODE_STMT.format(r=ref,
                                      labels=labels,
                                      props=props,
                                      oncreate=oncreate,
                                      onmatch=onmatch)

    def create_rel(self, index, n1, rtype, n2, props=None):
        ref = self.getref(index)
        ref1 = self.getref(n1)
        ref2 = self.getref(n2)
        props = self._dict_props(props)
        return CREATE_REL_STMT.format(r=ref, r1=ref1, r2=ref2,
                                      props=props)

    def merge_rel(self, index, n1, rtype, n2, props=None, cprops=None,
                  uprops=None, replace=False):

        ref = self.getref(index)
        ref1 = self.getref(n1)
        ref2 = self.getref(n2)
        props = self._dict_props(props)

        oncreate = self._oncreate_stmt(ref, cprops)
        onmatch = self._onmatch_stmt(ref, uprops, replace)

        return MERGE_REL_STMT.format(r=ref, r1=ref1, r2=ref2,
                                     rtype=rtype, oncreate=oncreate,
                                     onmatch=onmatch)


def send_request(uri, statements):
    "Sends a request to the transaction endpoint."
    url = TRANSACTION_URI_TMPL.format(uri)

    data = json.dumps({
        'statements': [{'statement': ' '.join(statements)}]
    })

    headers = {
        'accept': 'application/json; charset=utf-8',
        'content-type': 'application/json',
    }

    resp = requests.post(url, data=data, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    if data['errors']:
        print(data['errors'])


def pick(props, keys):
    picked = {}
    for key in keys:
        try:
            picked[key] = props[key]
        except KeyError:
            raise KeyError('"{}" does not exist in properties'.format(key))
    return picked


def parse_match_props(match, props):
    if not match:
        return {}
    elif isinstance(match, dict):
        return match
    elif isinstance(match, list):
        return pick(props, match)
    raise ValueError('match must be None, False, a list, or a dict')


def parse_update_props(update, props):
    if not update:
        return props
    elif isinstance(update, dict):
        return update
    elif isinstance(update, list):
        return pick(props, update)
    raise ValueError('update must be None, a list, or a dict')


def parse_node(index, node, factory):
    props = node.get('props', {})
    match = node.get('match')
    update = node.get('update')
    replace = node.get('replace', False)
    labels = node.get('labels')

    assert type(replace) is bool, 'replace must be a boolean'

    # Force create the node
    if match is False:
        return factory.create_node(index, props, labels=labels)

    mprops = parse_match_props(match, props)
    uprops = parse_update_props(update, props)

    return factory.merge_node(index, mprops, cprops=props,
                              uprops=uprops, labels=labels)


def parse_rel(index, rel, factory, bound):
    start = int(rel.get('start'))
    end = int(rel.get('end'))
    rtype = rel.get('type')
    props = rel.get('props', {})
    match = rel.get('match')
    update = rel.get('update')
    replace = rel.get('replace', False)

    # Ensure the references are within bounds
    assert 0 <= start <= bound, 'start node index not bounds'
    assert 0 <= end <= bound, 'end node index not in bounds'
    assert rtype, 'relationships must have a non-empty type'

    assert type(replace) is bool, 'replace must be a boolean'

    # Force create the node
    if match is False:
        return factory.create_rel(index, start, rtype, end, props)

    mprops = parse_match_props(match, props)
    uprops = parse_update_props(update, props)

    return factory.merge_rel(index, start, rtype, end, mprops, cprops=props,
                             uprops=uprops)


def parse(path):
    with open(path) as fin:
        data = json.load(fin)

    factory = MergeFactory()
    statements = []

    nodes = data.get('nodes', ())
    rels = data.get('rels', ())

    for index, node in enumerate(nodes):
        stmt = parse_node(index, node, factory)
        statements.append(stmt)

    # References to nodes in relationships cannot exceed
    # this upper bound, offset if for references in factory
    offset = len(nodes)
    bound = offset - 1

    for index, rel in enumerate(rels):
        stmt = parse_rel(offset + index, rel, factory, bound)
        statements.append(stmt)

    return statements


def load(path, uri=DEFAULT_URI):
    statements = parse(path)
    logger.debug('\n'.join(statements))
    send_request(uri, statements)


if __name__ == '__main__':
    import sys
    args = sys.argv[1:]
    if not args:
        print('error: path to JSON file is required')
        sys.exit(1)
    if '-p' in args:
        args.remove('-p')
        print('\n'.join(parse(*args)))
    else:
        load(*args)
