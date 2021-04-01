# zemfrog-auth

Authentication for the zemfrog framework

Currently only supports JWT (JSON Web Token) authentication.


# Features

* JWT Authentication Blueprint
* Event signal support for user information (login, register, etc)


Usage
=====

Install the module

```sh
pip install zemfrog-auth
```


Add jwt blueprints to your zemfrog application

```python
BLUEPRINTS = ["zemfrog_auth.jwt"]
```


Using event signals
-------------------

In this section I will give an example of using the event signal using a blinker.

```python
# Add this to wsgi.py

from zemfrog_auth.signals import on_user_logged_in

@on_user_logged_in.connect
def on_logged_in(user):
    print("Signal user logged in:", user)
```

For a list of available signals, you can see it [here](https://github.com/zemfrog/zemfrog-auth/blob/main/zemfrog_auth/signals.py).
For signal documentation you can visit [here](https://pythonhosted.org/blinker/).
