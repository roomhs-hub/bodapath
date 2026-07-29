import csv
import io

from flask import Blueprint, Response, flash, jsonify, redirect, render_template, request, url_for

from .auth import login_required
from .extensions import db
from .models import FieldConfig, FieldOption, HandoverItem, ItemDepartment

bp = Blueprint("admin", __name__, url_prefix="/admin")

FIELD_TYPES = [
    ("text", "텍스트"),
    ("textarea", "긴 텍스트"),
    ("date", "날짜"),
    ("select", "드롭다운(단일선택)"),
    ("multiselect", "다중선택"),
]


@bp.route("/")
@login_required
def dashboard():
    active = HandoverItem.query.filter(HandoverItem.is_deleted.is_(False))
    total = active.count()
    deleted_total = HandoverItem.query.filter(HandoverItem.is_deleted.is_(True)).count()

    category_counts = (
        db.session.query(HandoverItem.category, db.func.count(HandoverItem.id))
        .filter(HandoverItem.is_deleted.is_(False))
        .group_by(HandoverItem.category)
        .all()
    )
    status_counts = (
        db.session.query(HandoverItem.status, db.func.count(HandoverItem.id))
        .filter(HandoverItem.is_deleted.is_(False))
        .group_by(HandoverItem.status)
        .all()
    )
    department_counts = (
        db.session.query(ItemDepartment.department, db.func.count(ItemDepartment.id))
        .join(HandoverItem, ItemDepartment.item_id == HandoverItem.id)
        .filter(HandoverItem.is_deleted.is_(False))
        .group_by(ItemDepartment.department)
        .all()
    )

    return render_template(
        "admin/dashboard.html",
        total=total,
        deleted_total=deleted_total,
        category_counts=category_counts,
        status_counts=status_counts,
        department_counts=department_counts,
    )


@bp.route("/fields")
@login_required
def fields():
    all_fields = (
        FieldConfig.query.filter_by(is_deleted=False)
        .order_by(FieldConfig.sort_order.asc())
        .all()
    )
    deleted_fields = (
        FieldConfig.query.filter_by(is_deleted=True).order_by(FieldConfig.label.asc()).all()
    )
    return render_template(
        "admin/fields.html",
        fields=all_fields,
        deleted_fields=deleted_fields,
        field_types=FIELD_TYPES,
        field_type_labels=dict(FIELD_TYPES),
    )


@bp.route("/fields/new", methods=["POST"])
@login_required
def new_field():
    label = request.form.get("label", "").strip()
    field_type = request.form.get("field_type", "text")
    is_required = bool(request.form.get("is_required"))
    options_raw = request.form.get("options", "").strip()

    if not label:
        flash("필드명을 입력해 주세요.")
        return redirect(url_for("admin.fields"))

    existing_keys = {f.field_key for f in FieldConfig.query.all()}
    n = 1
    while f"custom_{n}" in existing_keys:
        n += 1
    field_key = f"custom_{n}"

    max_sort = db.session.query(db.func.max(FieldConfig.sort_order)).scalar() or 0

    field = FieldConfig(
        field_key=field_key,
        label=label,
        field_type=field_type,
        is_required=is_required,
        is_enabled=True,
        is_custom=True,
        sort_order=max_sort + 10,
    )
    db.session.add(field)

    if field_type in ("select", "multiselect") and options_raw:
        values = [v.strip() for v in options_raw.split(",") if v.strip()]
        for i, value in enumerate(values):
            db.session.add(FieldOption(field_key=field_key, value=value, sort_order=i * 10))

    db.session.commit()
    flash(f"'{label}' 필드가 추가되었습니다.")
    return redirect(url_for("admin.fields"))


@bp.route("/fields/<field_key>/toggle-enabled", methods=["POST"])
@login_required
def toggle_enabled(field_key):
    field = FieldConfig.query.filter_by(field_key=field_key, is_deleted=False).first_or_404()
    field.is_enabled = not field.is_enabled
    db.session.commit()
    return redirect(url_for("admin.fields"))


@bp.route("/fields/<field_key>/toggle-required", methods=["POST"])
@login_required
def toggle_required(field_key):
    field = FieldConfig.query.filter_by(field_key=field_key, is_deleted=False).first_or_404()
    field.is_required = not field.is_required
    db.session.commit()
    return redirect(url_for("admin.fields"))


@bp.route("/fields/<field_key>/move/<direction>", methods=["POST"])
@login_required
def move_field(field_key, direction):
    all_fields = FieldConfig.query.order_by(FieldConfig.sort_order.asc()).all()
    idx = next((i for i, f in enumerate(all_fields) if f.field_key == field_key), None)
    if idx is None:
        return redirect(url_for("admin.fields"))

    swap_idx = idx - 1 if direction == "up" else idx + 1
    if 0 <= swap_idx < len(all_fields):
        a, b = all_fields[idx], all_fields[swap_idx]
        a.sort_order, b.sort_order = b.sort_order, a.sort_order
        db.session.commit()

    return redirect(url_for("admin.fields"))


