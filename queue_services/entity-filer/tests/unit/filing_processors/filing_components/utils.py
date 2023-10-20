from attrs import has, fields
from cattrs import Converter
from cattrs.gen import make_dict_unstructure_fn, make_dict_structure_fn, override

converter = Converter()

def to_camel_case(snake_str: str) -> str:
    components = snake_str.split("_")
    return components[0] + "".join(x.title() for x in components[1:])

def to_camel_case_unstructure(cls):
    return make_dict_unstructure_fn(
        cls,
        converter,
        **{
            a.name: override(rename=to_camel_case(a.name))
            for a in fields(cls)
        }
    )

def to_camel_case_structure(cls):
    return make_dict_structure_fn(
        cls,
        converter,
        **{
            a.name: override(rename=to_camel_case(a.name))
            for a in fields(cls)
        }
    )

converter.register_unstructure_hook_factory(
    has, to_camel_case_unstructure
)
converter.register_structure_hook_factory(
    has, to_camel_case_structure
)