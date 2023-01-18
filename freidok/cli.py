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
    PublicationsMarkdownExporter, TemplateExporter
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


def env2dict(env_prefix: str, key_mapper: Callable[[str], str] = str,
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
    """Update pre-defined sets of fields from environment"""
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
                    f"Invalid 3-letter language code: '{item}'")
        else:
            return items

    # root parser
    argp_main = argparse.ArgumentParser(prog='freidok', add_help=False)
    group = argp_main.add_argument_group('options')
    group.add_argument(
        '-h', '--help', action='help',
        help="Show this help text")

    # parent parser for all api subparsers
    argp_api = argparse.ArgumentParser(add_help=False)

    # common subparser options
    argp_api.add_argument(
        '--format', choices=['markdown', 'html', 'json'],
        help='Output file format. Ignored if --template is provided. '
             'For json, some post-retrieval operations (e.g. author name modifications)'
             'are not available yet.')

    argp_api.add_argument(
        '--template', metavar='FILE', type=Path,
        help='Custom Jinja2 template file path')

    argp_api.add_argument(
        '--out', type=Path,
        help='Output file, otherwise stdout')

    argp_api.add_argument(
        '-h', '--help', action='help',
        help="Show this help text")

    # group for common API settings
    argp_api_settings = argp_api.add_argument_group('general settings')

    env_url = os.getenv('FREIDOK_URL')
    argp_api_settings.add_argument(
        '--source', default=env_url, required=not env_url,
        help='URL of FreiDok JSON API or path to JSON file')

    argp_api_settings.add_argument(
        '--maxitems', metavar='N', default=100,
        type=partial(int_minmax_type, xmin=1, xmax=100),
        help='Maximum number of items to retrieve')

    argp_api_settings.add_argument(
        '--startitem', metavar='N', default=0, type=int,
        help='Start index of retrieved items (useful for pagination)')

    default_langs = 'eng,deu'
    env_langs = os.getenv('FREIDOK_LANGUAGES', default_langs)
    argp_api_settings.add_argument(
        '--langs', type=language_type, default=env_langs,
        help='Comma-separated list of preferred languages '
             f"(3-letter codes, default={default_langs})")

    argp_api_settings.add_argument(
        '-n', '--dryrun', action='store_true',
        help="Only print API request, don't send it")

    subparsers = argp_main.add_subparsers(
        title='actions',
        description='',
        help='')

    #
    # subparser: publications
    #

    sub_pub = subparsers.add_parser(
        'publ', parents=[argp_api],
        help='Retrieve publications', add_help=False)

    sub_pub_filters = sub_pub.add_argument_group('filter options')
    sub_pub_filters.add_argument(
        '--id', type=intlist, metavar='ID[,ID,..]',
        help='Retrieve publications by ID')

    sub_pub_filters.add_argument(
        '--pers-id', type=intlist, metavar='ID[,ID,..]',
        help='Filter by person IDs')

    sub_pub_filters.add_argument(
        '--inst-id', type=intlist, metavar='ID[,ID,..]',
        help='Filter by institution IDs')

    sub_pub_filters.add_argument(
        '--proj-id', type=intlist, metavar='ID[,ID,..]',
        help='Filter by project IDs')

    sub_pub_filters.add_argument(
        '--title', metavar='TERM',
        help='Filter by title ("contains")')

    sub_pub_filters.add_argument(
        '--years', metavar='YYYY[-YYYY]', type=year_range_type, default=0,
        help='Filter by year of publication')

    sub_pub_filters.add_argument(
        '--maxpers', metavar='N', default=0, type=int,
        help='Limit the number of listed authors')

    group = sub_pub_filters.add_mutually_exclusive_group()

    group.add_argument(
        '--fields', metavar='F[,F,...]',
        type=partial(multi_choice_type, allowed=PUBLICATION_FIELDS),
        help='Field(s) to include in response. '
             'Available fields: ' + ', '.join(PUBLICATION_FIELDS))

    group.add_argument(
        '--fieldset', metavar='NAME',
        type=partial(simple_choice_type, allowed=publication_fieldsets),
        help='Predefined set of fields. '
             'Available sets: ' + str(list(publication_fieldsets.keys())))

    sub_pub_filters.add_argument(
        '--authors-abbrev', metavar='STR', nargs='?', const='',
        help='Abbreviate authors first names [with optional character]')

    sub_pub_filters.add_argument(
        '--authors-reverse', action='store_true',
        help='Reverse author names, having last name come first')

    sub_pub_filters.add_argument(
        '--authors-sep', metavar='STR',
        help='Separate author names with STR')

    sub_pub.set_defaults(func=get_publications)

    #
    # subparser: institutions
    #

    sub_inst = subparsers.add_parser(
        'inst', parents=[argp_api], add_help=False,
        help='Retrieve institutions')

    sub_inst_filters = sub_inst.add_argument_group('filter options')

    sub_inst_filters.add_argument(
        '--id', type=str2list, metavar='ID1[,ID2,..]',
        help='One or many institution IDs')

    sub_inst_filters.add_argument(
        '--name', type=str, metavar='TERM',
        help='Show institutions containing TERM')

    sub_inst.set_defaults(func=get_institutions)

    return argp_main.parse_args()


def run():
    args = arguments()
    args.func(args)


def get_output_format(args):
    # template argument overrides any other format argument
    if args.template:
        return ExportFormat.TEMPLATE

    if args.format:
        return args.format

    if args.out:
        match args.out.suffix.lower():
            case ('.htm' | '.html'):
                return ExportFormat.HTML
            case '.md':
                return ExportFormat.MARKDOWN
            case _:
                return ExportFormat.JSON

    return ExportFormat.MARKDOWN


def create_freidok_client(args):
    if args.source.startswith('http'):
        return FreidokApiClient(
            base_url=args.source,
            user_agent=USER_AGENT,
            dryrun=args.dryrun,
            default_max_items=args.maxitems)
    else:
        return FreidokFileReader(file=args.source)


def get_publications(args):
    client = create_freidok_client(args)

    # year params
    if args.years:
        year_from = args.years[0]
        year_to = args.years[1] if len(args.years) > 1 else year_from
    else:
        year_from = None
        year_to = None

    # field params
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
        proj_ids=args.proj_id,
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

    if args.authors_abbrev:
        modify.shorten_author_firstnames(publist, sep=args.authors_abbrev)
    # add pre-formatted authors list to each publication object (_extras_authors)
    modify.add_author_list_string(
        publist, abbrev=args.authors_abbrev, reverse=args.authors_reverse,
        sep=args.authors_sep)
    # sort titles, abstracts, etc. by preferred language
    modify.sort_items_by_language(publist, preferred=args.langs)
    # sort publication links by type
    modify.sort_links_by_type(publist, preferred=['doi'])

    export(publist, data, args)


def get_institutions(args):
    client = create_freidok_client(args)

    data = client.get_institutions(
        ids=args.id,
        name=args.name,
    )
    print(data)


def export(publist, data, args):
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
            TemplateExporter().export(
                publist, outfile, template_file=args.template)
        case ExportFormat.JSON:
            with opens(outfile, encoding='utf-8') as f:
                json.dump(data, f)
        case _:
            raise NotImplementedError(f'Unsupported format: {outfmt}')
