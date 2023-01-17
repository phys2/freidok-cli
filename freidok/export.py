import warnings
from pathlib import Path

import jinja2

from freidok.models.api import Doc, Publications, Person
from freidok.utils import first, preference_score, opens


def sort_items_by_preferred_languages(publist: Publications,
                                      preferred_langs: list[str]):
    for pub in publist.docs:
        pub.titles.sort(key=lambda t: preference_score(t.language, preferred_langs))


def sort_links_by_preferred_type(publist: Publications, preferred_types: list[str]):
    for pub in publist.docs:
        pub.pub_ids.sort(key=lambda p: preference_score(p.type, preferred_types))


class PublicationsExporter:
    def __init__(
            self,
            pref_langs: list[str] | None = None,
            abbreviate_author_names=False):
        self.prefered_languages = pref_langs or ['eng', 'deu']
        self.abbreviate_author_names = abbreviate_author_names

    def get_best_title(self, pub: Doc) -> str:
        for lang in self.prefered_languages:
            if t := first(pub.titles, lambda _: _.language == lang):
                return t.value

        # no preferred language found, fall back to first title
        return pub.titles[0].value

    def get_author_name(self, author: Person):
        def _abbreviate(name):
            if not name:
                return ''
            else:
                return "".join(c[0].upper() for c in name.split())

    def get_author_names(self, pub: Doc):
        return [self.get_author_name(a) for a in pub.persons]

    def get_source(self, pub: Doc):
        # take first
        journal = pub.source_journal[0]
        if not journal:
            warnings.warn('No journal data available for publication', pub.id)
            return []
        if len(pub.source_journal) > 1:
            warnings.warn('More than one source journal available for', pub.id)

        return journal


class PublicationsTemplateExporter(PublicationsExporter):
    """Export publications via Jinja2 templates"""

    def __init__(self, default_template=None, jinja_args=None, **kwargs):
        super().__init__(**kwargs)
        self.default_template = default_template
        if not jinja_args:
            jinja_args = {}
        self.environment_args = dict(lstrip_blocks=True, trim_blocks=True, **jinja_args)

    def _load_template(self, template_file: Path | None):
        """Load Jinja2 template from file"""
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_file.parent),
            **self.environment_args
        )
        return env.get_template(template_file.name)

    def _load_default_template(self):
        """Load Jinja2 template from our package"""
        env = jinja2.Environment(
            loader=jinja2.PackageLoader('freidok', 'templates'),
            **self.environment_args
        )
        return env.get_template(self.default_template)

    def export(self, publications: Publications, outfile: str | Path,
               template_file=None):
        context = {
            'publications': publications.docs,
        }

        if template_file:
            template = self._load_template(template_file)
        else:
            template = self._load_default_template()

        with opens(outfile, mode='w', encoding='utf-8') as fout:
            fout.write(template.render(context))


PublicationsHtmlExporter = PublicationsTemplateExporter(
    default_template='simple-list.html', jinja_args=dict(autoescape=True))
PublicationsMarkdownExporter = PublicationsTemplateExporter(
    default_template='simple-list.md')
