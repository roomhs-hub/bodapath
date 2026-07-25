from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from .auth import login_required
from .extensions import db
from .fields import get_all_fields, get_options
from .models import CustomFieldValue, FieldConfig, HandoverItem, ItemDepartment

bp = Blueprint("items", __name__)

SELECT_FIELD_KEYS = {"category", "cycle", "priority", "status"}


def _fields_for_form():
    """폼에 노출할 필드 목록(사용 설정된 필드만, 순서대로)."""
    return get_all_fields(enabled_only=True)


def _apply_builtin_field(item, field_key, value):
    if field_key == "last_done_at":
        item.last_done_at = datetime.strptime(value, "%Y-%m-%d").date() if value else None
    else:
        setattr(item, field_key, value or None)


BUILTIN_KEYS = {
    "title", "category", "content", "cycle", "deadline", "prev_owner", "next_owner",
    "submit_to", "contact", "related_url", "priority", "status", "note", "last_done_at",
}


def _save_item_from_form(item, fields):
    for f in fields:
        key = f.field_key
        if key == "department":
            selected = request.form.getlist("department")
            item.departments = [ItemDepartment(department=d) for d in selected]
            continue

        if f.field_type == "multiselect":
            selected = request.form.getlist(key)
            value = ",".join(selected)
        else:
            value = request.form.get(key, "").strip()

        if key in BUILTIN_KEYS:
            _apply_builtin_field(item, key, value)
        elif f.is_custom:
            existing = next((c for c in item.custom_values if c.field_key == key), None)
            if existing:
                existing.value = value
            else:
                item.custom_values.append(CustomFieldValue(field_key=key, value=value))


def _validate_required(fields):
    errors = []
    for f in fields:
        if not f.is_required:
            continue
        if f.field_key == "department":
            if not request.form.getlist("department"):
                errors.append(f"{f.label}은(는) 필수 항목입니다.")
            continue
        if f.field_type == "multiselect":
            if not request.form.getlist(f.field_key):
                errors.append(f"{f.label}은(는) 필수 항목입니다.")
            continue
        if not request.form.get(f.field_key, "").strip():
            errors.append(f"{f.label}은(는) 필수 항목입니다.")
    return errors


def _custom_values_map(item):
    return {c.field_key: c.value for c in item.custom_values}


def _multiselect_keys(fields):
    return ["department"] + [f.field_key for f in fields if f.field_type == "multiselect"]


def _multiselect_from_form(fields):
    return {key: request.form.getlist(key) for key in _multiselect_keys(fields)}


def _multiselect_from_item(item, fields):
    result = {"department": item.department_list}
    custom_values = _custom_values_map(item)
    for f in fields:
        if f.field_type == "multiselect" and f.field_key != "department":
            raw = custom_values.get(f.field_key, "")
            result[f.field_key] = raw.split(",") if raw else []
    return result


@bp.route("/")
@login_required
def index():
    return redirect(url_for("items.list_items"))


@bp.route("/items")
@login_required
def list_items():
    fields = _fields_for_form()
    query = HandoverItem.query

    category = request.args.get("category") or ""
    status = request.args.get("status") or ""
    departments = request.args.getlist("department")

    if category:
        query = query.filter(HandoverItem.category == category)
    if status:
        query = query.filter(HandoverItem.status == status)
    if departments:
        query = query.join(ItemDepartment).filter(ItemDepartment.department.in_(departments))

    query = query.order_by(HandoverItem.updated_at.desc())

    page = request.args.get("page", 1, type=int)
    per_page = 20
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        "list.html",
        fields=fields,
        items=pagination.items,
        pagination=pagination,
        category_options=get_options("category"),
        status_options=get_options("status"),
        department_options=get_options("department"),
        selected_category=category,
        selected_status=status,
        selected_departments=departments,
    )


@bp.route("/items/new", methods=["GET", "POST"])
@login_required
def new_item():
    fields = _fields_for_form()

    if request.method == "POST":
        errors = _validate_required(fields)
        if errors:
            for e in errors:
                flash(e)
            return render_template(
                "item_form.html", fields=fields, item=None, mode="new",
                form_values=request.form, multiselect_values=_multiselect_from_form(fields),
            )

        item = HandoverItem(status="미확인")
        _save_item_from_form(item, fields)
        db.session.add(item)
        db.session.commit()

        if item.prev_owner:
            session["default_prev_owner"] = item.prev_owner

        flash("등록되었습니다.")
        return redirect(url_for("items.list_items"))

    default_values = {"prev_owner": session.get("default_prev_owner", "")}
    return render_template(
        "item_form.html", fields=fields, item=None, mode="new",
        form_values=default_values, multiselect_values={},
    )


@bp.route("/items/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
def edit_item(item_id):
    item = HandoverItem.query.get_or_404(item_id)
    fields = _fields_for_form()

    if request.method == "POST":
        errors = _validate_required(fields)
        if errors:
            for e in errors:
                flash(e)
            return render_template(
                "item_form.html", fields=fields, item=item, mode="edit",
                form_values=request.form, multiselect_values=_multiselect_from_form(fields),
            )

        _save_item_from_form(item, fields)
        db.session.commit()
        flash("수정되었습니다.")
        return redirect(url_for("items.list_items"))

    form_values = {f.name: getattr(item, f.name, "") for f in HandoverItem.__table__.columns}
    if item.last_done_at:
        form_values["last_done_at"] = item.last_done_at.strftime("%Y-%m-%d")
    form_values.update(_custom_values_map(item))

    return render_template(
        "item_form.html", fields=fields, item=item, mode="edit",
        form_values=form_values, multiselect_values=_multiselect_from_item(item, fields),
    )


@bp.route("/items/<int:item_id>/delete", methods=["POST"])
@login_required
def delete_item(item_id):
    item = HandoverItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash("삭제되었습니다.")
    return redirect(url_for("items.list_items"))
