import argparse
import json
import os
import re
from collections.abc import Callable
from enum import Enum
from functools import partial
from pathlib import Path

from dotenv import load_dotenv

from freidok import modify
from freidok.client import FreidokApiClient, FreidokFileReader
from freidok.export import PublicationsHtmlExporter, \
    PublicationsMarkdownExporter, PublicationsTemplateExporter
from freidok.models.api import Publications
from freidok.utils import str2list, opens

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

# Sets of fields can be predefined via environment variables
# starting with FREIDOK_FIELDSET_PUBLICATION_
publication_fieldsets = {
    'default': 'id link publication_year titles publisher persons persons_stat pubtype '
               'source_journal source_compilation pub_ids preview_image'.split()
}


# ExportFormats = Enum('ExportFormats', ['MARKDOWN', 'JSON', 'HTML', 'TEMPLATE'])
class ExportFormat(str, Enum):
    MARKDOWN = 'markdown'
    HTML = 'html'
    JSON = 'json'
    TEMPLATE = 'template'


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

    def multi_choice_type(value, allowed: list | set):
        items = str2list(value)
        if bad_apples := set(items) - set(allowed):
            raise argparse.ArgumentTypeError(f"Value(s) not allowed: {bad_apples}")
        else:
            return items

    def simple_choice_type(value, allowed: list | set):
        """Like argparse 'choice', but doesn't flood usage string with choices"""
        if value in allowed:
            return value
        else:
            raise argparse.ArgumentTypeError(f"Value not allowed: {value}")

    def language_type(value):
        items = str2list(value)
        for item in items:
            if not (m := re.match(r'^[a-zA-Z]{3}$', item)):
                raise argparse.ArgumentTypeError(
                    f"Invalid 3-character language code: '{item}'")
        else:
            return items

    env_url = os.getenv('FREIDOK_URL')
    max_rows_type = partial(int_minmax_type, xmin=1, xmax=100)
    pub_fields_type = partial(multi_choice_type, allowed=PUBLICATION_FIELDS)
    pub_fieldset_type = partial(simple_choice_type, allowed=publication_fieldsets)

    argp_main = argparse.ArgumentParser(prog='freidok', )

    subparsers = argp_main.add_subparsers(
        title='subcommands', description='available subcommands:', help='Description')

    argp_api = argparse.ArgumentParser(add_help=False)

    argp_api.add_argument(
        '--source', default=env_url, required=not env_url,
        help='Freidok JSON API URL or path to stored JSON file')

    argp_api.add_argument(
        '-n', '--dryrun', action='store_true',
        help="Don't actually send API requests, just print query")

    argp_api.add_argument(
        '--maxitems', metavar='N', default=100,
        type=partial(int_minmax_type, xmin=1, xmax=100),
        help='Maximum number of items to retrieve')

    argp_api.add_argument(
        '--startitem', metavar='N', default=0, type=int,
        help='Start retrieval at this offset (useful for pagination)')

    # argp_api.add_argument('--startrow', default=0, type=int,
    #                       help='Row index to start retrieval from (for pagination)')

    argp_api.add_argument(
        '--langs', type=language_type, default='eng,deu',
        help='Preferred languages (3-character code, decreasing preference)')

    # subparser: publications

    argp_pub = subparsers.add_parser(
        'publications', parents=[argp_api], aliases=['pub'],
        help='Retrieve publications')

    argp_pub.add_argument(
        '--id', type=intlist, metavar='ID[,ID,..]',
        help='Retrieve publications by their ID')

    argp_pub.add_argument(
        '--pers-id', type=intlist, metavar='ID[,ID,..]',
        help='Retrieve publications associated with these person IDs')

    argp_pub.add_argument(
        '--inst-id', type=intlist, metavar='ID[,ID,..]',
        help='Retrieve publications associated with these institution IDs')

    argp_pub.add_argument(
        '--proj-id', type=intlist, metavar='ID[,ID,..]',
        help='Retrieve publications associated with these project IDs')

    argp_pub.add_argument(
        '--title', metavar='TERM',
        help='Retrieve publications with a title that contain TERM')

    argp_pub.add_argument(
        '--years', metavar='YYYY[-YYYY]', type=year_range_type,
        help='Limit publication years')

    argp_pub.add_argument(
        '--maxpers', metavar='N', default=0, type=int,
        help='Limit the number of listed authors')

    argp_pub.add_argument(
        '--author-abbrev', metavar='STR', nargs='?', const='',
        help='Abbreviate first author names [with given character]')

    argp_pub.add_argument(
        '--author-reverse', action='store_true',
        help='Reverse author names, having last name come first')

    argp_pub.add_argument(
        '--author-sep', metavar='STR',
        help='Separate author names with STR')

    group_fields = argp_pub.add_mutually_exclusive_group()

    group_fields.add_argument(
        '--fields', metavar='F[,F,...]', type=pub_fields_type,
        help='Field(s) to include in response. '
             'Available fields: ' + ', '.join(PUBLICATION_FIELDS))

    group_fields.add_argument(
        '--fieldset', metavar='NAME', type=pub_fieldset_type,
        help='Predefined set of fields. '
             'Available sets: ' + str(list(publication_fieldsets.keys())))

    argp_pub.add_argument(
        '--format', choices=['markdown', 'html', 'json'],
        help='Output file format. Ignored if --template is provided. '
             'For json, some post-retrieval operations (e.g. author name modifications)'
             'are not available yet.')

    argp_pub.add_argument(
        '--template', metavar='FILE', type=Path,
        help='Jinja2 template to use for output rendering')

    argp_pub.add_argument(
        '--out', type=Path,
        help='Output file, otherwise stdout')

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


