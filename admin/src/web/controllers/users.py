from flask import Blueprint, render_template
from src.core.users.users import list_users

users_bp = Blueprint('users', __name__, url_prefix='/users')

@users_bp.route('/')
def user_index():
    users = list_users()
    return render_template('users/users_list.html', users=users)
