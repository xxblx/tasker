#!/usr/bin/env python3

import argparse
import getpass
from uuid import uuid4

import nacl.pwhash
import psycopg2
from psycopg2.sql import SQL, Identifier

from server.sql.create import (CreateSchemaQueries, CreateFunctionQueries,
                               CreateSequenceQueries, CreateTableQueries,
                               CreateTriggerQueries)
from server.sql.delete import DeleteQueries
from server.sql.insert import InsertQueries
from server.sql.update import UpdateQueries
from server.conf import DB_SETTINGS


def run_create_queries():
    with psycopg2.connect(**DB_SETTINGS) as conn:
        with conn.cursor() as cur:
            cur.execute(CreateSchemaQueries.schema)
            for query in CreateFunctionQueries.get_create_queries():
                cur.execute(query)
            for query in CreateSequenceQueries.get_create_queries():
                cur.execute(query)
            for query in CreateTableQueries.get_create_queries():
                cur.execute(query)
            for query in CreateTriggerQueries.get_create_queries():
                cur.execute(query)


def create_user(username, password=None, generate_password=None):
    results = {'username': username}
    if password is None and generate_password is not None:
        password = uuid4().hex
        results['password'] = password
    elif password is None and generate_password is None:
        password = getpass.getpass()
    hashed = nacl.pwhash.str(password.encode())
    with psycopg2.connect(**DB_SETTINGS) as conn:
        with conn.cursor() as cur:
            # Create a user
            cur.execute(InsertQueries.add_user, (username, hashed))
            results['user_id'] = cur.fetchall()[0][0]
            # Create home project for the user
            cur.execute(InsertQueries.add_project, ('My Project', None))
            project_id, project_pub_id = cur.fetchall()[0]
            results['project_id'] = project_pub_id
            # Make the user an admin of the project
            cur.execute(
                InsertQueries.add_user_project,
                (project_id, results['user_id'], 2)
            )
            # Create sequences for the project: folders, tasks
            seq_pf = Identifier(
                'project_folder_{}_seq'.format(project_id)
            )
            seq_pt = Identifier(
                'project_task_{}_seq'.format(project_id)
            )
            cur.execute(
                SQL(CreateSequenceQueries._new_sequence).format(seq=seq_pf)
            )
            cur.execute(
                SQL(CreateSequenceQueries._new_sequence).format(seq=seq_pt)
            )
            # Create default folder
            cur.execute(
                SQL(InsertQueries.add_folder).format(seq=seq_pf),
                ('My Tasks', project_id)
            )
            folder_id, folder_pub_id = cur.fetchall()[0]
            results['folder_id'] = folder_pub_id
            results['tasks'] = []
            # Create a few demo tasks
            for i in range(3):
                args = (
                    'Demo task {}'.format(i+1),  # title
                    'This is a description of Task #{}'.format(i+1),
                    None, None,  # datetime_from, datetime_due
                    results['user_id'],
                    project_id,
                    folder_id
                )
                cur.execute(
                    SQL(InsertQueries.add_task).format(seq=seq_pt),
                    args
                )
                task_id, task_pub_id = cur.fetchall()[0]
                results['tasks'].append(task_pub_id)
    return results


def delete_user(username):
    with psycopg2.connect(**DB_SETTINGS) as conn:
        with conn.cursor() as cur:
            cur.execute(DeleteQueries.delete_user, (username,))


def modify_user(username, displayname=None, role=None):
    queries = []
    if role is not None and not (0 <= role <= 2):
        return
    elif role is not None:
        queries.append([UpdateQueries.role_global, (role, username)])

    if displayname is not None:
        queries.append([UpdateQueries.display_name, (displayname, username)])

    with psycopg2.connect(**DB_SETTINGS) as conn:
        with conn.cursor() as cur:
            for query, args in queries:
                cur.execute(query, args)


def set_password(username):
    password = getpass.getpass()
    hashed = nacl.pwhash.str(password.encode())
    with psycopg2.connect(**DB_SETTINGS) as conn:
        with conn.cursor() as cur:
            cur.execute(UpdateQueries.password, (hashed, username))


def main():
    commands = {
        'init-db': {
            'func': run_create_queries,
            'kw': []
        },
        'user-add': {
            'func': create_user,
            'kw': ['username', 'password', 'generate_password']
        },
        'user-del': {
            'func': delete_user,
            'kw': ['username']
        },
        'user-mod': {
            'func': modify_user,
            'kw': ['username', 'displayname', 'role']
        },
        'user-mod-passwd': {
            'func': set_password,
            'kw': ['username']
        }
    }

    parser = argparse.ArgumentParser(prog='tasker-manager-cli')
    subparsers = parser.add_subparsers()

    init_db = subparsers.add_parser('init-db')
    init_db.set_defaults(used='init-db')

    user_add = subparsers.add_parser('user-add')
    user_add.set_defaults(used='user-add')
    user_add.add_argument('-u', '--username', type=str, required=True)
    user_add.add_argument('-p', '--password', type=str, default=None)
    user_add.add_argument('--generate-password', dest='generate_password',
                          action='store_true', default=None)

    user_del = subparsers.add_parser('user-del')
    user_del.set_defaults(used='user-del')
    user_del.add_argument('-u', '--username', type=str, required=True)

    user_mod = subparsers.add_parser('user-mod')
    user_mod.set_defaults(used='user-mod')
    user_mod.add_argument('-u', '--username', type=str, required=True)
    user_mod.add_argument('-d', '--displayname', type=str, default=None)
    user_mod.add_argument('-r', '--role', type=int, default=None)

    user_mod_passwd = subparsers.add_parser('user-mod-passwd')
    user_mod_passwd.set_defaults(used='user-mod-passwd')
    user_mod_passwd.add_argument('-u', '--username', type=str, required=True)

    args = parser.parse_args()
    if 'used' not in args:
        return
    else:
        _args = vars(args)
        func = commands[args.used]['func']
        kw = {k: _args[k] for k in commands[args.used]['kw']}
        result = func(**kw)
        if result is not None:
            print(result)


if __name__ == '__main__':
    main()
