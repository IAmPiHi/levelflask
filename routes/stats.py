from flask import Blueprint, render_template, jsonify, session
from db import Database
from utils import login_required

bp = Blueprint("stats", __name__)

@bp.route("/stats")
@login_required
def stats_page():
    return render_template("stats.html", username=session["username"])

@bp.route("/api/stats")
@login_required
def get_stats():
    db = Database()
    username = session["username"]
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT SUM(xp_earned)
            FROM task_completions
            WHERE username = ?
        """, (username,))
        total_xp = cursor.fetchone()[0] or 0
        
        cursor.execute("""
            SELECT t.category_id, c.name, SUM(tc.xp_earned)
            FROM task_completions tc
            JOIN tasks t ON tc.task_id = t.id
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE tc.username = ?
            GROUP BY t.category_id, c.name
        """, (username,))
        categories = [{"id": row[0], "name": row[1] or "已被刪除的分類", "xp": row[2]} 
                     for row in cursor.fetchall()]
    
    return jsonify({
        "total_xp": total_xp,
        "categories": categories
    })