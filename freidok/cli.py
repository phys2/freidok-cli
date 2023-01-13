import argparse
import os
import re
from collections.abc import Callable
from functools import partial

from dotenv import load_dotenv

from freidok.client import FreidokClient, FreidokMockClient
from freidok.format import PublicationsHtmlExporter, AuthorsListStyle
from freidok.models.freidok_json_api import Publications
from freidok.utils import str2list

USER_AGENT = 'freidok-retrieve/1.0'

PUBLICATION_FIELDS = [
    'id', 'link', 'abstracts', 'researchdata_descriptions', 'descriptions', 'messages',
    'classifications', 'pub_ids', 'pub_ids_internal', 'pubtype', 'languages', 'edition',
    'keywords', 'keywords_uncontrolled', 'publication_year', 'peerreviewed',
    'day_of_exam', 'system_time', 'titles', 'title_parents', 'persons', 'persons_stat',
    'affiliations_list', 'functions_list', 'institutions', 'relations',
    'reverse_relations', 'publisher', 'source_journal', 'source_compilation', 'size',
    'series', 'contract', 'license_metadata', 'license', 'contact', 'fundings',
    'preview_image', 'files_stat', 'files', 'files_external', 'oa_status', 'revision',
    'acquisition_type', 'fachsigel', 'state', 'locked', 'issued', 'created_by',
    'submission_type', 'current_person_affiliations',
    'current_institution_affiliations', 'current_project_affiliations',
    'current_activity_affiliations',
]

# Sets of fields can be predefined via environment variables starting with
publication_fieldsets = {}


def env2dict(env_prefix: str, key_mapper: Callable = str,
             value_mapper: Callable = None):
    """Return certain values from env"""
    d = {}
    if not env_prefix:
        raise ValueError(f"Invalid env_prefix: {env_prefix}")
    for key, value in os.environ.items():
        if key.startswith(env_prefix):
            name = key_mapper(key.removeprefix(env_prefix))
            if value_mapper:
                value = value_mapper(value)
            d[name] = value
    return d


def load_publication_fieldsets():
    d = env2dict(
        'FREIDOK_FIELDSET_PUBLICATION_',
        key_mapper=str.lower,
        value_mapper=str2list
    )
    publication_fieldsets.update(d)


