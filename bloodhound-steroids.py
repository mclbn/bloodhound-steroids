#!/usr/bin/env python3

import argparse
import logging
import sys

from neo4j import GraphDatabase

known_modules = [
    'samepass',
    'samelocaladmin'
]

def do_insert_samepassword(driver, user, others):
    res_count = 0
    query = """
    MATCH (a:User), (b:User)
    WHERE a.name = toUpper("%s")
    AND b.name = toUpper("%s")
    CREATE (a)-[r:SamePassword]->(b), (b)-[k:SamePassword]->(a)
    RETURN r
    """

    for other in others:
        with driver.session() as session:
            try:
                result = session.run(query % (user, other))
                res_count = len(result.value())
            except Exception as e:
                print(str(e))
    return res_count

def do_samepass_user_file(driver, user_files):
    users = []
    updated = 0

    for user_file in user_files:
        try:
            f = open(user_file)
        except Exception as e:
            print(str(e))
        else:
            with f:
                for line in f:
                    clean = line.rstrip()
                    if len(clean):
                        users.append(clean)

    users = list(set(users))

    for user in users:
        updated += do_insert_samepassword(driver, '%s@%s' % (user, options.domain),
                             ['%s@%s' % (x, options.domain) for x in users if x != user])

    return updated

def do_samepass_nt_file(driver, nt_file):
    updated = 0
    nt = []
    grouped_nt = {}
    final = []

    try:
        f = open(nt_file)
    except Exception as e:
        print(str(e))
    else:
        with f:
            for line in f:
                clean = line.rstrip()
                if len(clean):
                    nt_entry = clean.split(':')

                    id = nt_entry[0].split('\\')

                    nt.append({
                        'username': id[0] if len(id) == 1 else id[1],
                        'hash': nt_entry[3]
                    })

    for entry in nt:
        if entry['hash'] not in grouped_nt.keys():
            grouped_nt[entry['hash']] = [entry['username']]
        else:
            grouped_nt[entry['hash']].append(entry['username'])

    for hash in grouped_nt.keys():
        if hash == '31d6cfe0d16ae931b73c59d7e0c089c0':
            print('The following users have an empty hash and will not be processed : %s'
                  % ', '.join(grouped_nt[hash]))
        if len(grouped_nt[hash]) > 1:
            final.append(grouped_nt[hash])

    for user_list in final:
        for user in user_list:
            updated += do_insert_samepassword(driver, '%s@%s' % (user, options.domain),
                             ['%s@%s' % (x, options.domain) for x in user_list if x != user])

    return updated

def do_samepass(driver, options):
    updated = 0

    if options.user_file is not None:
        updated += do_samepass_user_file(driver, options.user_file)
    if options.nt_file is not None:
        updated += do_samepass_nt_file(driver, options.nt_file)

    print('Updated : %d\n' % updated)

def do_insert_samelocal_admin(driver, computer, others):
    res_count = 0
    query = """
    MATCH (a:Computer), (b:Computer)
    WHERE a.name = toUpper("%s")
    AND b.name = toUpper("%s")
    CREATE (a)-[r:SameLocalAdmin]->(b), (b)-[k:SameLocalAdmin]->(a)
    RETURN r
    """

    for other in others:
        with driver.session() as session:
            try:
                print(query % (computer, other))
                result = session.run(query % (computer, other))
                res_count = len(result.value())
            except Exception as e:
                print(str(e))
    return res_count

def do_samelocaladmin(driver, options):
    computers = []
    updated = 0

    for computer_file in options.computer_file:
        try:
            f = open(computer_file)
        except Exception as e:
            print(str(e))
        else:
            with f:
                for line in f:
                    clean = line.rstrip()
                    if len(clean):
                        computers.append(clean)

    computers = list(set(computers))

    for computer in computers:
        updated += do_insert_samelocal_admin(driver, '%s.%s' % (computer, options.domain),
                             ['%s.%s' % (x, options.domain) for x in computers if x != computer])
    print('Updated : %d\n' % updated)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        add_help = True,
        description = "Give performance enhancing drugs to bloodhound.")

    parser.add_argument('-l', '--list', action='store_true', default=False,
                        help='list available modules')
    parser.add_argument('-m', '--module', action='store',
                        help='module to use')
    parser.add_argument('--domain', action='store',
                        help='the related domain')
    parser.add_argument('--user-file', action='append',
                        help='a list of user names (you can specify multiple files)')
    parser.add_argument('--computer-file', action='append',
                        help='a list of computer names (you can specify multiple files)')
    parser.add_argument('--nt-file', action='store',
                        help='a NT dump file (NTDS.DIT) to parse')
    parser.add_argument('--neo4j-host', '-n', action='store',
                        help='target neo4j host')
    parser.add_argument('--port', '-p', action='store', default=7687,
                        help='target neo4j port (default: 7474)')
    parser.add_argument('--user', '-u', action='store', default='neo4j',
                        help='target neo4j username')
    parser.add_argument('--secret', '-s', action='store',
                        help='target neo4j secret')

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    options = parser.parse_args()
    should_exit = False
    uri = None
    username = ''
    password = ''

    if options.list == True:
        print('\n'.join(known_modules))
        sys.exit(0)

    if options.module not in known_modules:
        print('Unknown module.')
        sys.exit(1)

    if options.neo4j_host is None:
        should_exit = True
    else:
        uri = 'bolt://%s:%d' % (options.neo4j_host, int(options.port))

    if options.user is not None:
        username = options.user
    if options.secret is not None:
        password = options.secret

    if should_exit is True:
        parser.print_help()
        sys.exit(1)

    print('Connecting to %s...' % uri)
    neo4j_log = logging.getLogger('neo4j')
    neo4j_log.setLevel(logging.CRITICAL)
    driver = GraphDatabase.driver(uri, auth=(username, password))

    if options.module == 'samepass':
        if options.domain is None or len(options.domain) == 0:
            print('You must specify a domain.')
            sys.exit(1)
        if options.user_file is None and options.nt_file is None:
            print('You must specify a user list or a dump file to parse.')
            sys.exit(1)
        if options.user_file is not None and options.nt_file is not None:
            print('You cannot specify both user list(s) and a dump file. Choose one.')
            sys.exit(1)
        do_samepass(driver, options)

    if options.module == 'samelocaladmin':
        if options.domain is None or len(options.domain) == 0:
            print('You must specify a domain.')
            sys.exit(1)
        if options.computer_file is None:
            print('You must specify a computer list.')
            sys.exit(1)
        do_samelocaladmin(driver, options)
