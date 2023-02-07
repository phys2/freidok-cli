import abc
import json
import warnings
from typing import Any

import requests
from requests.utils import get_encoding_from_headers

from freidok.utils import list2str


def create_headers(user_agent=None, user_email=None, extra_headers=None):
    """Build HTTP header dictionary"""
    headers = {}

    if user_agent:
        headers['User-Agent'] = user_agent

    if user_email:
        headers['X-User-Email'] = user_email

    if extra_headers:
        headers.update(extra_headers)

    return headers


def add_param(d: dict[str, Any], name: str, value: Any, overwrite=True) -> None:
    """
    Conditionally add single parameter to parameter dict.

    None values are ignored, existing keys are ignored by default.

    :param d: Parameter dictionary
    :param name: Parameter name
    :param value: Parameter value
    :param overwrite: Overwrite values of existing keys.
    """
    if d is not None and value is not None:
        if overwrite:
            d[name] = value
        else:
            d.setdefault(name, value)


class FreiDokReader(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def __init__(self, endpoint: str):
        self.endpoint = endpoint

    @abc.abstractmethod
    def get_publications(self):
        pass

    @abc.abstractmethod
    def get_institutions(self):
        pass


class FreidokApiClient(FreiDokReader):
    def __init__(self, base_url: str, user_agent: str, user_email=None,
                 extra_headers: dict[str, str] = None, default_max_items: int = 0,
                 dryrun=False):
        """
        FreiDok API client.

        :param base_url: API endpoint
        :param user_agent: User agent string.
        :param user_email: User email to include in request headers
        :param extra_headers: Additional header values
        :param default_max_items: Default row limit
        :param dryrun: If set to true, print request but don't send anything
        """
        if not base_url:
            raise ValueError("Invalid Freidok API URL")

        self.endpoint = base_url.rstrip('/')
        self.default_max_items = default_max_items
        self.headers = create_headers(user_agent, user_email, extra_headers)
        self.timeout = 30
        self.dryrun = dryrun

    def _print_prep_request(self, req, encoding=None):
        """Print a prepared request"""
        if not encoding:
            encoding = get_encoding_from_headers(req.headers)
        if body := req.body:
            body = req.body.decode(encoding) if encoding else '<binary data>'
        headers = '\n'.join(['{}: {}'.format(*hv) for hv in req.headers.items()])
        print(f"{req.method} {req.path_url} HTTP/1.1")
        print(headers)
        if body:
            print()
            print()
            print(body)

    def _get(self, url, params: dict[str, Any] = None):
        # set default max_rows value, is not already present
        if params and self.default_max_items:
            params.setdefault('maxRows', self.default_max_items)

        if self.dryrun:
            r = requests.Request('GET', url=url, headers=self.headers, params=params)
            self._print_prep_request(r.prepare())
            exit()

        r = requests.get(url, headers=self.headers, params=params,
                         timeout=self.timeout)
        r.raise_for_status()

        return r.json()

    def get_publications(
            self,
            ids: list[int] = None,
            inst_ids: list[int] = None,
            pers_ids: list[int] = None,
            proj_ids: list[int] = None,
            title: str = None,
            year_from: int = 0,
            year_to: int = 0,
            fields: list[str] = None,
            maxpers: int = None,
            maxitems: int = 0,
            startitem: int = 0,
            **kwargs):
        """
        Retrieve publcations from API.

        :param ids: Retrieve by publication IDs
        :param inst_ids: Retrieve by institution IDs
        :param pers_ids: Retrieve by person/author IDs
        :param proj_ids: Retrieve by project IDs
        :param title: Require publication titles to contain this value
        :param year_from: Filter out publications from before this year
        :param year_to: Filter out publications from after this year
        :param fields: Fields to include in the response (see API documentation)
        :param maxpers: Limit the number of reported authors
        :param maxitems: Limit the number of returned items
        :param startitem: Offset for item retrieval
        :param kwargs: Additional API parameters
        :return: Dictionary with deserialized response
        """
        url = self.endpoint + '/publications'

        params = {}
        add_param(params, 'publicationId', list2str(ids))
        add_param(params, 'instId', list2str(inst_ids))
        add_param(params, 'persId', list2str(pers_ids))
        add_param(params, 'projId', list2str(proj_ids))
        add_param(params, 'titleSearch', title)

        # some parameters are required (for this client, at least)
        if not params:
            raise ValueError(
                'Missing parameters! At least one of these parameters is required: '
                'ids, inst_ids, pers_ids, proj_ids, title')

        add_param(params, 'field', list2str(fields))
        add_param(params, 'maxPers', maxpers)
        if maxitems:
            add_param(params, 'maxRows', maxitems)
        if startitem:
            add_param(params, 'start', startitem)

        # add date params
        if year_from and year_from > 0:
            if year_to and year_to > 0:
                if year_to < year_from:
                    raise ValueError(f"Invalid date range {year_from}-{year_to}")
            else:
                year_to = year_from
            add_param(params, 'yearFrom', year_from)
            add_param(params, 'yearTo', year_to)

        if kwargs:
            params.update(kwargs)

        return self._get(url, params)

    def get_institutions(self, ids: list[int] = None, name: str = None, **kwargs):
        url = self.endpoint + '/institutions'
        params = {}
        add_param(params, 'instId', list2str(ids))
        add_param(params, 'nameSearch', name)
        if not params:
            raise ValueError(
                'Missing parameters! At least one of these parameters is required: '
                'ids, name')
        if kwargs:
            params.update(kwargs)

        return self._get(url, params)


class FreidokFileReader(FreiDokReader):
    """
    Read FreiDok data from file.

    Currently, NO FILTERING is applied, i.e. all data from file will be returned.
    """

    def __init__(self, file: str):
        self.endpoint = file

    def _get(self, url=None, params: dict[str, Any] = None, **kwargs):
        if params or kwargs:
            warnings.warn(
                "Some API filters/parameters cannot be applied to local files")
        with open(self.endpoint) as f:
            return json.load(f)

    def get_institutions(self, *args, **kwargs):
        return self._get(*args, **kwargs)

    def get_publications(self, *args, **kwargs):
        return self._get(*args, **kwargs)