def arguments():
    load_dotenv()
    load_publication_fieldsets()

    intlist = partial(str2list, mapper=int)

    def int_minmax_type(x, xmin: int = None, xmax: int = None):
        x = int(x)
        if xmin is not None and x < xmin:
            raise argparse.ArgumentTypeError(f"must be >= {xmin}")
        if xmax is not None and x > xmax:
            raise argparse.ArgumentTypeError(f"must be <= {xmax}")
        return x

    def year_range_type(y):
        if m := re.match(r'^\d{4}(?:-\d{4})?$', y):
            return list(map(int, y.split('-')))
        else:
            raise argparse.ArgumentTypeError(f"{y} is not a valid year range")

    def multi_choice_type(value, allowed_values: list | set):
        items = str2list(value)
        if bad_apples := set(items) - set(allowed_values):
            raise argparse.ArgumentTypeError(f"Value(s) not allowed: {bad_apples}")
        else:
            return items

    def choice_type(value, allowed_values: list | set):
        if value in allowed_values:
            return value
        else:
            raise argparse.ArgumentTypeError(f"Value not allowed: {value}")

    env_url = os.getenv('FREIDOK_URL')
    max_rows_type = partial(int_minmax_type, xmin=1, xmax=100)
    pub_fields_type = partial(multi_choice_type, allowed_values=PUBLICATION_FIELDS)
    pub_fieldset_type = partial(choice_type, allowed_values=publication_fieldsets)

    argp_main = argparse.ArgumentParser(prog='freidok', )

    subparsers = argp_main.add_subparsers(
        title='subcommands', description='available subcommands:', help='Description')

    argp_api = argparse.ArgumentParser(add_help=False)

    argp_api.add_argument(
        '--url', default=env_url, required=not env_url,
        help='Freidok JSON API URL')

    argp_api.add_argument(
        '-n', '--dryrun', action='store_true',
        help="Don't actually send API requests, just print query")

    argp_api.add_argument(
        '--maxrows', metavar='N', default=0, type=max_rows_type,
        help='Maximum number of rows to retrieve')

    # argp_api.add_argument('--startrow', default=0, type=int,
    #                       help='Row index to start retrieval from (for pagination)')

    # subparser: publications

    argp_pub = subparsers.add_parser(
        'publications', parents=[argp_api], aliases=['pub'],
        help='Retrieve publications')

    argp_pub.add_argument(
        '--id', type=str2list, metavar='ID[,ID,..]',
        help='One or many publication IDs')

    argp_pub.add_argument(
        '--pers-id', type=intlist, metavar='ID[,ID,..]',
        help='One or many person IDs')

    argp_pub.add_argument(
        '--inst-id', type=intlist, metavar='ID[,ID,..]',
        help='One or many institution IDs')

    argp_pub.add_argument(
        '--title', metavar='TERM',
        help='Search TERM in publication title')

    argp_pub.add_argument(
        '--years', metavar='YYYY[-YYYY]', type=year_range_type,
        help='Limit publication years')

    argp_pub.add_argument(
        '--maxpers', metavar='N', default=0, type=int,
        help='Maximum number of listed authors')

    group_fields = argp_pub.add_mutually_exclusive_group()

    group_fields.add_argument(
        '--fields', metavar='F[,F,...]', type=pub_fields_type,
        help='Field(s) to include in response. '
             'Available fields: ' + ', '.join(PUBLICATION_FIELDS))

    group_fields.add_argument(
        '--fieldset', metavar='NAME', type=pub_fieldset_type,
        help='Predefined set of fields to include in response. '
             'Available sets: ' + str(list(publication_fieldsets.keys())))

    argp_pub.set_defaults(func=get_publications)

    # subparser: institutions

    argp_inst = subparsers.add_parser(
        'institutions', parents=[argp_api], aliases=['inst'],
        help='Retrieve institutions')

    argp_inst.add_argument(
        '--id', type=str2list, metavar='ID1[,ID2,..]',
        help='One or many institution IDs')

    argp_inst.add_argument(
        '--name', type=str, metavar='TERM',
        help='Show institutions containing TERM')

    argp_inst.set_defaults(func=get_institutions)

    return argp_main.parse_args()


def run():
    args = arguments()
    # print(args)
    args.func(args)


def get_publications(args):
    client = FreidokMockClient(base_url=args.url, user_agent=USER_AGENT,
                               dryrun=args.dryrun,
                               default_max_rows=args.maxrows)

    if args.years:
        year_from = args.years[0]
        year_to = args.years[1] if len(args.years) > 1 else year_from
    else:
        year_from = None
        year_to = None

    if args.fields:
        fields = args.fields
    elif args.fieldset:
        fields = publication_fieldsets[args.fieldset]
    else:
        fields = None

    data = client.get_publications(
        ids=args.id,
        inst_ids=args.inst_id,
        pers_ids=args.pers_id,
        title=args.title,
        year_from=year_from,
        year_to=year_to,
        fields=fields,
        maxpers=args.maxpers,
    )

    publist = Publications(**data)

    exporter = PublicationsHtmlExporter(
        author_list_style=AuthorsListStyle.LAST_FIRST_ABBREV
    )
    exporter.export(publist, 'publications.html')


def get_institutions(args):
    client = FreidokClient(base_url=args.url, user_agent=USER_AGENT, dryrun=args.dryrun,
                           default_max_rows=args.maxrows)

    data = client.get_institutions(
        ids=args.id,
        name=args.name,
    )
    print(data)
