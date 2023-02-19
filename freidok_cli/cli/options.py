import argparse
import os
import re
from functools import partial
from pathlib import Path
from typing import Callable

from freidok_cli.utils import str2list
from freidok_cli.version import __version__

API_FIELDS_PUBLICATION = [
    "id",
    "link",
    "abstracts",
    "researchdata_descriptions",
    "descriptions",
    "messages",
    "classifications",
    "pub_ids",
    "pub_ids_internal",
    "pubtype",
    "languages",
    "edition",
    "keywords",
    "keywords_uncontrolled",
    "publication_year",
    "peerreviewed",
    "day_of_exam",
    "system_time",
    "titles",
    "title_parents",
    "persons",
    "persons_stat",
    "affiliations_list",
    "functions_list",
    "institutions",
    "relations",
    "reverse_relations",
    "publisher",
    "source_journal",
    "source_compilation",
    "size",
    "series",
    "contract",
    "license_metadata",
    "license",
    "contact",
    "fundings",
    "preview_image",
    "files_stat",
    "files",
    "files_external",
    "oa_status",
    "revision",
    "acquisition_type",
    "fachsigel",
    "state",
    "locked",
    "issued",
    "created_by",
    "submission_type",
    "current_person_affiliations",
    "current_institution_affiliations",
    "current_project_affiliations",
    "current_activity_affiliations",
]

# Sets of fields can be predefined via environment variables
# starting with FREIDOK_FIELDSET_PUBLICATION_
publication_fieldsets = {
    "default": (
        "id link publication_year titles publisher persons persons_stat pubtype "
        "source_journal source_compilation pub_ids preview_image".split()
    )
}


def env2dict(
    env_prefix: str,
    key_mapper: Callable[[str], str] = str,
    value_mapper: Callable = None,
):
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
        "FREIDOK_FIELDSET_PUBLICATION_", key_mapper=str.lower, value_mapper=str2list
    )
    publication_fieldsets.update(d)


