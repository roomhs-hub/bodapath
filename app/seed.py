from .extensions import db
from .models import FieldConfig, FieldOption

# (field_key, label, field_type, is_required, sort_order)
DEFAULT_FIELDS = [
    ("title", "업무명(제목)", "text", True, 10),
    ("category", "카테고리/구분", "select", True, 20),
    ("department", "관련자(부서)", "multiselect", True, 30),
    ("content", "업무내용(상세설명)", "textarea", True, 40),
    ("cycle", "주기", "select", True, 50),
    ("deadline", "제출·처리 기한", "text", False, 60),
    ("prev_owner", "이전 업무자", "text", True, 70),
    ("next_owner", "이후 업무자", "text", True, 80),
    ("submit_to", "제출처 / 보고 대상", "text", True, 90),
    ("contact", "문의처", "text", False, 100),
    ("related_url", "관련 시스템/URL", "text", False, 110),
    ("priority", "중요도", "select", False, 120),
    ("status", "인수인계 진행 상태", "select", True, 130),
    ("successor", "인수자", "multiselect", False, 135),
    ("note", "특이사항/주의사항", "textarea", False, 140),
    ("last_done_at", "최근 수행일", "date", False, 150),
]

# (field_key, [values in order])
DEFAULT_OPTIONS = {
    "category": ["정기보고", "시스템운영", "대외협력", "예산/정산", "기타"],
    "department": ["본사", "지사", "가맹점", "기타거래처"],
    "cycle": ["매일", "매주", "매월", "매분기", "매년", "수시", "1회성"],
    "priority": ["상", "중", "하"],
    "status": ["미확인", "확인중", "완료"],
}


def seed_defaults():
    """기본 필드/선택항목이 비어있을 때만 생성한다 (idempotent)."""
    if FieldConfig.query.first() is not None:
        return False

    for field_key, label, field_type, is_required, sort_order in DEFAULT_FIELDS:
        db.session.add(
            FieldConfig(
                field_key=field_key,
                label=label,
                field_type=field_type,
                is_required=is_required,
                is_enabled=True,
                is_custom=False,
                sort_order=sort_order,
            )
        )

    for field_key, values in DEFAULT_OPTIONS.items():
        for i, value in enumerate(values):
            db.session.add(
                FieldOption(field_key=field_key, value=value, sort_order=i * 10)
            )

    db.session.commit()
    return True


def ensure_default_fields():
    """이미 운영 중인(필드가 이미 채워진) DB에도, 이후 세션에서 DEFAULT_FIELDS에
    새로 추가된 기본 필드가 있으면 누락분만 추가한다 (idempotent).
    완전 신규 설치는 seed_defaults()가 DEFAULT_FIELDS 전체를 이미 생성하므로 건너뛴다."""
    if FieldConfig.query.first() is None:
        return False

    existing_keys = {row[0] for row in db.session.query(FieldConfig.field_key).all()}
    added = False

    for field_key, label, field_type, is_required, sort_order in DEFAULT_FIELDS:
        if field_key in existing_keys:
            continue
        db.session.add(
            FieldConfig(
                field_key=field_key,
                label=label,
                field_type=field_type,
                is_required=is_required,
                is_enabled=True,
                is_custom=False,
                sort_order=sort_order,
            )
        )
        added = True

    if added:
        db.session.commit()
    return added
