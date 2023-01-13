import re
import warnings
from enum import Enum
from pathlib import Path

import lxml.html as lxhtml
from lxml.html import etree, builder as E

from freidok.models.freidok_json_api import Doc, Publications, Person
from freidok.utils import first


class AuthorsListStyle(Enum):
    ORIGINAL = 1  # content of 'value' element as is
    FIRST_LAST = 2
    LAST_FIRST = 3
    LAST_ONLY = 4
    FIRST_LAST_ABBREV = 5
    FIRST_LAST_ABBREV_DOT = 6
    LAST_FIRST_ABBREV = 7
    LAST_FIRST_ABBREV_DOT = 8


class PublicationsExporter:
    def __init__(
            self,
            pref_langs: list[str] | None = None,
            author_list_style: AuthorsListStyle = AuthorsListStyle.ORIGINAL):
        self.prefered_languages = pref_langs or ['eng', 'deu']
        self.author_list_style = author_list_style

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

        match self.author_list_style:
            case AuthorsListStyle.ORIGINAL:
                return author.value
            case AuthorsListStyle.LAST_ONLY:
                return {author.surname}

            case AuthorsListStyle.FIRST_LAST:
                return f"{author.forename} {author.surname}"
            case AuthorsListStyle.FIRST_LAST_ABBREV:
                firstchars = _abbreviate(author.forename)
                return f"{firstchars} {author.surname}"
            case AuthorsListStyle.FIRST_LAST_ABBREV_DOT:
                firstchars = _abbreviate(author.forename)
                return f"{firstchars}. {author.surname}"

            case AuthorsListStyle.LAST_FIRST:
                return f"{author.surname} {author.forename}"
            case AuthorsListStyle.LAST_FIRST_ABBREV:
                firstchars = _abbreviate(author.forename)
                return f"{author.surname} {firstchars}"
            case AuthorsListStyle.LAST_FIRST_ABBREV_DOT:
                firstchars = _abbreviate(author.forename)
                return f"{author.surname} {firstchars}."

            case _:
                return author.value

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


class PublicationsHtmlExporter(PublicationsExporter):
    def __init__(self, class_prefix='publist', wrapper_element='div',
                 item_element='div', **kwargs):
        super().__init__(**kwargs)
        self.item_element = item_element
        self.wrapper_element = wrapper_element
        self.class_prefix = class_prefix

    def wrap(self, text, tag, cls=None):
        if cls:
            cls = f' class="{cls}"'
        return f'<{tag}{cls}>{text}</{tag}>'

    def format_authors(self, pub: Doc, parent_class: str):
        classname = f'{parent_class}-authors'
        authors = ", ".join(self.get_author_names(pub))
        return E.SPAN(E.CLASS(classname), authors)

    def format_title(self, pub: Doc, parent_class: str):
        classname = f'{parent_class}-title'
        title = self.get_best_title(pub)
        return E.SPAN(E.CLASS(classname), title)

    def format_source(self, pub, parent_class: str):
        classname = f'{parent_class}-source'
        src = self.get_source(pub)

        # data dict
        data = {
            'name': src.title or '<unknown>',
            'volume': src.volume,
            'year': src.year,
            'pages': src.page,
            'issue': src.issue,
        }

        # convert to html elements
        for key, value in data.items():
            if value:
                _class = classname + '-' + key
                data[key] = f'<span class="{_class}">{str(value)}</span>'

        # todo: user-defined templates
        template = '{name} {volume} ({year}) {issue}, {pages}'
        text = template.format(**data)
        # remove leftover chars from substitution with empty string
        text = re.sub(r' [ ,]+', ' ', text)
        text = text.replace('()', '')

        text = f'<span class="{classname}">{text}</span>'
        html = lxhtml.fragment_fromstring(text)

        return html

    def format_link(self, pub: Doc, classname: str):
        if not pub.pub_ids:
            return ''
        if doi := first(pub.pub_ids, lambda p: p.type == 'doi'):
            link = doi.link
        else:
            link = pub.pub_ids[0].link

        return E.SPAN(
            E.CLASS(f'{classname}-url'),
            E.A(href=link, title="Go to Publication")
        )

    def format_publication(self, pub: Doc):
        classname = f'{self.class_prefix}-pub'

        authors = self.format_authors(pub, classname)
        title = self.format_title(pub, classname)
        source = self.format_source(pub, classname)
        link = self.format_link(pub, classname)

        html = E.DIV(
            E.CLASS(classname),
            authors, "\n",
            title, "\n",
            source, "\n",
            link, "\n",
        )

        return html

    def export(self, publications: Publications, file: str | Path):
        container = E.DIV(E.CLASS(self.class_prefix))
        head = E.HEAD(
            E.LINK(rel='stylesheet', href='styles.css')
        )
        body = E.BODY(
            container
        )
        root = E.HTML(head, body, lang='en')

        for pub in publications.docs:
            pub_elem = self.format_publication(pub)
            container.append(pub_elem)

        tree = etree.ElementTree(root)
        d = lxhtml.tostring(tree, pretty_print=True, doctype='<!DOCTYPE html>',
                            include_meta_content_type=True, encoding='unicode')
        with open(file, 'w') as f:
            print(d, file=f)
        print(d)
