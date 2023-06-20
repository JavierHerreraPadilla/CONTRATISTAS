from functools import wraps
from flask import abort
from flask_login import current_user
from ingresos import models

def client_only(f):
    """Used to allow url only to client, not to suppliers"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if isinstance(current_user, models.Supplier):
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function


def supplier_only(f):
    """Used to allow url only to client, not to suppliers"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if isinstance(current_user, models.Client):
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function
