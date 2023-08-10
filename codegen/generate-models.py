#!/usr/bin/env python
"""
Generate Python code (Pydantic model classes) from JSON Schema.
"""
import argparse
import shlex
import subprocess
import sys

FREIDOK_SCHEMA_PUB = (
    "https://freidok.uni-freiburg.de/site/interfaces?dl=schema_publications"
)

CMD_NOT_FOUND_MSG = """
Error: {cmd} cannot be found.

Install with
     poetry install --with dev
or
     pip install datamodel-code-generator[http]
"""


def arguments():
    argp = argparse.ArgumentParser(
        prog="generate-models",
        description=__doc__,
    )

    argp.add_argument("outfile", help="Output file")
    argp.add_argument("--schema", metavar="SRC", help="JSON Schema file or URL")

    return argp.parse_args()


def main():
    args = arguments()

    # base class for all generated models
    base_class = "freidok_cli.models.base.BaseModel"

    source = args.schema or FREIDOK_SCHEMA_PUB

    if source.startswith(("http:", "https:")):
        source = f'--url "{source}"'
    else:
        source = f'--input "{source}"'

    cmdstr = f"""
        datamodel-codegen
        --use-schema-description
        --use-field-description
        --target-python-version 3.10
        --use-double-quotes
        --use-standard-collections
        --encoding utf-8
        --allow-extra-fields
        --use-annotated
        --force-optional
        --base-class {base_class}
        --output {args.outfile}
        {source}
    """

    cmd = shlex.split(cmdstr)

    try:
        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
    except FileNotFoundError:
        msg = CMD_NOT_FOUND_MSG.format(cmd=cmd[0]).strip()
        print(msg, file=sys.stderr)
        exit(1)

    print(process.stdout)
    if process.returncode:
        print(f"{cmd[0]} returned an error")
    exit(process.returncode)


if __name__ == "__main__":
    main()
