from flask import Flask
from flask_restx import Api
from config import Config

from app.routes.chat import api as chat_ns
from app.routes.health import api as health_ns


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    api = Api(
        app,
        title="Oncology Assistant API",
        version="1.0",
        doc="/docs"
    )

    api.add_namespace(health_ns, path="/health")
    api.add_namespace(chat_ns, path="/chat")

    return app