@bp.route("/fields/reorder", methods=["POST"])
@login_required
def reorder_fields():
    """드래그로 재배열한 필드 순서를 한 번에 저장한다. (노션 스타일 드래그앤드롭)"""
    payload = request.get_json(silent=True) or {}
    order = payload.get("order") or request.form.getlist("order[]")
    if not order:
        return jsonify({"ok": False, "error": "순서 정보가 없습니다."}), 400

    fields_by_key = {f.field_key: f for f in FieldConfig.query.filter_by(is_deleted=False).all()}
    for i, field_key in enumerate(order):
        field = fields_by_key.get(field_key)
        if field:
            field.sort_order = (i + 1) * 10
    db.session.commit()
    return jsonify({"ok": True})


@bp.route("/fields/<field_key>/delete", methods=["POST"])
@login_required
def delete_field(field_key):
    """실제로 필드(및 선택항목·기존 입력값)를 지우지 않고 is_deleted 플래그만 세운다.
    같은 필드관리 화면 하단의 필터에서 검색해 다시 사용(복구)할 수 있다."""
    field = FieldConfig.query.filter_by(field_key=field_key, is_deleted=False).first_or_404()
    if not field.is_custom:
        flash("기본 제공 필드는 삭제할 수 없습니다. 미사용으로 전환해 주세요.")
        return redirect(url_for("admin.fields"))

    field.is_deleted = True
    field.is_enabled = False  # 목록/입력 화면에 더는 노출되지 않도록 사용도 함께 해제
    db.session.commit()
    flash(f"'{field.label}' 필드를 삭제했습니다. (아래 '삭제된 필드' 필터에서 검색해 다시 사용할 수 있습니다)")
    return redirect(url_for("admin.fields"))


@bp.route("/fields/<field_key>/restore", methods=["POST"])
@login_required
def restore_field(field_key):
    field = FieldConfig.query.filter_by(field_key=field_key, is_deleted=True).first_or_404()
    field.is_deleted = False
    db.session.commit()
    flash(f"'{field.label}' 필드를 복구했습니다. 목록에서 '사용' 여부를 확인해 주세요.")
    return redirect(url_for("admin.fields"))


@bp.route("/fields/<field_key>/options")
@login_required
def options(field_key):
    field = FieldConfig.query.filter_by(field_key=field_key, is_deleted=False).first_or_404()
    opts = FieldOption.query.filter_by(field_key=field_key).order_by(FieldOption.sort_order).all()
    return render_template("admin/options.html", field=field, options=opts)


@bp.route("/fields/<field_key>/options/new", methods=["POST"])
@login_required
def new_option(field_key):
    value = request.form.get("value", "").strip()
    if value:
        max_sort = (
            db.session.query(db.func.max(FieldOption.sort_order))
            .filter(FieldOption.field_key == field_key)
            .scalar()
            or 0
        )
        db.session.add(FieldOption(field_key=field_key, value=value, sort_order=max_sort + 10))
        db.session.commit()
    return redirect(url_for("admin.options", field_key=field_key))


@bp.route("/fields/<field_key>/options/<int:option_id>/update", methods=["POST"])
@login_required
def update_option(field_key, option_id):
    opt = FieldOption.query.get_or_404(option_id)
    value = request.form.get("value", "").strip()
    if not value:
        flash("항목명은 비워둘 수 없습니다.")
        return redirect(url_for("admin.options", field_key=field_key))
    opt.value = value
    db.session.commit()
    flash("변경되었습니다.")
    return redirect(url_for("admin.options", field_key=field_key))


@bp.route("/fields/<field_key>/options/<int:option_id>/delete", methods=["POST"])
@login_required
def delete_option(field_key, option_id):
    opt = FieldOption.query.get_or_404(option_id)
    db.session.delete(opt)
    db.session.commit()
    return redirect(url_for("admin.options", field_key=field_key))


@bp.route("/export.csv")
@login_required
def export_csv():
    # 백업 목적이므로 삭제(플래그) 항목도 포함해서 전체를 내보내되, 구분할 수 있도록 컬럼을 추가한다.
    items = HandoverItem.query.order_by(HandoverItem.id.asc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "업무명", "카테고리", "관련자(부서)", "업무내용", "주기", "제출기한",
        "이전업무자", "이후업무자", "제출처", "문의처", "관련시스템/URL", "중요도",
        "진행상태", "특이사항", "최근수행일", "등록일", "수정일", "삭제여부",
    ])
    for item in items:
        writer.writerow([
            item.id, item.title, item.category or "", ", ".join(item.department_list),
            item.content, item.cycle, item.deadline or "", item.prev_owner, item.next_owner,
            item.submit_to, item.contact or "", item.related_url or "", item.priority or "",
            item.status, item.note or "",
            item.last_done_at.isoformat() if item.last_done_at else "",
            item.created_at.isoformat(), item.updated_at.isoformat(),
            "삭제됨" if item.is_deleted else "",
        ])

    csv_data = "﻿" + output.getvalue()  # BOM for Excel(한글) 호환
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=handover_export.csv"},
    )


@bp.route("/deleted-items")
@login_required
def deleted_items():
    items = (
        HandoverItem.query.filter(HandoverItem.is_deleted.is_(True))
        .order_by(HandoverItem.updated_at.desc())
        .all()
    )
    return render_template("admin/deleted_items.html", items=items)


@bp.route("/deleted-items/<int:item_id>/restore", methods=["POST"])
@login_required
def restore_item(item_id):
    item = HandoverItem.query.filter_by(id=item_id, is_deleted=True).first_or_404()
    item.is_deleted = False
    db.session.commit()
    flash(f"'{item.title}' 항목을 복구했습니다.")
    return redirect(url_for("admin.deleted_items"))
