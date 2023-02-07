import abc
from pathlib import Path

import jinja2

from freidok.models.publications import Publications
from freidok.utils import opens


class Exporter(metaclass=abc.ABCMeta):
    """
    Publications exporter base class.
    """

    pass


class TemplateExporter(Exporter):
    """
    Export publications via Jinja2 templates.
    """

    def __init__(self, default_template=None, jinja_args=None, **kwargs):
        self.default_template = default_template
        self.environment_args = dict(lstrip_blocks=True, trim_blocks=True)
        if jinja_args:
            self.environment_args.update(jinja_args)

    def _load_template(self, template_file: Path | None):
        """Load Jinja2 template from file"""
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_file.parent),
            **self.environment_args,
        )
        return env.get_template(template_file.name)

    def _load_default_template(self):
        """Load Jinja2 template from our package"""
        env = jinja2.Environment(
            loader=jinja2.PackageLoader("freidok", "templates"), **self.environment_args
        )
        return env.get_template(self.default_template)

    def export(
        self, publications: Publications, outfile: str | Path, template_file=None
    ):
        context = {
            "items": publications.docs,
        }

        if template_file:
            template = self._load_template(template_file)
        elif self.default_template:
            template = self._load_default_template()
        else:
            raise ValueError("No template specified")

        with opens(outfile, mode="w", encoding="utf-8") as fout:
            fout.write(template.render(context))


PublicationsHtmlExporter = TemplateExporter(
    default_template="publications/simple-list.html", jinja_args=dict(autoescape=True)
)

PublicationsMarkdownExporter = TemplateExporter(
    default_template="publications/simple-list.md"
)

InstitutionsHtmlExporter = TemplateExporter(
    default_template="institutions/simple-list.html", jinja_args=dict(autoescape=True)
)

InstitutionsMarkdownExporter = TemplateExporter(
    default_template="institutions/simple-list.md"
)
