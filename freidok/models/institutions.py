"""
Manually generated model classes for freidok API responses of type "institution".
"""
from typing import Annotated, Any, Optional

from pydantic import BaseModel, Extra, Field


class Lifetime(BaseModel):
    """
    Entry for a lifetime
    """

    class Config:
        extra = Extra.allow

    from_: Annotated[
        Optional[str],
        Field(alias='global')
    ] = None
    until: Optional[str] = None
    value: Optional[str] = None


class Director(BaseModel):
    """
    Entry for a director
    """

    class Config:
        extra = Extra.allow

    link: Optional[str] = None
    value: Optional[str] = None
    forename: Optional[str] = None
    surname: Optional[str] = None
    time_active: Optional[str] = None


class Name(BaseModel):
    """
    Entry for a institution name
    """

    class Config:
        extra = Extra.allow

    language: Optional[str] = None
    """
    attribute-id of the language
    """
    language_value: Optional[str] = None
    """
    language-dependend description of the language
    """
    value: Optional[str] = None
    """
    the keyword
    """


class Doc(BaseModel):
    """
    Entry for a single publication.
    """

    class Config:
        extra = Extra.allow

    id: Optional[int] = None

    link: Optional[str] = None

    names: Optional[list[Name]] = None

    directors: Optional[list[Director]] = None

    lifetime: Optional[Lifetime] = None


class Institutions(BaseModel):
    """
    Schema for the JSON-Output of a List of publications by the API-v1 of FreiDok plus
    """

    class Config:
        extra = Extra.allow

    numFound: Annotated[Optional[int], Field(ge=0)] = None
    """
    Number of searchresults for the given request.
    """
    start: Annotated[Optional[int], Field(ge=0)] = 0
    """
    Offset for the result-list.
    """
    maxRows: Annotated[Optional[int], Field(ge=0, le=100)] = 25
    """
    Maximum number of results per request.
    """
    type: str = "institution"
    """
    Describes the type of this JSON-object
    """
    docs: Optional[list[Doc]] = None
    """
    List of found publications.
    """
