from app import create_app
from app.extensions import db
from app.models.chat_conversation import ChatConversation

app = create_app()
with app.app_context():
    conv = ChatConversation.query.first()
    if conv:
        for m in conv.messages:
            print(f{m.role.value}:
