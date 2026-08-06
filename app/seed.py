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

# ensure_default_fields()가 이미 필드 순서가 운영자에 의해 커스터마이즈된(드래그앤드롭으로
# sort_order가 DEFAULT_FIELDS의 고정값과 달라진) DB에 새 기본 필드를 추가할 때, 위 목록의
# 고정 sort_order 대신 "이 필드 바로 다음에 배치" 기준으로 현재 순서에 맞춰 동적으로 위치를
# 계산하도록 하는 힌트. (예: 성공적으로 배포된 뒤에도 운영 DB의 필드 순서가 이미 바뀌어 있어
# 고정 sort_order=135를 그대로 썼더니 "인수인계 진행 상태" 근처가 아닌 엉뚱한 위치에 필드가
# 삽입된 적이 있어, 이를 방지하기 위해 도입했다.)
INSERT_AFTER = {
    "successor": "status",
}

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

        insert_sort_order = sort_order
        anchor_key = INSERT_AFTER.get(field_key)
        if anchor_key:
            anchor = FieldConfig.query.filter_by(field_key=anchor_key).first()
            if anchor is not None:
                # 앵커 필드의 "현재" sort_order를 기준으로, 그 바로 다음 필드와의 사이에 끼워
                # 넣는다. DEFAULT_FIELDS의 고정 숫자를 쓰지 않으므로 운영자가 필드 순서를
                # 드래그앤드롭으로 바꿔 놓았어도 항상 앵커 필드 바로 다음에 배치된다.
                next_field = (
                    FieldConfig.query.filter(FieldConfig.sort_order > anchor.sort_order)
                    .order_by(FieldConfig.sort_order.asc())
                    .first()
                )
                if next_field is not None and next_field.sort_order > anchor.sort_order + 1:
                    insert_sort_order = (anchor.sort_order + next_field.sort_order) // 2
                else:
                    insert_sort_order = anchor.sort_order + 1

        db.session.add(
            FieldConfig(
                field_key=field_key,
                label=label,
                field_type=field_type,
                is_required=is_required,
                is_enabled=True,
                is_custom=False,
                sort_order=insert_sort_order,
            )
        )
        added = True

    if added:
        db.session.commit()
    return added
