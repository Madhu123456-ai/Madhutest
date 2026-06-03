from flask_login import UserMixin


class AdminUser(UserMixin):
    def __init__(self, user_id: int, username: str):
        self.id = user_id
        self.username = username
