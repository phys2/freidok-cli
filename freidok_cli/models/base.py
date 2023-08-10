import pydantic


class BaseModel(pydantic.BaseModel):
    @pydantic.validator('*', pre=True)
    def empty_str_to_none(cls, v):
        # if isinstance(v, str) and v == '':
        #     return None
        return v
