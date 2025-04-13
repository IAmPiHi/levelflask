from flask import Flask
from routes import auth, admin, tasks, stats, settings
import os
from dotenv import load_dotenv

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "d2DFD^FGDGfB$s23@jhGGXSBCdj@hgsD1")  # 用於會話加密
    app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "sound")

    # 註冊藍圖
    app.register_blueprint(auth.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(tasks.bp)
    app.register_blueprint(stats.bp)
    app.register_blueprint(settings.bp)

    # 錯誤處理
    @app.errorhandler(404)
    def not_found(e):
        return {"error": "404 Not Found"}, 404

    @app.errorhandler(403)
    def forbidden(e):
        return {"error": "403 Forbidden"}, 403

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)), debug=os.getenv("FLASK_ENV") == "development")