def arguments(func_institutions, func_publications):
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
        if re.match(r"^\d{4}(?:-\d{4})?$", y):
            return list(map(int, y.split("-")))
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
            if not re.match(r"^[a-zA-Z]{3}$", item):
                raise argparse.ArgumentTypeError(
                    f"Invalid 3-letter language code: '{item}'"
                )
        else:
            return items

    def api_params_type(value):
        params = {}
        for item in value.split():
            try:
                key, val = item.split("=")
                params[key] = val
            except ValueError:
                raise argparse.ArgumentTypeError(
                    f"Invalid API parameter string: '{value}' ({item})"
                )
        return params

    # root parser
    argp_main = argparse.ArgumentParser(
        prog="freidok",
        add_help=False,
        description=(
            "Retrieve publications from FreiDok API and render them as html, Markdown"
            " or any other text format via Jinja2 templates."
        ),
    )
    group = argp_main.add_argument_group("options")
    group.add_argument(
        "-h",
        "--help",
        action="help",
        help="Show this help text",
    )

    group.add_argument(
        "--version",
        action="version",
        help="Show version info",
        version=f"%(prog)s {__version__}",
    )

    # parent parser for all api subparsers
    argp_api = argparse.ArgumentParser(add_help=False)

    # common subparser options
    argp_api.add_argument(
        "--format",
        choices=["markdown", "html", "json"],
        help="Output file format (ignored if --template is provided)",
    )

    argp_api.add_argument(
        "--template",
        metavar="FILE",
        type=Path,
        default=os.getenv("FREIDOK_TEMPLATE"),
        help="Custom Jinja2 template file path (env: FREIDOK_TEMPLATE)",
    )

    argp_api.add_argument(
        "--out",
        type=Path,
        help="Output file, otherwise stdout",
    )

    argp_api.add_argument(
        "-h",
        "--help",
        action="help",
        help="Show this help text",
    )

    # group for common API settings
    argp_api_settings = argp_api.add_argument_group("general settings")

    env_url = os.getenv("FREIDOK_URL", "https://freidok.uni-freiburg.de/jsonApi/v1/")
    argp_api_settings.add_argument(
        "--source",
        default=env_url,
        required=not env_url,
        help="URL of FreiDok JSON API or path to JSON file (env: FREIDOK_URL)",
    )

    argp_api_settings.add_argument(
        "--maxitems",
        metavar="N",
        default=100,
        type=partial(int_minmax_type, xmin=1, xmax=100),
        help="Maximum number of items to retrieve",
    )

    argp_api_settings.add_argument(
        "--startitem",
        metavar="N",
        default=0,
        type=int,
        help="Start index of retrieved items (useful for pagination)",
    )

    default_langs = "eng,deu"
    env_langs = os.getenv("FREIDOK_LANGUAGES", default_langs)
    argp_api_settings.add_argument(
        "--langs",
        metavar="LANG[,LANG...]",
        type=language_type,
        default=env_langs,
        help=(
            "Comma-separated list of preferred languages "
            f"(3-letter codes, decreasing preference, default: '{default_langs}', "
            f"env: FREIDOK_LANGUAGES)"
        ),
    )

    argp_api_settings.add_argument(
        "-n",
        "--dryrun",
        action="store_true",
        help="Only print API request, don't send it",
    )

    subparsers = argp_main.add_subparsers(title="actions", description="", help="")

    #
    # subparser: publications
    #

    sub_pub = subparsers.add_parser(
        "publ", parents=[argp_api], help="Retrieve publications", add_help=False
    )

    sub_pub_filters = sub_pub.add_argument_group("filter options")
    sub_pub_filters.add_argument(
        "--id",
        type=intlist,
        metavar="ID[,ID...]",
        help="Retrieve publications by ID",
    )

    sub_pub_filters.add_argument(
        "--pers-id",
        type=intlist,
        metavar="ID[,ID...]",
        help="Filter by person IDs",
    )

    sub_pub_filters.add_argument(
        "--inst-id",
        type=intlist,
        metavar="ID[,ID...]",
        help="Filter by institution IDs",
    )

    sub_pub_filters.add_argument(
        "--proj-id",
        type=intlist,
        metavar="ID[,ID...]",
        help="Filter by project IDs",
    )

    sub_pub_filters.add_argument(
        "--title",
        metavar="TERM",
        help="Filter by title ('contains')",
    )

    sub_pub_filters.add_argument(
        "--years",
        metavar="YYYY[-YYYY]",
        type=year_range_type,
        default=0,
        help="Filter by year of publication",
    )

    sub_pub_filters.add_argument(
        "--maxpers",
        metavar="N",
        default=0,
        type=int,
        help="Limit the number of listed authors",
    )

    sub_pub_filters.add_argument(
        "--exclude-author",
        metavar="NAME",
        action="append",
        dest="exclude_authors",
        help="Exclude publications where an author name ('<first> <last>') "
        "contains NAME (case insensitive)",
    )

    sub_pub_filters.add_argument(
        "--exclude-title",
        metavar="TEXT",
        action="append",
        dest="exclude_titles",
        help="Exclude publications having TEXT in its title (case insensitive)",
    )

    group = sub_pub_filters.add_mutually_exclusive_group()

    group.add_argument(
        "--fields",
        metavar="F[,F...]",
        type=partial(multi_choice_type, allowed=API_FIELDS_PUBLICATION),
        help="Field(s) to include in response. Available fields: "
        + ", ".join(API_FIELDS_PUBLICATION),
    )

    group.add_argument(
        "--fieldset",
        metavar="NAME",
        type=partial(simple_choice_type, allowed=publication_fieldsets),
        help="Predefined set of fields. Available sets: "
        + str(list(publication_fieldsets.keys())),
    )

    sub_pub_filters.add_argument(
        "--params",
        metavar="STR",
        dest="api_params",
        type=api_params_type,
        help=(
            "Additional parameters passed to freidok API, "
            'e.g. "transitive=true pubtype=book"'
        ),
    )

    sub_pub_filters.add_argument(
        "--authors-abbrev",
        metavar="STR",
        nargs="?",
        const="",
        help=(
            "Abbreviate authors first names [with optional character] "
            "(ignored if --format=json)"
        ),
    )

    sub_pub_filters.add_argument(
        "--authors-reverse",
        action="store_true",
        help='List authors names as "last name, first name" (ignored if --format=json)',
    )

    sub_pub_filters.add_argument(
        "--authors-sep",
        metavar="STR",
        help="Separate individual authors with STR (ignored if --format=json)",
    )

    sub_pub.set_defaults(func=func_publications)

    #
    # subparser: institutions
    #

    sub_inst = subparsers.add_parser(
        "inst",
        parents=[argp_api],
        add_help=False,
        help="Retrieve institutions",
    )

    sub_inst_filters = sub_inst.add_argument_group("filter options")

    sub_inst_filters.add_argument(
        "--id",
        type=str2list,
        metavar="ID[,ID...]",
        help="One or many institution IDs",
    )

    sub_inst_filters.add_argument(
        "--name",
        type=str,
        metavar="TERM",
        help="Show institutions containing TERM",
    )

    sub_inst.set_defaults(func=func_institutions)

    return argp_main.parse_args()
