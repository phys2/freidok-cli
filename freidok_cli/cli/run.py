import json
import sys
import warnings
from enum import Enum

from dotenv import load_dotenv

from freidok_cli import modify
from freidok_cli.cli import options
from freidok_cli.client import FreidokApiClient, FreidokFileReader
from freidok_cli.export import (
    InstitutionsHtmlExporter,
    InstitutionsMarkdownExporter,
    PublicationsHtmlExporter,
    PublicationsMarkdownExporter,
    TemplateExporter,
)
from freidok_cli.models.institutions import Institutions
from freidok_cli.models.publications import Publications
from freidok_cli.utils import opens
from freidok_cli.version import __version__

USER_AGENT = f"freidok-cli/{__version__}"


class ExportFormat(str, Enum):
    MARKDOWN = "markdown"
    HTML = "html"
    JSON = "json"
    TEMPLATE = "template"


def main():
    load_dotenv()

    args = options.arguments(
        func_institutions=get_institutions,
        func_publications=get_publications,
    )

    with warnings.catch_warnings(record=True) as caught_warnings:
        warnings.simplefilter("always")
        args.func(args)
        for warn in caught_warnings:
            print(f"{warn.category.__name__}: {warn.message}", file=sys.stderr)


def get_output_format(args):
    # template argument overrides any other format argument
    if args.template:
        return ExportFormat.TEMPLATE

    if args.format:
        return args.format

    if args.out:
        match args.out.suffix.lower():
            case (".htm" | ".html"):
                return ExportFormat.HTML
            case ".json":
                return ExportFormat.JSON
            case _:
                return ExportFormat.MARKDOWN

    return ExportFormat.MARKDOWN


def create_freidok_client(args):
    if args.source.startswith("http"):
        return FreidokApiClient(
            base_url=args.source,
            user_agent=USER_AGENT,
            dryrun=args.dryrun,
            default_max_items=args.maxitems,
        )
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
        fields = options.publication_fieldsets[args.fieldset]
    else:
        fields = options.publication_fieldsets["default"]

    # additional API parameters
    params = {}

    # sort params
    # todo: make sort parameters available on command line
    sortfields = []
    if "publication_year" in fields:
        sortfields.append("publication_year+desc")
    if "id" in fields:
        sortfields.append("id+desc")
    if sortfields:
        params["sortfield"] = ",".join(sortfields)

    if args.api_params:
        params.update(args.api_params)

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

    if args.langs != ["ALL"]:
        data = modify.json_strip_languages(data, preferred=args.langs)

    publist = Publications(**data)

    if args.exclude_authors:
        modify.exclude_publications_by_author(publist, names=args.exclude_authors)

    if args.exclude_titles:
        modify.exclude_publications_by_title(publist, titles=args.exclude_titles)

    # add pre-formatted authors list to each publication object (_extras_authors)
    modify.add_author_list_string(
        publist,
        abbrev=args.authors_abbrev,
        reverse=args.authors_reverse,
        sep=args.authors_sep,
    )

    if args.authors_abbrev:
        modify.shorten_author_firstnames(publist, sep=args.authors_abbrev)

    # sort publication links by type
    modify.sort_links_by_type(publist, preferred=["doi"])

    export(publist, data, args)


def get_institutions(args):
    client = create_freidok_client(args)
    data = client.get_institutions(
        ids=args.id,
        name=args.name,
    )

    if args.langs != ["ALL"]:
        data = modify.json_strip_languages(data, preferred=args.langs)

    items = Institutions(**data)

    export(items, data, args)


def export(items, data, args):
    outfile = args.out or "-"
    outfmt = get_output_format(args)
    match outfmt:
        case ExportFormat.HTML if items.type == "publication":
            PublicationsHtmlExporter.export(items, outfile, template_file=args.template)

        case ExportFormat.HTML if items.type == "institution":
            InstitutionsHtmlExporter.export(items, outfile, template_file=args.template)

        case ExportFormat.MARKDOWN if items.type == "publication":
            PublicationsMarkdownExporter.export(
                items, outfile, template_file=args.template
            )

        case ExportFormat.MARKDOWN if items.type == "institution":
            InstitutionsMarkdownExporter.export(
                items, outfile, template_file=args.template
            )

        case ExportFormat.TEMPLATE:
            TemplateExporter().export(items, outfile, template_file=args.template)

        case ExportFormat.JSON:
            with opens(outfile, encoding="utf-8") as f:
                json.dump(data, f, indent=2)

        case _:
            raise NotImplementedError(f"Unsupported format: {outfmt}")
