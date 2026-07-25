import csv
import io

from flask import Blueprint, Response, flash, redirect, render_template, request, url_for

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
    total = HandoverItem.query.count()

    category_counts = (
        db.session.query(HandoverItem.category, db.func.count(HandoverItem.id))
        .group_by(HandoverItem.category)
        .all()
    )
    status_counts = (
        db.session.query(HandoverItem.status, db.func.count(HandoverItem.id))
        .group_by(HandoverItem.status)
        .all()
    )
    department_counts = (
        db.session.query(ItemDepartment.department, db.func.count(ItemDepartment.id))
        .group_by(ItemDepartment.department)
        .all()
    )

    return render_template(
        "admin/dashboard.html",
        total=total,
        category_counts=category_counts,
        status_counts=status_counts,
        department_counts=department_counts,
    )


@bp.route("/fields")
@login_required
def fields():
    all_fields = FieldConfig.query.order_by(FieldConfig.sort_order.asc()).all()
    return render_template(
        "admin/fields.html",
        fields=all_fields,
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
    field = FieldConfig.query.filter_by(field_key=field_key).first_or_404()
    field.is_enabled = not field.is_enabled
    db.session.commit()
    return redirect(url_for("admin.fields"))


@bp.route("/fields/<field_key>/toggle-required", methods=["POST"])
@login_required
def toggle_required(field_key):
    field = FieldConfig.query.filter_by(field_key=field_key).first_or_404()
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


@bp.route("/fields/<field_key>/delete", methods=["POST"])
@login_required
def delete_field(field_key):
    field = FieldConfig.query.filter_by(field_key=field_key).first_or_404()
    if not field.is_custom:
        flash("기본 제공 필드는 삭제할 수 없습니다. 미사용으로 전환해 주세요.")
        return redirect(url_for("admin.fields"))

    FieldOption.query.filter_by(field_key=field_key).delete()
    db.session.delete(field)
    db.session.commit()
    flash(f"'{field.label}' 필드가 삭제되었습니다.")
    return redirect(url_for("admin.fields"))


@bp.route("/fields/<field_key>/options")
@login_required
def options(field_key):
    field = FieldConfig.query.filter_by(field_key=field_key).first_or_404()
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
    items = HandoverItem.query.order_by(HandoverItem.id.asc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "업무명", "카테고리", "관련자(부서)", "업무내용", "주기", "제출기한",
        "이전업무자", "이후업무자", "제출처", "문의처", "관련시스템/URL", "중요도",
        "진행상태", "특이사항", "최근수행일", "등록일", "수정일",
    ])
    for item in items:
        writer.writerow([
            item.id, item.title, item.category or "", ", ".join(item.department_list),
            item.content, item.cycle, item.deadline or "", item.prev_owner, item.next_owner,
            item.submit_to, item.contact or "", item.related_url or "", item.priority or "",
            item.status, item.note or "",
            item.last_done_at.isoformat() if item.last_done_at else "",
            item.created_at.isoformat(), item.updated_at.isoformat(),
        ])

    csv_data = "﻿" + output.getvalue()  # BOM for Excel(한글) 호환
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=handover_export.csv"},
    )
