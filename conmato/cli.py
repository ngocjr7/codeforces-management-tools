from __future__ import absolute_import

from .check_plagiarism import *
from .contest import *
from .crawl_standings import *
from .csession import *
from .member import *
from .mossum import *
from .parameters import *
from .utils import *

import os
import click
import sys
import pickle
import json
import yaml
from tqdm import tqdm

def standing_to_df(standings):
    prob_names = [p['index']+'('+p['name']+')' for p in standings['problems']]
    standing_list = []
    for row in standings['rows']:
        a_standing = {'Who':row['handles']}
        for i, prob in enumerate(row['problemResults']):
            a_standing[prob_names[i]] = prob['points']
        standing_list.append(a_standing)
    standing_df = pd.DataFrame(standing_list)
    return standing_df

@click.group()
def cli():
    pass

@cli.command('config', help='Config command.')
@click.option(
    '--group-id', '-g', default=None, 
    help='Group id in Codeforces.com.'
)
# @click.option(
#     '--contest-id', '-c', 
#     help='Contest id in Codeforces.com'
# )
# @click.option(
#     '--user-format', '-f', 
#     help='User format.'
# )
@click.option(
    '--min-lines', '-ml', type=int,
    help='Min similar lines between two files.'
)
@click.option(
    '--min-percent', '-mp', type=int,
    help='Min percent between two files.'
)
@click.option(
    '--output-dir', '-o', 
    help='Working directory.'
)
@click.option(
    '--reset', '-rs', is_flag=True,
    help='Reset config file to default values.')
def config(group_id, # contest_id, user_format, 
    min_lines, min_percent, output_dir, reset):
    if reset:
        config = {'group_id':None, 'min_lines':10, 'min_percent':90, 'output_dir':None}
        with open(CONFIG_FILE, 'w') as file:
            yaml.dump(config, file)
        print('Successfully reset config file.')
    with open(CONFIG_FILE) as file:
        config = yaml.full_load(file)
    if group_id != None:
        config['group_id'] = group_id
    # if contest_id != None:
    #     config['contest_id'] = contest_id
    # if user_format != None:
    #     config['user_format'] = user_format
    if min_lines != None:
        config['min_lines'] = min_lines
    if min_percent != None:
        config['min_percent'] = min_percent
    if output_dir != None:
        config['output_dir'] = output_dir
    with open(CONFIG_FILE, 'w') as file:
        yaml.dump(config, file)
    print('Successfully updated config file.')

@cli.command('login', help='Login command.')
@click.option(
    '--username', '-u', required=True, prompt=True,
    help='Username in Codeforces.com.'
)
@click.option(
    '--password', '-p', required=True, prompt=True, hide_input=True,
    help='Password in Codeforces.com.'
)
def login(username, password):
    ss = CSession()
    if ss.login(username, password) != "Login successfully":
        print("Login fail! Please try again!", file=sys.stderr)
        sys.exit(-1)
    print('Successfully login with username: ', ss.get_logged_username())
    with open(SESSION_FILE, 'wb') as f:
        pickle.dump(ss, f)

# Member commands 
@cli.group(help='Member commands.')
def member():
    pass

@member.command('is-manager', help='Check if this user is the group manager.')
@click.option(
    '--group-id', '-g',
    help='Group id in Codeforces.com.'
)
@click.option(
    '--username', '-u', required=True,
    help='Username in Codeforces.com.'
)
@click.option(
    '--password', '-p', required=True,
    help='Password in Codeforces.com.'
)
def member_is_manager(group_id, username, password):
    with open(CONFIG_FILE) as file:
        config = yaml.full_load(file)
    if group_id == None:
        if config['group_id'] != None:
            group_id = config['group_id']
    if group_id == None:
        print("group-id not found in the command or config file.", file=sys.stderr)
        sys.exit(-1)
    print(is_manager(group_id, username, password))

