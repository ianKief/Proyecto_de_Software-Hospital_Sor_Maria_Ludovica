from flask import Blueprint, render_template, request
from src.core.users.models import User
from src.web.helpers.auth import permission_required

users_bp = Blueprint('users', __name__, url_prefix='/users')

@users_bp.route('/')
@permission_required('user_index')
def user_index():
    page = request.args.get('page', 1, type=int)
    users = User.query.paginate(page=page, per_page=25, error_out=False)
    return render_template('users/users_list.html', users=users)
