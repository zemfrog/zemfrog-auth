from . import views

routes = [
    ("/user", views.user_detail, ["GET"]),
    ("/login", views.login, ["POST"]),
    ("/register", views.register, ["POST"]),
    ("/confirm/<token>", views.confirm_account, ["GET"]),
    ("/forgot-password", views.request_password_reset, ["POST"]),
    ("/reset-password/verify/<token>", views.confirm_password_reset_token, ["GET"]),
    ("/reset-password/<token>", views.password_reset, ["POST"]),
]