def get_output_format(args):
    # template argument overrides any format arg
    if args.template:
        return ExportFormat.TEMPLATE

    if args.format:
        fmt = args.format
    elif args.out:
        match args.out.suffix.lower():
            case ('.htm' | '.html'):
                fmt = ExportFormat.HTML
            case '.md':
                fmt = ExportFormat.MARKDOWN
            case _:
                fmt = ExportFormat.JSON
    else:
        fmt = ExportFormat.MARKDOWN

    return fmt


def create_freidok_client(args):
    if args.source.startswith('http'):
        reader = FreidokApiClient(
            base_url=args.source,
            user_agent=USER_AGENT,
            dryrun=args.dryrun,
            default_max_items=args.maxitems)
    else:
        reader = FreidokFileReader(file=args.source)

    return reader


def get_publications(args):
    client = create_freidok_client(args)

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
        fields = publication_fieldsets['default']

    # sort params
    # todo: make sort parameters available on command line
    sortfields = []
    if 'publication_year' in fields:
        sortfields.append('publication_year+desc')
    if 'id' in fields:
        sortfields.append('id+desc')
    params = dict(sortfield=','.join(sortfields))

    data = client.get_publications(
        ids=args.id,
        inst_ids=args.inst_id,
        pers_ids=args.pers_id,
        proj_ids=args.proj_ids,
        title=args.title,
        year_from=year_from,
        year_to=year_to,
        fields=fields,
        maxpers=args.maxpers,
        maxitems=args.maxitems,
        startitem=args.startitem,
        **params,
    )

    publist = Publications(**data)

    # modify publication list

    if args.author_abbrev:
        modify.shorten_firstnames(publist, sep=args.author_abbrev)

    # add pre-formatted authors list to each publication object (_extras_authors)
    modify.add_author_list_string(
        publist, abbrev=args.author_abbrev, reverse=args.author_reverse,
        sep=args.author_sep)

    # sort titles by preferred language
    modify.sort_items_by_language(publist, preferred=args.langs)
    # sort publication links by type
    modify.sort_links_by_type(publist, preferred=['doi'])

    outfile = args.out or '-'
    outfmt = get_output_format(args)
    match outfmt:
        case ExportFormat.HTML:
            PublicationsHtmlExporter.export(
                publist, outfile, template_file=args.template)
        case ExportFormat.MARKDOWN:
            PublicationsMarkdownExporter.export(
                publist, outfile, template_file=args.template)
        case ExportFormat.TEMPLATE:
            exporter = PublicationsTemplateExporter()
            exporter.export(
                publist, outfile, template_file=args.template)
        case ExportFormat.JSON:
            with opens(outfile, encoding='utf-8') as f:
                json.dump(data, f)
        case _:
            raise NotImplementedError(f'Unsupported format: {outfmt}')


def get_institutions(args):
    client = FreidokApiClient(base_url=args.url, user_agent=USER_AGENT,
                              dryrun=args.dryrun,
                              default_max_rows=args.maxrows)

    data = client.get_institutions(
        ids=args.id,
        name=args.name,
    )
    print(data)
