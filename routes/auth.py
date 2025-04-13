from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template
from db import Database
import bcrypt

bp = Blueprint("auth", __name__)

@bp.route("/")
def index():
        return render_template("index.html", register=False)

@bp.route("/login", methods=["GET", "POST"])
def login():
    username = request.form.get("un")
    password = request.form.get("pwd")
    if not username or not password:
        return jsonify({"error": "請提供使用者名稱和密碼"}), 400
    db = Database()
    user = db.get_user(username)
    if not user:
        return jsonify({"error": "帳號不存在"}), 404
    if bcrypt.checkpw(password.encode('utf-8'), user["password"].encode('utf-8')):
        session["username"] = username
        return jsonify({"message": "登入成功"})
    return jsonify({"error": "密碼錯誤"}), 401

@bp.route("/register", methods=["POST"])
def register():
    username = request.form.get("un")
    password = request.form.get("pwd")
    if not username or not password:
        return jsonify({"error": "請提供使用者名稱和密碼"}), 400
    db = Database()
    if db.get_user(username):
        return jsonify({"error": "使用者名稱已存在"}), 400
    db.add_user(username, password)
    return jsonify({"message": "註冊成功"})

@bp.route("/logins", methods=["GET", "POST"])
def admin_login():
    if request.method == "GET":
        return render_template("login.html")
    username = request.form.get("username")
    password = request.form.get("password")
    if not username or not password:
        return jsonify({"error": "請提供使用者名稱和密碼"}), 400
    if username != "admin":
        return jsonify({"error": "請使用管理員帳號登入"}), 403
    db = Database()
    user = db.get_user(username)
    if not user:
        return jsonify({"error": "帳號不存在"}), 404
    if bcrypt.checkpw(password.encode('utf-8'), user["password"].encode('utf-8')):
        session["username"] = username
        return jsonify({"message": "登入成功"})
    return jsonify({"error": "密碼錯誤"}), 401

@bp.route("/logout", methods=["POST"])
def logout():
    session.pop("username", None)
    return render_template("index.html", register=False)