@member.command('confirm', help='Confirm members in a group.')
@click.option(
    '--group-id', '-g',
    help='Group id in Codeforces.com.'
)
@click.option(
    '--input-file', '-i',
    help='CSV file path that stores members.'
)
@click.option(
    '--user-format', '-f', 
    help='User format.'
)
@click.option(
    '--action', '-ac', required=True,
    type=click.Choice(['accept','reject'], case_sensitive=False),
    help='Accept or reject users.'
)
def confirm(group_id, action, input_file, user_format):
    with open(CONFIG_FILE) as file:
        config = yaml.full_load(file)
    if group_id == None:
        if config['group_id'] != None:
            group_id = config['group_id']
    if group_id == None:
        print("group-id not found in the command or config file.", file=sys.stderr)
        sys.exit(-1)
    ss = CSession.load_session(SESSION_FILE)

    members = get_pending_participants(ss, group_id)
    if not members:
        print('There is no pending members to be confirmed.')
        sys.exit(0)
    members_df = to_df(members)

    if input_file != None:
        try:
            input_df = pd.read_csv(input_file)
            input_df = input_df['username']
        except KeyError:
            input_df = pd.read_csv(input_file, header=None)  
            input_df = input_df.iloc[:, 0]
        members_df = members_df[members_df['username'].isin(input_df.tolist())]

    if user_format != None:
        members_df = members_df[members_df['username'].str.match(user_format)==True]

    print('Do you want to confirm (accept/reject) {} user(s)? [y/n]: '.format(len(members_df)), end='')
    ans = input()
    if ans.strip().lower() == 'y':
        members = members_df.to_dict('records')
        for member in tqdm(members, desc='Confirming member(s)', unit=' members'):
            confirm_joining(ss, member, action, group_id)
        print('Successfully {}ed {} user(s)'.format(action, len(members_df)))

@member.command('remove', help='Remove members in a group.')
@click.option(
    '--input-file', '-i',
    help='CSV file that stores members.'
)
@click.option(
    '--user-format', '-f', 
    help='User format.'
)
@click.option(
    '--group-id', '-g', 
    help='Group id in Codeforces.com.'
)
def remove(group_id, input_file, user_format):
    with open(CONFIG_FILE) as file:
        config = yaml.full_load(file)
    if group_id == None:
        if config['group_id'] != None:
            group_id = config['group_id']
    if group_id == None:
        print("group-id not found in the command or config file.", file=sys.stderr)
        sys.exit(-1)
    ss = CSession.load_session(SESSION_FILE)
    
    members = get_all_members(ss, group_id)
    if not members:
        print('There is no members in the group to be removed.')
        sys.exit(0)
    members_df = to_df(members)

    if input_file != None:
        try:
            input_df = pd.read_csv(input_file)
            input_df = input_df['username']
        except KeyError:
            input_df = pd.read_csv(input_file, header=None)  
            input_df = input_df.iloc[:, 0]
        members_df = members_df[members_df['username'].isin(input_df.tolist())]

    if user_format != None:
        members_df = members_df[members_df['username'].str.match(user_format)==True]
    print('Do you want to remove {} user(s)? [y/n]: '.format(len(members_df)), end='')
    ans = input()
    if ans.strip().lower() == 'y':
        members = members_df.to_dict('records')
        for member in tqdm(members, desc='Removing member(s)', unit=' members'):
            remove_participants(ss, member, group_id)
        print('Successfully removed {} user(s)'.format(len(members_df)))

# Contest commands 
@cli.group(help='Contest commands.')
def contest():
    pass

@contest.command('ls', help='List all contests of a group.')
@click.option(
    '--group-id', '-g', 
    help='Group id in Codeforces.com.'
)
def ls(group_id):
    with open(CONFIG_FILE) as file:
        config = yaml.full_load(file)
    if group_id == None:
        if config['group_id'] != None:
            group_id = config['group_id']
        else:
            print("group-id not found in the command or config file.", file=sys.stderr)
            sys.exit(-1)
    ss = CSession.load_session(SESSION_FILE)

    contests = get_contests(ss, group_id)
    contest_df = pd.DataFrame(data={'contest id':list(contests.keys()),
        'contest name': list(contests.values())})
    print(contest_df)

@contest.command('register', help='Register users to join contest.')
@click.option(
    '--group-id', '-g', required=True,
    help='Group id in Codeforces.com.'
)
def register(group_id):
    print('Developing')

