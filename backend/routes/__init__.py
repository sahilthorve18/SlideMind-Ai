from routes.assets import bp as assets_bp
from routes.auth import bp as auth_bp
from routes.conversations import bp as conversations_bp
from routes.documents import bp as documents_bp
from routes.presentations import bp as presentations_bp
from routes.rehearsal import bp as rehearsal_bp
from routes.research import bp as research_bp

ALL_BLUEPRINTS = [
    assets_bp,
    auth_bp,
    conversations_bp,
    documents_bp,
    presentations_bp,
    rehearsal_bp,
    research_bp,
]
