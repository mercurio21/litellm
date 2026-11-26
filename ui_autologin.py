"""Admin UI without a login form, for a proxy that sits behind another gate (Cloudflare Access).

Off by default. With LITELLM_UI_AUTOLOGIN=true, GET /ui/login signs the visitor in as the proxy
admin (the same session /login would mint for the env credentials) and redirects to the dashboard,
so nobody types UI_USERNAME/UI_PASSWORD. The API is untouched: keys and the master key still apply.

Loaded as a callback (litellm_settings.callbacks) only to get imported at startup; it does nothing
until the proxy app exists, then puts one route in front of the /ui static mount.
"""

import os

from litellm._logging import verbose_proxy_logger
from litellm.integrations.custom_logger import CustomLogger

_ENABLED = os.getenv("LITELLM_UI_AUTOLOGIN", "false").lower() == "true"


async def _autologin(request):
    from starlette.responses import RedirectResponse

    from litellm.proxy import proxy_server as ps
    from litellm.proxy.auth.login_throttle import LoginThrottle
    from litellm.proxy.auth.login_utils import (
        authenticate_user,
        create_ui_token_object,
        encode_ui_session_jwt,
        get_ui_credentials,
    )
    from litellm.proxy.management_endpoints.ui_sso import set_session_token_cookie
    from litellm.proxy.utils import get_custom_url

    username, password = get_ui_credentials(ps.master_key)
    result = await authenticate_user(
        username=username,
        password=password,
        master_key=ps.master_key,
        prisma_client=ps.prisma_client,
        throttle=LoginThrottle.from_request(request, ps.general_settings, ps.redis_usage_cache),
        general_settings=ps.general_settings,
    )
    token_object = create_ui_token_object(
        login_result=result, general_settings=ps.general_settings, premium_user=ps.premium_user
    )
    jwt_token = encode_ui_session_jwt(token_object, str(ps.master_key))
    target = get_custom_url(str(request.base_url)).rstrip("/") + "/ui?login=success"
    response = RedirectResponse(url=target, status_code=303)
    set_session_token_cookie(response, request, jwt_token)
    return response


def _install() -> None:
    from starlette.routing import Route

    from litellm.proxy.proxy_server import app

    if any(getattr(r, "name", "") == "ui_autologin" for r in app.router.routes):
        return
    for path in ("/ui/login", "/ui/login/"):
        app.router.routes.insert(0, Route(path, _autologin, methods=["GET"], name="ui_autologin"))
    verbose_proxy_logger.warning("ui_autologin: /ui/login signs in as proxy admin (LITELLM_UI_AUTOLOGIN=true)")


class UIAutologin(CustomLogger):
    def __init__(self) -> None:
        super().__init__()
        if _ENABLED:
            _install()


proxy_handler_instance = UIAutologin()