@contest.command('manage', help='Turn on manager-mode for contest(s) in a group.')
@click.option(
    '--group-id', '-g',
    help='Group id in Codeforces.com.'
)
@click.option(
    '--contest-id', '-c',
    help='Contest id in Codeforces.com.'
)
@click.option(
    '--mode', '-m', required=True,
    type=click.Choice(['true','false'], case_sensitive=False),
    help='true for Yes, false for No.'
)
def manage(group_id, contest_id, mode):
    with open(CONFIG_FILE) as file:
        config = yaml.full_load(file)
    if group_id == None:
        if config['group_id'] != None:
            group_id = config['group_id']
    # if contest_id == None:
    #     if config['contest_id'] != None:
    #         contest_id = config['contest_id']
    if group_id == None:
        print("group-id not found in the command or config file.", file=sys.stderr)
        sys.exit(-1)
    ss = CSession.load_session(SESSION_FILE)

    if contest_id != None:
        toggle_manager_mode(ss, contest_id, group_id, mode)
        contest_ids = [contest_id]
    else:
        ret = get_managed_contests(ss, group_id, mode)
        contest_ids = ret.keys()
    for contest_id in contest_ids:
        print('Successfully changed manage mode at contest {} in group {}.'
            .format(contest_id, group_id, mode))
# Plagiarism commands 
@cli.group(help='Plagiarism commands.')
def plagiarism():
    pass

@plagiarism.command('check', help='Check plagiarism.')
@click.option(
    '--group-id', '-g',
    help='Group id in Codeforces.com.'
)
@click.option(
    '--contest-id', '-c', required=True,
    help='Contest id in Codeforces.com.'
)
@click.option(
    '--min-lines', '-ml', 
    help='Min similar lines between two files.'
)
@click.option(
    '--min-percent', '-mp', 
    help='Min percent between two files.'
)
@click.option(
    '--submission-dir', '-sd', required=True,
    help='Submission directory (output dir from "get submission" command).'
)
# @click.option(
#     '--output-dir', '-o', 
#     help='Output directory.'
# )
def check(group_id, contest_id, min_lines, min_percent, submission_dir):
    with open(CONFIG_FILE) as file:
        config = yaml.full_load(file)
    if group_id == None:
        if config['group_id'] != None:
            group_id = config['group_id']
    # if contest_id == None:
    #     if config['contest_id'] != None:
    #         contest_id = config['contest_id']
    if min_lines == None:
        if config['min_lines'] != None:
            min_lines = config['min_lines']
        else:
            min_lines = 0
    if min_percent == None:
        if config['min_percent'] != None:
            min_percent = config['min_percent']
        else:
            min_percent = 0
    if group_id == None:
        print("group-id not found in the command or config file.", file=sys.stderr)
        sys.exit(-1)
    ss = CSession.load_session(SESSION_FILE)

    print("Checking plagiarism".format(contest_id, group_id))
    res = check_plagiarism(ss, contest_id, submission_dir, group_id, min_lines, min_percent, True)
    if res:
        print(pd.DataFrame(res).to_string())
    else:
        print('There is no submissions found in plagiarism check.')
    print("Successfully checked plagiarism.".format(contest_id, group_id))

@cli.group(help='Get commands.')
def get():
    pass

@get.command('username', help='Get this logged username.')
def username():
    ss = CSession.load_session(SESSION_FILE)
    print(ss.get_logged_username())

@get.command('member', help='Get members in a group.')
@click.option(
    '--group-id', '-g',
    help='Group id in Codeforces.com.'
)
@click.option(
    '--type', '-t', multiple=True,
    type=click.Choice(['all','pending', 'spectator', 'manager', 'participant'], case_sensitive=False),
    help='Get all members or pending participants in a group.'
)
@click.option(
    '--user-format', '-f', 
    help='User format.'
)
@click.option(
    '--output-dir', '-o', 
    help='Output directory.'
)
def member(group_id, type, user_format, output_dir):
    with open(CONFIG_FILE) as file:
        config = yaml.full_load(file)
    if group_id == None:
        if config['group_id'] != None:
            group_id = config['group_id']
    if output_dir == None:
        if config['output_dir'] != None:
            output_dir = config['output_dir']
    if group_id == None:
        print("group-id not found in the command or config file.", file=sys.stderr)
        sys.exit(-1)
    ss = CSession.load_session(SESSION_FILE)

    if type == None:
        type = ('all',)

    if 'all' in type:
        members = get_all_members(ss, group_id)
        result_df = to_df(members)
        result_df.loc[result_df['pending']==True, ['role']] = 'pending'
        result_df.drop(columns={'pending', 'csrf_token', 'groupRoleId', '_tta'}, inplace=True)
    else:
        pending_members_df = pd.DataFrame(columns={'username', 'role'})
        remaining_members_df = pd.DataFrame(columns={'username', 'role'})

        if 'pending' in type:
            pending_members = get_pending_participants(ss, group_id)
            pending_members_df = to_df(pending_members)
            pending_members_df['role'] = 'pending'
            pending_members_df.drop(columns={'csrf_token', 'groupRoleId', '_tta'}, inplace=True)

        remaining_roles = set(type) - {'pending'}
        if remaining_roles:                 
            remaining_members = get_all_members(ss, group_id)
            remaining_members_df = to_df(remaining_members)
            remaining_members_df = remaining_members_df[remaining_members_df['pending']==False]
            remaining_members_df = remaining_members_df[remaining_members_df['role'].isin(list(remaining_roles))]
            remaining_members_df.drop(columns={'pending', 'csrf_token', 'groupRoleId', '_tta'}, inplace=True)

        result_df = pd.concat([pending_members_df, remaining_members_df])
    if user_format != None:
        result_df = result_df[result_df['username'].str.match(user_format)==True]
    if output_dir != None:
        output_file = os.path.join(output_dir,'members_{}_{}.csv'.format(group_id, '_'.join(type)))
        create_dir(output_file)
        result_df.to_csv(output_file, index=False)
        print('Members was written to {} successfully'.format(output_file))
    else:
        if result_df.empty:
            print('There is no members!')
        else:
            print(result_df.to_string())

