import os


STANDALONE_MODE = "standalone"
INTEGRATION_MODE = "integration"


def get_runtime_mode(env=None):
    env = os.environ if env is None else env
    return INTEGRATION_MODE if env.get("APP_RUNTIME_MODE") == INTEGRATION_MODE else STANDALONE_MODE


def get_app_port(env=None):
    env = os.environ if env is None else env
    explicit_port = env.get("APP_PORT")
    if explicit_port:
        try:
            return int(explicit_port)
        except ValueError as exc:
            raise ValueError(f"APP_PORT must be an integer, got: {explicit_port}") from exc
    return 6102 if get_runtime_mode(env) == INTEGRATION_MODE else 8000


def get_debug_enabled(env=None):
    env = os.environ if env is None else env
    return env.get("DEBUG", "false").lower() == "true"


def get_reload_enabled(env=None):
    env = os.environ if env is None else env
    return get_debug_enabled(env) and get_runtime_mode(env) != INTEGRATION_MODE


def get_default_cors_origins(mode):
    if mode == INTEGRATION_MODE:
        return [
            "http://127.0.0.1:6101",
            "http://localhost:6101",
            "http://127.0.0.1:16101",
            "http://localhost:16101",
            "http://127.0.0.1:5173",
            "http://localhost:5173",
        ]

    return [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://0.0.0.0:5173",
    ]


def get_cors_allow_origins(env=None):
    env = os.environ if env is None else env
    configured = env.get("CORS_ALLOW_ORIGINS", "").strip()
    if configured:
        return [item.strip() for item in configured.split(",") if item.strip()]
    return get_default_cors_origins(get_runtime_mode(env))


def get_docs_url(env=None):
    env = os.environ if env is None else env
    host = env.get("APP_HOST", "0.0.0.0")
    host = "localhost" if host == "0.0.0.0" else host
    return f"http://{host}:{get_app_port(env)}/docs"
