from freidok.models.api import Publications, Person


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


def sort_items_by_language(publist: Publications, preferred: list[str]):
    """Sort specific publication data by preferred language"""
    for pub in publist.docs:
        attributes = ['titles', 'abstracts']
        for attr in attributes:
            if items := getattr(pub, attr, None):
                items.sort(key=lambda t: preference_index(t.language, preferred))


def sort_links_by_type(publist: Publications, preferred: list[str]):
    """Sort specific publication links by type"""
    for pub in publist.docs:
        # move preferred link types to beginning
        pub.pub_ids.sort(key=lambda p: preference_index(p.type, preferred))


def shorten_firstnames(publist: Publications, sep=''):
    """Shorten author first names"""
    for pub in publist.docs:
        for pers in pub.persons:
            if pers.forename:
                pers.forename = _abbreviate(pers.forename, sep)


def _abbreviate(name, sep=''):
    """Abbreviate names, e.g. Roland Werder Friedrich -> RWF"""
    if not name:
        return ''
    else:
        return sep.join(c[0].upper() for c in name.split()) + sep


def get_author_name(author: Person, abbrev: str | None = None, reverse=False):
    firstname = author.forename or ''
    lastname = author.surname or ''

    if abbrev is not None:
        firstname = _abbreviate(firstname, sep=abbrev)

    names = [firstname, lastname]

    if reverse:
        names = reversed(names)

    name = ' '.join(names)

    return name


def add_author_list_string(
        publist: Publications, abbrev: str | None = None, reverse=False, sep=None):
    """Add pre-formatted authors list as extra field"""
    if sep is None:
        sep = ', '
    for pub in publist.docs:
        authors = [get_author_name(a, abbrev, reverse) for a in pub.persons]
        pub._extras_authors = sep.join(authors)
