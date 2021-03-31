from flask import Blueprint

def init_blueprint():
    blueprint = Blueprint("jwt", __name__, url_prefix="/jwt")
    return blueprint
