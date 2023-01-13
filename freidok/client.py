import json
from typing import Any

import requests
from requests.utils import get_encoding_from_headers

from freidok.utils import list2str


def create_headers(user_agent, user_email=None, extra_headers=None):
    headers = {
        'User-Agent': user_agent
    }

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


class FreidokClient:
    def __init__(self, base_url: str, user_agent: str, user_email=None,
                 extra_headers: dict[str, str] = None, default_max_rows: int = 0,
                 dryrun=False):
        if not base_url:
            raise ValueError("Invalid Freidok API URL")

        self.base_url = base_url.rstrip('/')
        self.default_max_rows = default_max_rows
        self.headers = create_headers(user_agent, user_email, extra_headers)
        self.timeout = 30
        self.dryrun = dryrun

    def _print_prep_request(self, req, encoding=None):
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
        # set default max_rows
        if params and self.default_max_rows:
            params.setdefault('maxRows', self.default_max_rows)

        if self.dryrun:
            r = requests.Request('GET', url=url, headers=self.headers, params=params)
            self._print_prep_request(r.prepare())
            exit()

        r = requests.get(url, headers=self.headers, params=params,
                         timeout=self.timeout)
        r.raise_for_status()
        return r

    def get_publications(
            self,
            ids: list[int] = None,
            inst_ids: list[int] = None,
            pers_ids: list[int] = None,
            title: str = None,
            year_from: int = 0,
            year_to: int = 0,
            fields: list[str] = None,
            maxpers: int = None,
            **kwargs):

        url = self.base_url + '/publications'
        params = {}
        add_param(params, 'publicationId', list2str(ids))
        add_param(params, 'instId', list2str(inst_ids))
        add_param(params, 'persId', list2str(pers_ids))
        add_param(params, 'titleSearch', title)
        add_param(params, 'field', list2str(fields))
        add_param(params, 'maxPers', maxpers)

        # years
        if year_from > 0:
            if year_to > 0:
                if year_to < year_from:
                    raise ValueError(f"Invalid date range {year_from}-{year_to}")
            else:
                year_to = year_from
            add_param(params, 'yearFrom', year_from)
            add_param(params, 'yearTo', year_to)

        if not params:
            raise ValueError(
                'Missing parameters! At least one of these parameters is required: '
                'ids, inst_ids, title')
        if kwargs:
            params.update(kwargs)
        r = self._get(url, params)
        return r.json()

    def get_institutions(self, ids: list[int] = None, name: str = None, **kwargs):
        url = self.base_url + '/institutions'
        params = {}
        add_param(params, 'instId', list2str(ids))
        add_param(params, 'nameSearch', name)
        if not params:
            raise ValueError(
                'Missing parameters! At least one of these parameters is required: '
                'ids, name')
        if kwargs:
            params.update(kwargs)
        r = self._get(url, params)
        return r.json()


class DummyRequest:
    def __init__(self, data):
        self.data = data

    def json(self):
        return self.data


class FreidokMockClient(FreidokClient):

    def _get(self, url, params: dict[str, Any] = None):
        with open('response_fieldset_full.json') as f:
            data = json.load(f)
            return DummyRequest(data)