@get.command('contest', help='Get all standing and submission in a contest.')
@click.option(
    '--group-id', '-g', 
    help='Group id in Codeforces.com.'
)
@click.option(
    '--contest-id', '-c', required=True,
    help='Contest id in Codeforces.com.'
)
@click.option(
    '--output-dir', '-o', 
    help='Output directory.'
)
def contest(group_id=None, contest_id=None, output_dir=None):
    with open(CONFIG_FILE) as file:
        config = yaml.full_load(file)
    if group_id == None:
        if config['group_id'] != None:
            group_id = config['group_id']
    # if contest_id == None:
    #     if config['contest_id'] != None:
    #         contest_id = config['contest_id']
    if output_dir == None:
        if config['output_dir'] != None:
            output_dir = config['output_dir']
    if group_id == None or contest_id == None or output_dir == None:
        print("group-id or contest-id or output-dir not found in the command or config file.", file=sys.stderr)
        sys.exit(-1)
    ss = CSession.load_session(SESSION_FILE)

    members = get_all_members(ss, group_id)
    members_df = to_df(members)
    members_df = members_df[members_df['pending']==False]
    standings = get_standings(contest_id, usernames=members_df['username'].to_list())
    standing_df = standing_to_df(standings)
    # Saving standings file
    contest_name = get_contest_name(ss, contest_id, group_id)
    # print(contest_name)
    standings_file = os.path.join(output_dir, 'contest_{}_{}({})/standings.csv'.format(
        group_id, contest_id, contest_name))
    create_dir(standings_file)
    standing_df.to_csv(standings_file, index=False)
    print('Standings was written to {} successfully'.format(standings_file))

    print("Getting all submission from contest {} in group {}".format(contest_id, group_id))
    new_output_dir = os.path.join(output_dir, 'contest_{}_{}({})'.format(
        group_id, contest_id, contest_name))
    get_all_submission(ss, contest_id, new_output_dir, group_id)
    print("Successfully getting all submission from contest {} in group {}".format(contest_id, group_id))

@get.command('standings', help='Get standing in a contest.')
@click.option(
    '--group-id', '-g',
    help='Group id in Codeforces.com.'
)
@click.option(
    '--contest-id', '-c', required=True,
    help='Contest id in Codeforces.com.'
)
# @click.option(
#     '--username-list', '-ul', 
#     help='List of username'
# )
@click.option(
    '--user-format', '-f', 
    help='User format.'
)
@click.option(
    '--common', '-cm', is_flag=True,
    help='Flag for getting all participants (group outter included).')
