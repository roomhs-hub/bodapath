from datetime import datetime, date

from .extensions import db


class FieldConfig(db.Model):
    """필드 정의 (기본 필드 + 관리자가 추가한 커스텀 필드 모두 등록)"""

    __tablename__ = "field_config"

    id = db.Column(db.Integer, primary_key=True)
    field_key = db.Column(db.String(64), nullable=False, unique=True)
    label = db.Column(db.String(128), nullable=False)
    # text / textarea / date / select / multiselect
    field_type = db.Column(db.String(32), nullable=False)
    is_required = db.Column(db.Boolean, nullable=False, default=False)
    is_enabled = db.Column(db.Boolean, nullable=False, default=True)
    is_custom = db.Column(db.Boolean, nullable=False, default=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    options = db.relationship(
        "FieldOption",
        backref="field",
        primaryjoin="FieldConfig.field_key==foreign(FieldOption.field_key)",
        order_by="FieldOption.sort_order",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<FieldConfig {self.field_key}>"


class FieldOption(db.Model):
    """select / multiselect 타입 필드의 선택항목"""

    __tablename__ = "field_option"

    id = db.Column(db.Integer, primary_key=True)
    field_key = db.Column(
        db.String(64), db.ForeignKey("field_config.field_key"), nullable=False
    )
    value = db.Column(db.String(128), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)


class HandoverItem(db.Model):
    """업무 인수인계 항목 (기본 제공 필드는 실제 컬럼으로 저장)"""

    __tablename__ = "handover_item"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(128))
    content = db.Column(db.Text, nullable=False)
    cycle = db.Column(db.String(32), nullable=False)
    deadline = db.Column(db.String(255))
    prev_owner = db.Column(db.String(128), nullable=False)
    next_owner = db.Column(db.String(128), nullable=False)
    submit_to = db.Column(db.String(255), nullable=False)
    contact = db.Column(db.String(255))
    related_url = db.Column(db.String(512))
    priority = db.Column(db.String(16))
    status = db.Column(db.String(32), nullable=False, default="미확인")
    note = db.Column(db.Text)
    last_done_at = db.Column(db.Date)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    departments = db.relationship(
        "ItemDepartment", backref="item", cascade="all, delete-orphan"
    )
    custom_values = db.relationship(
        "CustomFieldValue", backref="item", cascade="all, delete-orphan"
    )

    @property
    def department_list(self):
        return [d.department for d in self.departments]


class ItemDepartment(db.Model):
    """관련자(부서): 다중 선택이므로 항목 1개당 여러 행이 생길 수 있음"""

    __tablename__ = "item_department"

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(
        db.Integer, db.ForeignKey("handover_item.id", ondelete="CASCADE"), nullable=False
    )
    department = db.Column(db.String(64), nullable=False)


class CustomFieldValue(db.Model):
    """관리자가 나중에 추가한 커스텀 필드의 값"""

    __tablename__ = "custom_field_value"

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(
        db.Integer, db.ForeignKey("handover_item.id", ondelete="CASCADE"), nullable=False
    )
    field_key = db.Column(
        db.String(64), db.ForeignKey("field_config.field_key"), nullable=False
    )
    value = db.Column(db.Text)
