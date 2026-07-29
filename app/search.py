from flask import Blueprint, render_template, request

from .auth import login_required
from .fields import BUILTIN_TEXT_SEARCH_FIELDS, get_options, searchable_custom_field_keys
from .models import CustomFieldValue, HandoverItem, ItemDepartment
from .extensions import db

bp = Blueprint("search", __name__)


@bp.route("/search")
@login_required
def search():
    keyword = request.args.get("q", "").strip()
    category = request.args.getlist("category")
    cycle = request.args.getlist("cycle")
    priority = request.args.getlist("priority")
    status = request.args.getlist("status")
    next_owner = request.args.get("next_owner", "").strip()
    departments = request.args.getlist("department")

    query = HandoverItem.query.filter(HandoverItem.is_deleted.is_(False))

    if keyword:
        like = f"%{keyword}%"
        conditions = [getattr(HandoverItem, f).ilike(like) for f in BUILTIN_TEXT_SEARCH_FIELDS]

        custom_keys = searchable_custom_field_keys()
        matching_item_ids = []
        if custom_keys:
            matching_item_ids = [
                row.item_id
                for row in CustomFieldValue.query.filter(
                    CustomFieldValue.field_key.in_(custom_keys),
                    CustomFieldValue.value.ilike(like),
                ).all()
            ]

        from sqlalchemy import or_

        clause = or_(*conditions)
        if matching_item_ids:
            clause = or_(clause, HandoverItem.id.in_(matching_item_ids))
        query = query.filter(clause)

    if category:
        query = query.filter(HandoverItem.category.in_(category))
    if cycle:
        query = query.filter(HandoverItem.cycle.in_(cycle))
    if priority:
        query = query.filter(HandoverItem.priority.in_(priority))
    if status:
        query = query.filter(HandoverItem.status.in_(status))
    if next_owner:
        query = query.filter(HandoverItem.next_owner.ilike(f"%{next_owner}%"))
    if departments:
        query = query.join(ItemDepartment).filter(ItemDepartment.department.in_(departments))

    query = query.order_by(HandoverItem.updated_at.desc())
    results = query.all() if (keyword or category or cycle or priority or status or next_owner or departments) else []

    return render_template(
        "search.html",
        keyword=keyword,
        results=results,
        category_options=get_options("category"),
        cycle_options=get_options("cycle"),
        priority_options=get_options("priority"),
        status_options=get_options("status"),
        department_options=get_options("department"),
        selected_category=category,
        selected_cycle=cycle,
        selected_priority=priority,
        selected_status=status,
        selected_departments=departments,
        next_owner=next_owner,
        searched=bool(request.args),
    )
