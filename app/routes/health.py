from flask_restx import Namespace, Resource

api = Namespace("health", description="Health check")

@api.route("")
class Health(Resource):
    def get(self):
        return {
            "status": "ok",
            "service": "Oncology Assistant Backend"
        }, 200