@click.option(
    '--output-dir', '-o', 
    help='Output directory.'
)
def standings(group_id, contest_id, user_format, common, output_dir):
    ss = CSession.load_session(SESSION_FILE)
    with open(CONFIG_FILE) as file:
        config = yaml.full_load(file)
    if group_id == None:
        if config['group_id'] != None:
            group_id = config['group_id']
    # if contest_id == None:
    #     if config['contest_id'] != None:
    #         contest_id = config['contest_id']
    if output_dir == None:
        if config['output_dir'] != None:
            output_dir = config['output_dir']
    if group_id == None and not common:
        print("group-id not found in the command or config file.\n" + \
            "Please provide group id or use '--common'/'-cm' flag to get common standings.", file=sys.stderr)
        sys.exit(-1)

    if common:
        standings = get_standings(contest_id, usernames=None, user_format=user_format)
        standing_df = standing_to_df(standings)
        # if user_format != None:
        #     standing_df = standing_df[standing_df['Who'].str.match(user_format)==True]
    else:
        members = get_all_members(ss, group_id)
        members_df = to_df(members)
        members_df = members_df[members_df['pending']==False]
        # if user_format != None:
        #     members_df = members_df[members_df['username'].str.match(user_format)==True]
        standings = get_standings(contest_id, usernames=members_df['username'].to_list(), user_format=user_format)
        standing_df = standing_to_df(standings)
    
    if output_dir != None:
        name = 'common' if common else group_id
        output_file = os.path.join(output_dir, 'standings_{}_{}.csv'.format(name, contest_id))
        create_dir(output_file)
        standing_df.to_csv(output_file, index=False)
        print('Standings was written to {} successfully'.format(output_file))
    else:
        print(standing_df.to_string())

@get.command('submission', help='Get all submission in a contest.')
@click.option(
    '--group-id', '-g',
    help='Group id in Codeforces.com.'
)
@click.option(
    '--contest-id', '-c', required=True,
    help='Contest id in Codeforces.com.'
)
@click.option(
    '--user-format', '-f', 
    help='User format.'
)
@click.option(
    '--output-dir', '-o', 
    help='Output directory.'
)
def submission(group_id, contest_id, user_format, output_dir):
    ss = CSession.load_session(SESSION_FILE)
    with open(CONFIG_FILE) as file:
        config = yaml.full_load(file)
    if group_id == None:
        if config['group_id'] != None:
            group_id = config['group_id'] 
    # if contest_id == None:
    #     if config['contest_id'] != None:
    #         contest_id = config['contest_id']
    if output_dir == None:
        if config['output_dir'] != None:
            output_dir = config['output_dir']
    if group_id == None or output_dir == None:
        print("group-id or output-dir not found in the command or config file.", file=sys.stderr)
        sys.exit(-1)
    print("Getting all submission from contest {} in group {}".format(contest_id, group_id))
    get_all_submission(ss, contest_id, output_dir, group_id, page=1, user_format=user_format)
    print("Successfully getting all submission from contest {} in group {}".format(contest_id, group_id))

@get.command('pstandings', help='Get all standing with plagiarism in a contest.')
@click.option(
    '--group-id', '-g', 
    help='Group id in Codeforces.com.'
)
@click.option(
    '--contest-id', '-c', required=True,
    help='Contest id in Codeforces.com.'
)
@click.option(
    '--min-lines', '-ml', 
    help='Min similar lines between two files.'
)
@click.option(
    '--min-percent', '-mp', 
    help='Min percent between two files.'
)
@click.option(
    '--output-dir', '-o', 
    help='Output directory.'
)
def pstandings(group_id=None, contest_id=None, 
    min_lines=None, min_percent=None, output_dir=None):
    ss = CSession.load_session(SESSION_FILE)
    with open(CONFIG_FILE) as file:
        config = yaml.full_load(file)
    if group_id == None:
        if config['group_id'] != None:
            group_id = config['group_id']
    # if contest_id == None:
    #     if config['contest_id'] != None:
    #         contest_id = config['contest_id']
    if min_lines == None:
        if config['min_lines'] != None:
            min_lines = config['min_lines']
        else:
            min_lines = 0
    if min_percent == None:
        if config['min_percent'] != None:
            min_percent = config['min_percent']
        else:
            min_percent = 0
    if output_dir == None:
        if config['output_dir'] != None:
            output_dir = config['output_dir']
    if group_id == None or output_dir == None:
        print("group-id or output-dir not found in the command or config file.", file=sys.stderr)
        sys.exit(-1)
    print("Crawling checked standings from contest {} in group {}".format(contest_id, group_id))
    crawl_checked_standings(ss, contest_id, output_dir, group_id, min_lines, min_percent, True)
    print("Successfully Crawling checked standings from contest {} in group {}!".format(contest_id, group_id))

if __name__ == "__main__":
    cli()