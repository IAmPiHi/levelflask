from flask import Blueprint, render_template, request, jsonify, session, abort
from db import Database
from utils import admin_required

bp = Blueprint("admin", __name__, url_prefix="/admin")

@bp.route("/", methods=["GET"])
@admin_required
def admin_page():
    return render_template("admin.html")

@bp.route("/users", methods=["GET"])
@admin_required
def get_users():
    db = Database()
    users = db.get_all_users()
    return jsonify([
        {
            "id": user["id"],
            "username": user["username"],
            "level": user["level"],
            "xp": user["xp"]
        } for user in users
    ])

@bp.route("/users/delete", methods=["POST"])
@admin_required
def delete_user():
    user_id = request.form.get("id")
    if not user_id:
        return jsonify({"error": "缺少用戶 ID"}), 400
    db = Database()
    user = db.get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "用戶不存在"}), 404
    if user["username"] == "admin":
        return jsonify({"error": "無法刪除管理員帳號"}), 403
    db.delete_user(user_id)
    return jsonify({"message": "用戶刪除成功"})

@bp.route("/reduce_xp", methods=["POST"])
@admin_required
def reduce_xp():
    user_id = request.form.get("user_id")
    xp_amount = request.form.get("xp")
    try:
        user_id = int(user_id)
        xp_amount = int(xp_amount)
        if xp_amount < 0:
            return jsonify({"error": "XP 值不能為負數"}), 400
    except ValueError:
        return jsonify({"error": "無效的用戶 ID 或 XP 值"}), 400

    db = Database()
    user = db.get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "用戶不存在"}), 404
    if user["username"] == "admin":
        return jsonify({"error": "無法修改管理員的 XP"}), 403

    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT xp, level FROM users WHERE id = ?", (user_id,))
        current = cursor.fetchone()
        if not current:
            return jsonify({"error": "用戶數據不存在"}), 500

        current_xp, current_level = current["xp"], current["level"]
        new_xp = max(0, current_xp - xp_amount)
        new_level = current_level

        # 重新計算等級
        while new_xp < 0 or new_level > 1:
            required_xp = round(100 * (1.03 ** (new_level - 2)))
            if new_xp < required_xp:
                new_level -= 1
                new_xp += required_xp
            else:
                break

        cursor.execute(
            "UPDATE users SET xp = ?, level = ? WHERE id = ?",
            (new_xp, max(1, new_level), user_id)
        )
        conn.commit()

    return jsonify({"message": f"已減少用戶 {user['username']} 的 {xp_amount} XP"})