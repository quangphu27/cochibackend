"""Register all API blueprints."""
from app.controllers.auth_controller import auth_bp
from app.controllers.class_controller import class_bp
from app.controllers.exam_controller import exam_bp
from app.controllers.ai_controller import ai_bp
from app.controllers.content_controller import content_bp
from app.controllers.analytics_controller import analytics_bp
from app.controllers.user_controller import user_bp
from app.controllers.lms_controller import lms_bp
from app.controllers.community_controller import community_bp
from app.controllers.speaking_controller import speaking_bp, writing_bp
from app.controllers.lesson_controller import lesson_bp


def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(class_bp)
    app.register_blueprint(exam_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(content_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(lms_bp)
    app.register_blueprint(community_bp)
    app.register_blueprint(speaking_bp)
    app.register_blueprint(writing_bp)
    app.register_blueprint(lesson_bp)
