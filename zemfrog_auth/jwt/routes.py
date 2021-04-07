from flask_smorest import Blueprint

def init_blueprint():
    blueprint = Blueprint("jwt", __name__, url_prefix="/jwt", description="JWT Authentication")
    return blueprint
