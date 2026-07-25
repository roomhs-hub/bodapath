from .extensions import db
from .models import FieldConfig, FieldOption


def get_all_fields(enabled_only=True):
    query = FieldConfig.query.order_by(FieldConfig.sort_order.asc())
    if enabled_only:
        query = query.filter_by(is_enabled=True)
    return query.all()


def get_field(field_key):
    return FieldConfig.query.filter_by(field_key=field_key).first()


def get_options(field_key):
    return (
        FieldOption.query.filter_by(field_key=field_key)
        .order_by(FieldOption.sort_order.asc())
        .all()
    )


def get_options_map(field_keys):
    """여러 select/multiselect 필드의 옵션을 한 번에 dict로 반환."""
    result = {}
    for key in field_keys:
        result[key] = [o.value for o in get_options(key)]
    return result


BUILTIN_TEXT_SEARCH_FIELDS = ["title", "content", "note", "contact"]


def searchable_custom_field_keys():
    """관리자가 추가한 커스텀 필드 중 검색 대상이 되는 텍스트형 필드 키 목록."""
    return [
        f.field_key
        for f in FieldConfig.query.filter_by(is_custom=True, is_enabled=True).all()
        if f.field_type in ("text", "textarea")
    ]
