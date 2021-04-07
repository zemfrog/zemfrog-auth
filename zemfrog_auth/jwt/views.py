from datetime import datetime, timedelta
from flask_jwt_extended import create_access_token, decode_token, get_raw_jwt
from jwt import DecodeError, ExpiredSignatureError
from marshmallow import fields
from werkzeug.security import generate_password_hash, check_password_hash
from zemfrog.decorators import http_code, authenticate, use_kwargs, marshal_with
from zemfrog.helper import db_add, db_update, db_commit, get_mail_template, get_user_roles
from zemfrog.models import (
    DefaultResponseSchema,
    LoginSchema,
    LoginSuccessSchema,
    PasswordResetSchema,
    RegisterSchema,
    RequestPasswordResetSchema,
)

from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from zemfrog.tasks import send_email
from ..models import User, Log, Role, Permission
from ..signals import *


class PermissionSchema(SQLAlchemyAutoSchema):
    class Meta:
        ordered = True
        model = Permission


class RoleSchema(SQLAlchemyAutoSchema):
    class Meta:
        ordered = True
        model = Role

    permissions = fields.List(fields.Nested(PermissionSchema()))


class UserDetailSchema(SQLAlchemyAutoSchema):
    class Meta:
        ordered = True
        model = User
        exclude = ("password",)

    roles = fields.List(fields.Nested(RoleSchema()))


@authenticate()
@marshal_with(200, UserDetailSchema)
def user_detail():
    """
    User detail info.
    """

    email = get_raw_jwt().get("identity")
    user = User.query.filter_by(email=email).first()
    return user

@use_kwargs(LoginSchema(), location="form")
@marshal_with(404, DefaultResponseSchema)
@marshal_with(200, LoginSuccessSchema)
@http_code
def login(kwds):
    """
    Login and get access token.
    """

    email = kwds.get("username")
    passw = kwds.get("password")
    user = User.query.filter_by(email=email).first()
    if user and user.confirmed and check_password_hash(user.password, passw):
        login_date = datetime.utcnow()
        log = Log(login_date=login_date)
        user.logs.append(log)
        db_commit()
        roles = get_user_roles(user)
        claims = {"roles": roles}
        access_token = create_access_token(email, user_claims=claims)
        on_user_logged_in.send(user)
        return {"access_token": access_token}

    return {"message": "Incorrect email or password.", "code": 404}


@use_kwargs(RegisterSchema(), location="form")
@marshal_with(200, DefaultResponseSchema)
@marshal_with(403, DefaultResponseSchema)
@http_code
def register(kwds):
    """
    Register an account.
    """

    email = kwds.get("username")
    passw = kwds.get("password")
    first_name = kwds.get("first_name")
    last_name = kwds.get("last_name")
    username = first_name + " " + last_name
    if email:
        user = User.query.filter_by(email=email).first()
        if not user:
            if username and passw:
                passw = generate_password_hash(passw)
                user = User(
                    first_name=first_name,
                    last_name=last_name,
                    name=username,
                    email=email,
                    password=passw,
                    registration_date=datetime.utcnow(),
                )
                db_add(user)
                token = create_access_token(
                    user.id,
                    expires_delta=False,
                    user_claims={"token_registration": True},
                )
                msg = get_mail_template("register.html", token=token)
                send_email.delay("Registration", html=msg, recipients=[email])
                on_user_registration.send(user)
                message = "Successful registration."
                status_code = 200
            else:
                message = "Username and password are required."
                status_code = 403
        else:
            message = "Email already exists."
            status_code = 403
    else:
        message = "Email required."
        status_code = 403

    return {"message": message, "code": status_code}


@marshal_with(200, DefaultResponseSchema)
@marshal_with(403, DefaultResponseSchema)
@http_code
def confirm_account(token):
    """
    Confirm account.
    """

    try:
        data = decode_token(token)
        if not data["user_claims"].get("token_registration"):
            raise DecodeError

        uid = data["identity"]
        user = User.query.filter_by(id=uid).first()
        if user and not user.confirmed:
            message = "Confirmed."
            status_code = 200
            db_update(user, confirmed=True, date_confirmed=datetime.utcnow())
            on_confirmed_user.send(user)

        else:
            raise DecodeError

    except DecodeError:
        message = "Invalid token."
        status_code = 403

    return {"message": message, "code": status_code}


@use_kwargs(RequestPasswordResetSchema(), location="form")
@marshal_with(200, DefaultResponseSchema)
@marshal_with(404, DefaultResponseSchema)
@marshal_with(403, DefaultResponseSchema)
@http_code
def request_password_reset(kwds):
    """
    Request a password reset.
    """

    email = kwds.get("username")
    if email:
        user = User.query.filter_by(email=email).first()
        if not user:
            message = "User not found."
            status_code = 404
        else:
            message = "A password reset request has been sent."
            status_code = 200
            token = create_access_token(
                user.id,
                expires_delta=timedelta(hours=2),
                user_claims={"token_password_reset": True},
            )
            msg = get_mail_template(
                "forgot_password.html", token=token
            )
            send_email.delay("Forgot password", html=msg, recipients=[email])
            log = Log(date_requested_password_reset=datetime.utcnow())
            user.logs.append(log)
            db_commit()
            on_forgot_password.send(user)
    else:
        message = "Email required."
        status_code = 403

    return {"message": message, "code": status_code}


@marshal_with(200, DefaultResponseSchema)
@marshal_with(401, DefaultResponseSchema)
@marshal_with(403, DefaultResponseSchema)
@http_code
def confirm_password_reset_token(token):
    """
    Validate password reset token.
    """

    try:
        data = decode_token(token)
        if not data["user_claims"].get("token_password_reset"):
            raise DecodeError

        uid = data["identity"]
        user = User.query.filter_by(id=uid).first()
        if user:
            message = "Valid token."
            status_code = 200
        else:
            raise DecodeError

    except DecodeError:
        message = "Invalid token."
        status_code = 401

    except ExpiredSignatureError:
        message = "Token expired."
        status_code = 403

    return {"message": message, "code": status_code}


@use_kwargs(PasswordResetSchema(), location="form")
@marshal_with(200, DefaultResponseSchema)
@marshal_with(403, DefaultResponseSchema)
@marshal_with(401, DefaultResponseSchema)
@marshal_with(404, DefaultResponseSchema)
@http_code
def password_reset(kwds, token):
    """
    Reset user password.
    """

    try:
        data = decode_token(token)
        if not data["user_claims"].get("token_password_reset"):
            raise DecodeError

        uid = data["identity"]
        user = User.query.filter_by(id=uid).first()
        passw = kwds.get("password")
        if user and passw:
            passw = generate_password_hash(passw)
            log = Log(date_set_new_password=datetime.utcnow())
            user.logs.append(log)
            db_update(user, password=passw)
            on_reset_password.send(user)
            message = "Successfully change password."
            status_code = 200
        else:
            message = "User not found."
            status_code = 404

    except DecodeError:
        message = "Invalid token."
        status_code = 401

    except ExpiredSignatureError:
        message = "Token expired."
        status_code = 403

    return {"message": message, "code": status_code}
