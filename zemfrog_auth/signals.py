from blinker import signal

on_user_logged_in = signal("on_user_logged_in", "when the user is logged in")
on_user_registration = signal("on_user_registration", "when the user registers")
on_confirmed_user = signal("on_confirmed_user", "when the user is confirmed")
on_forgot_password = signal("on_forgot_password", "when it asks for a user password reset")
on_reset_password = signal("on_reset_password", "when the user has successfully reset the password")
