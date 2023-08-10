# freidok-cli

A command-line client for
**[FreiDok](https://freidok.uni-freiburg.de/)**, 
the publication platform, institutional bibliography and research documentation 
system of the [University of Freiburg](https://www.uni-freiburg.de), Germany. 

## What it does

Retrieve information about institutions and publications of the University of 
Freiburg, using the FreiDok API. 

Specifically, the client can
  - search for an institution by name
  - retrieve publication lists for any institution, person, project, date, etc.
  - export publication lists to any text format (e.g. HTML, Markdown) via Jinja2 
    templates 

_Note: The client does not cover the complete FreiDok API, it is focused on 
retrieving publication data in an easy but flexible way._

## Installation

```bash
pip install freidok-cli
```

The ```freidok``` executable will be available after installation. 

## Usage

Two subcommands are available:

  - `freidok publ` retrieves publication data
  - `freidok inst` retrieves university institutions

### Retrieve institutions

#### Examples

```bash
# Print the ids and names of all institutions with *physiol* in its name
freidok inst --name physiol

# Export data to html, prefer German names
freidok inst --name physiol --out inst.html --langs=deu,ger,eng
```

### Retrieve publications

#### Examples

```bash
# create an html file listing publications from a specific institution
freidok publ --inst-id 2555 --years 2020-2022 --out pubs.html

# create a markdown file listing publications for a group of persons, prefer German titles
freidok publ --pers-id 100,1034,264 --langs=deu,ger,eng --out pubs.md

# pass extra API parameters and use a custom template
freidok publ --inst-id 2555 --years 2022 --params "transitive=true" --template my_publist.jinja2.html

# save results as JSON file (passthrough)
freidok publ --inst-id 2555 --years 2010-2022 --out db.json

# query local file
freidok publ --source db.json --years 2019
```

Run `freidok publ --help` to see a full list of arguments.
Here are the most common:

```
filter options:
  --id ID[,ID...]       Retrieve publications by ID
  --pers-id ID[,ID...]  Filter by person IDs
  --inst-id ID[,ID...]  Filter by institution IDs
  --proj-id ID[,ID...]  Filter by project IDs
  --title TERM          Filter by title ("contains")
  --years YYYY[-YYYY]   Filter by year of publication
  --maxpers N           Limit the number of listed authors
  --exclude-author STR  Exclude publications where an author name ("<first> <last>") contains STR.
  --fields F[,F...]     Field(s) to include in response. 
  --fieldset NAME       Predefined set of fields. Available sets: ['default', 'short']
  --params STR          Additional parameters passed to freidok API, e.g. "transitive=true pubtype=book"
  --authors-abbrev [STR]
                        Abbreviate authors first names [with optional character] (ignored if --format=json)
  --authors-reverse     List authors names as "last name, first name" (ignored if --format=json)
  --authors-sep STR     Separate individual authors with STR (ignored if --format=json)
```

### Output Format

Output files are created by rendering a Jinja2 template 
(except for JSON output). For HTML and Markdown, simple built-in templates 
are used by default. Custom templates can be used with `--template <file>`. 

To specify the output format, either 

  - use a recognized file extension for the output file _(.html, .md or .json)_,
 
  - set it explicitly with `--format html|markdown|json`

  - provide a custom Jinja2 template with `--template <file>`.
   
    _This will ignore any `--format` argument._

Omitting the output file name or setting it to "-" prints to _stdout_.
The default output format is _Markdown_.


### Templates

[Jinja2](https://palletsprojects.com/p/jinja/) templates are supported.
In the template, the list of retrieved items (publications, institutions, ...) 
is accessible via the ```items``` variable. Each item is a full
Python object deserialized from API responses.

This is a simple example for generating a Markdown list of publication titles 
and years: 

```
# Publications
{% for pub in items %}
- {{ pub.titles[0].value }} ({{ pub.publication_year.value }})
{% endfor %}
```

### Predefined Authors List

Creating well-formatted author lists in the template is not straighforward, 
since FreiDok returns authors as a list of individual _person_ objects. 
This list needs to be iterated, the separator character has to be placed 
correctly and whitespace issues have to be dealt with.

To facilitate the ouput of author lists in templates, each _publication_ 
object has the additional string attribute ```_extras_authors``` that 
contains a pre-formatted authors string.

Three arguments control the style of that author list:
```
--authors-abbrev [STR]  Abbreviate authors first names [with optional character]
--authors-reverse       List authors names as "last name, first name"
--authors-sep STR       Separate individual authors with STR
```

Examples:
```bash
# Example 1: default style
freidok publ [...]
# Maciej K. Kocylowski, Hande Aypek, Wolfgang Bildl

# Example 2: abbreviate authors with a dot, reverse order
freidok publ [...] --authors-abbrev="." --authors-reverse
# Kocylowski M.K., Aypek H., Bildl W.

# Example 3: separate abbreviated authors with a slash
freidok publ [...] --authors-abbrev --authors-sep=" / " 
# MK Kocylowski / H Aypek / W Bildl
```



### Environment variables

*.env* files are supported. The following environment variables are recognized: 

```bash
# Env variables and example values

# API URL
FREIDOK_URL=https://freidok.uni-freiburg.de/jsonApi/v1/

# list of preferred languages
FREIDOK_LANGUAGES=eng,deu,ger

# FREIDOK_FIELDSET_PUBLICATION_* can be used to define custom fieldsets
# (use with --fieldset short)
FREIDOK_FIELDSET_PUBLICATION_SHORT=id,link,publication_year,titles,publisher,persons,persons_stat
```

## Development

### Generate Python classes from JSON schema

Make sure to install the package with *dev* dependencies, this will install
[datamodel-code-generator](https://github.com/koxudaxi/datamodel-code-generator).

Then use `codegen/generate-models.py` to generate Pydantic models from JSON schema.


## Missing functionality

  - In contrast to _Institutions_, the search for _Person_ and _Project_ is not 
    implemented yet. To generate a publication list for these entities, you 
    need to find out the FreiDok ID manually using the FreiDok web page.
  - Automatic pagination is not implemented yet. The FreiDok API returns at most 
    100 items per request, so you need to handle pagination manually using the
    parameters `--startitem` and  `--maxitems`. 
