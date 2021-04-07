from zemfrog.helper import get_object_model
from werkzeug.local import LocalProxy

User = LocalProxy(lambda: get_object_model("user"))
Role = LocalProxy(lambda: get_object_model("role"))
Permission = LocalProxy(lambda: get_object_model("permission"))
Log = LocalProxy(lambda: get_object_model("log"))
