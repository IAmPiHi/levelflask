from flask import Blueprint, render_template, request, jsonify, session
from db import Database
from utils import login_required

bp = Blueprint("tasks", __name__)

@bp.route("/system")
@login_required
def task_page():
    return render_template("2.html", username=session["username"])

@bp.route("/api/categories")
@login_required
def get_categories():
    db = Database()
    categories = db.get_all_user_tasks(session["username"])
    result = []
    current_cat = None
    for row in categories:
        cat_id, cat_name, task_id, task_name, xp, daily_completion_limit = row
        if not current_cat or current_cat["id"] != cat_id:
            if current_cat:
                result.append(current_cat)
            current_cat = {"id": cat_id, "name": cat_name, "tasks": []}
        if task_id:
            current_daily_completions = db.get_daily_xp(session["username"], task_id)
            current_cat["tasks"].append({
                "id": task_id,
                "name": task_name,
                "xp": xp,
                "daily_completion_limit": daily_completion_limit,
                "current_daily_completions": current_daily_completions
            })
    if current_cat:
        result.append(current_cat)
    return jsonify(result)

@bp.route("/api/add_category", methods=["POST"])
@login_required
def add_category():
    name = request.form.get("name", "").strip()
    if not name:
        return jsonify({"error": "分類名稱不能為空"}), 400
    db = Database()
    category_id = db.add_category(session["username"], name)
    if category_id:
        return jsonify({"id": category_id, "name": name})
    return jsonify({"error": "分類已存在"}), 400

@bp.route("/api/delete_category", methods=["POST"])
@login_required
def delete_category():
    category_id = request.form.get("id")
    try:
        category_id = int(category_id)
    except ValueError:
        return jsonify({"error": "無效的分類 ID"}), 400
    db = Database()
    if db.delete_category(session["username"], category_id):
        return jsonify({"message": "分類刪除成功"})
    return jsonify({"error": "無法刪除分類"}), 400

@bp.route("/api/add_task", methods=["POST"])
@login_required
def add_task():
    category_id = request.form.get("category_id")
    name = request.form.get("name", "").strip()
    xp = request.form.get("xp")
    daily_completion_limit = request.form.get("daily_completion_limit")
    try:
        category_id = int(category_id)
        xp = int(xp)
        daily_completion_limit = int(daily_completion_limit)
        if xp <= 0 or xp > 100 or daily_completion_limit <= 0:
            return jsonify({"error": "無效的 XP 或次數上限值"}), 400
    except ValueError:
        return jsonify({"error": "參數必須為數字"}), 400
    if not name:
        return jsonify({"error": "任務名稱不能為空"}), 400
    db = Database()
    task_id = db.add_task(category_id, name, xp, daily_completion_limit)
    return jsonify({
        "id": task_id,
        "name": name,
        "xp": xp,
        "daily_completion_limit": daily_completion_limit
    })

@bp.route("/api/delete_task", methods=["POST"])
@login_required
def delete_task():
    task_id = request.form.get("id")
    try:
        task_id = int(task_id)
    except ValueError:
        return jsonify({"error": "無效的任務 ID"}), 400
    db = Database()
    if db.delete_task(task_id):
        return jsonify({"message": "任務刪除成功"})
    return jsonify({"error": "無法刪除任務"}), 400

@bp.route("/add_xp", methods=["POST"])
@login_required
def add_xp():
    task_id = request.form.get("task_id")
    try:
        task_id = int(task_id)
    except ValueError:
        return jsonify({"error": "無效的任務 ID"}), 400
    db = Database()
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT xp, daily_completion_limit FROM tasks WHERE id = ?", (task_id,))
        task = cursor.fetchone()
        if not task:
            return jsonify({"error": "任務不存在"}), 400
        xp, daily_completion_limit = task
        current_daily_completions = db.get_daily_xp(session["username"], task_id)
        if current_daily_completions >= daily_completion_limit:
            return jsonify({"error": "已達今日完成次數上限"}), 400
        if db.update_user_xp(session["username"], xp):
            db.record_task_completion(session["username"], task_id, xp)
            user_xp_level = db.get_user_xp_level(session["username"])
            if user_xp_level is None:
                return jsonify({"error": "用戶數據不存在"}), 500
            return jsonify({"xp": user_xp_level["xp"], "level": user_xp_level["level"]})
        return jsonify({"error": "無法更新 XP"}), 400

@bp.route("/get_xp_level")
@login_required
def get_xp_level():
    db = Database()
    user_xp_level = db.get_user_xp_level(session["username"])
    if user_xp_level is None:
        return jsonify({"error": "用戶數據不存在"}), 500
    return jsonify({"xp": user_xp_level["xp"], "level": user_xp_level["level"]})