from typing import Sequence

from freidok_cli.models.publications import Publications, Person, Doc


def preference_index(value, preferred_values: list):
    """
    Return the list index of a value or the list length.

    Useful for sorting items based on a sorted list of preferred values.
    With Python's sort being stable, items that don't match any value in the
    preference list keep their relative order.

    Example:
        >>> items = [4, 7, 8, 2, 9, 1, 6]
        >>> prefs = [1, 2, 3]
        >>> sorted(items, key=lambda t: preference_index(t, prefs))
        [1, 2, 4, 7, 8, 9, 6]
    """
    try:
        return preferred_values.index(value)
    except ValueError:
        return len(preferred_values)


def json_strip_languages(node, attr="language", preferred=("eng", "deu", "ger")):
    """
    Recursively traverse a json dict and remove objects in non-preferred languages.

    :param node: Node in json dict tree
    :param attr: Sort lists with dict items having this key
    :param preferred: Sequence of preferred languages
    """
    if isinstance(node, dict):
        return {k: json_strip_languages(v, attr, preferred) for k, v in node.items()}
    elif isinstance(node, list):
        # is a proper list of objects having a matching attribute?
        if len(node) > 1 and isinstance(node[0], dict) and attr in node[0]:
            # sort by language
            node.sort(key=lambda x: preference_index(x[attr], preferred))
            # remove all but first item(s) (with the preferred language)
            k = 1
            while k < len(node) and node[k][attr] == node[0][attr]:
                k += 1
            node = node[0:k]
        return [json_strip_languages(item, attr, preferred) for item in node]
    else:
        return node


# def walk_dict_sort_by_attr(node, attr, sorter):
#     """
#     Recursively traverse a (json) dict and apply custom sorter to selected lists.
#
#     :param node: Node in json dict tree
#     :param attr: Sort lists with dict items having this key
#     :param sorter: List sort function
#     """
#     if isinstance(node, dict):
#         for val in node.values():
#             walk_dict_sort_by_attr(val, attr, sorter)
#     elif isinstance(node, list):
#         # is a proper list of objects having a matching attribute?
#         if len(node) > 1 and isinstance(node[0], dict) and attr in node[0]:
#             node.sort(key=sorter)
#         for item in node:
#             walk_dict_sort_by_attr(item, attr, sorter)


def sort_links_by_type(publist: Publications, preferred: list[str]):
    """Sort specific publication links by type"""
    for pub in publist.docs:
        # move preferred link types to beginning
        if pub.pub_ids:
            pub.pub_ids.sort(key=lambda p: preference_index(p.type, preferred))


def shorten_author_firstnames(publist: Publications, sep=""):
    """Shorten author first names"""
    for pub in publist.docs:
        for pers in pub.persons:
            if pers.forename:
                pers.forename = _abbreviate(pers.forename, sep)


def _abbreviate(name, sep=""):
    """Abbreviate names, e.g. Roland Werner Friedrich -> RWF"""
    if not name:
        return ""
    else:
        return sep.join(c[0].upper() for c in name.split()) + sep


def get_author_name(author: Person, abbrev: str | None = None, reverse=False):
    firstname = author.forename or ""
    lastname = author.surname or ""

    if abbrev is not None:
        firstname = _abbreviate(firstname, sep=abbrev)

    if reverse:
        name = f"{lastname} {firstname}"
    else:
        name = f"{firstname} {lastname}"

    return name.strip()


def add_author_list_string(
    publist: Publications, abbrev: str | None = None, reverse=False, sep=None
):
    """Add pre-formatted authors list as extra field"""
    if sep is None:
        sep = ", "
    for pub in publist.docs:
        authors = [get_author_name(a, abbrev, reverse) for a in pub.persons]
        pub._extras_authors = sep.join(authors)


def publication_has_author(pub: Doc, names: str | list[str]):
    """
    Return true if the author name(s) of a publication match any of the
    given name values, otherwise false.

    The string comparison is case insensitive.

    :param pub: Publication
    :param names: One or many string values
    :return: True, if some author name matches, otherwise false
    """
    if isinstance(names, str):
        names = [names]
    names = [p.lower() for p in names]
    for pers in pub.persons:
        name_value = get_author_name(pers)
        for name in names:
            if name in name_value.lower():
                return True
    return False


def publication_has_title(pub: Doc, titles: str | Sequence[str]):
    """
    Return true if the title(s) of a publication match any of the
    given title values, otherwise false.

    The string comparison is case insensitive.

    :param pub: Publication
    :param titles: One or many string values
    :return: True, if some title matches, otherwise false
    """
    if isinstance(titles, str):
        titles = [titles]
    titles = [t.lower() for t in titles]
    for title_value in pub.titles:
        for title in titles:
            if title in title_value.value.lower():
                return True
    return False


def exclude_publications_by_author(publist: Publications, names: str | Sequence[str]):
    """
    Remove publications having authors matching any of the provided name(s).

    :param publist: Publication list
    :param names: One or many string values
    :return: List of publications
    """
    # fmt: off
    publist.docs = [
        pub
        for pub in publist.docs
        if not publication_has_author(pub, names)
    ]
    # fmt: on


def exclude_publications_by_title(publist: Publications, titles: str | list[str]):
    """
    Remove publications having titles matching any of the provided name(s).

    :param publist: Publication list
    :param titles: One or many string values
    :return: List of publications
    """
    # fmt: off
    publist.docs = [
        pub
        for pub in publist.docs
        if not publication_has_title(pub, titles)
    ]
    # fmt: on
