from prefect import Task

class LearInitTask(Task):

    def __init__(self, flask_app_name, **kwargs):
        self.flask_app_name = flask_app_name
        super().__init__(**kwargs)

    def run(self, config):
        from legal_api.models import db
        from flask import Flask
        FLASK_APP = Flask(self.flask_app_name)
        FLASK_APP.config.from_object(config)
        db.init_app(FLASK_APP)
        FLASK_APP.app_context().push()
        return db


