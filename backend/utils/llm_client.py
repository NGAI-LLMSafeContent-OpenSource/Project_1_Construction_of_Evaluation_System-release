import os
from typing import Any, Dict, Optional

import httpx
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI


load_dotenv()


def _secret_from_env(*names: str) -> Optional[str]:
    """Read the first non-empty API key from environment variables."""
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None


def _required_secret(provider: str, *names: str) -> str:
    secret = _secret_from_env(*names)
    if secret:
        return secret
    joined_names = " or ".join(names)
    raise RuntimeError(f"{provider} API key is not configured. Set {joined_names}.")


def _provider_name() -> str:
    return os.getenv("LLM_PROVIDER", "deepseek").strip().lower()


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def get_llm_runtime_config() -> Dict[str, Any]:
    """Return the active LLM runtime configuration without exposing API keys."""
    provider = _provider_name()
    timeout_seconds = _env_float("LLM_TIMEOUT_SECONDS", 180.0)
    max_retries = _env_int("LLM_MAX_RETRIES", 1)

    if provider == "ollama":
        return {
            "provider": "ollama",
            "model": os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct"),
            "base_url": os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1"),
            "timeout_seconds": timeout_seconds,
            "max_retries": max_retries,
        }

    if provider == "deepseek":
        return {
            "provider": "deepseek",
            "model": os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro"),
            "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            "timeout_seconds": timeout_seconds,
            "max_retries": max_retries,
        }

    if provider == "openai":
        return {
            "provider": "openai",
            "model": os.getenv("OPENAI_MODEL", "gpt-4o"),
            "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            "timeout_seconds": timeout_seconds,
            "max_retries": max_retries,
        }

    return {
        "provider": "qwen",
        "model": os.getenv("QWEN_MODEL", "qwen-plus"),
        "base_url": os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        "timeout_seconds": timeout_seconds,
        "max_retries": max_retries,
    }


def get_llm(temperature: float = 0.7) -> ChatOpenAI:
    """Create a ChatOpenAI-compatible client for qwen/openai/deepseek/ollama."""
    runtime = get_llm_runtime_config()
    provider = runtime["provider"]
    timeout_seconds = runtime["timeout_seconds"]
    max_retries = runtime["max_retries"]

    if provider == "ollama":
        return ChatOpenAI(
            api_key=_secret_from_env("OLLAMA_API_KEY", "OPENAI_API_KEY") or "ollama",
            base_url=runtime["base_url"],
            model=runtime["model"],
            temperature=temperature,
            timeout=timeout_seconds,
            max_retries=max_retries,
        )

    if provider == "deepseek":
        return ChatOpenAI(
            api_key=_required_secret("deepseek", "DEEPSEEK_API_KEY"),
            base_url=runtime["base_url"],
            model=runtime["model"],
            temperature=temperature,
            timeout=timeout_seconds,
            max_retries=max_retries,
        )

    if provider == "openai":
        return ChatOpenAI(
            api_key=_required_secret("openai", "OPENAI_API_KEY"),
            base_url=runtime["base_url"],
            model=runtime["model"],
            temperature=temperature,
            timeout=timeout_seconds,
            max_retries=max_retries,
        )

    return ChatOpenAI(
        api_key=_required_secret("qwen", "QWEN_API_KEY", "DASHSCOPE_API_KEY"),
        base_url=runtime["base_url"],
        model=runtime["model"],
        temperature=temperature,
        timeout=timeout_seconds,
        max_retries=max_retries,
    )


async def check_llm_health() -> Dict[str, Any]:
    """Check the active LLM by performing a small real invocation."""
    runtime = get_llm_runtime_config()
    provider = runtime["provider"]

    if provider == "ollama":
        base_url = str(runtime.get("base_url", "http://127.0.0.1:11434/v1"))
        ollama_root = base_url[:-3] if base_url.endswith("/v1") else base_url
        tags_url = ollama_root.rstrip("/") + "/api/tags"
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(tags_url)
                resp.raise_for_status()
                payload = resp.json()
        except Exception as exc:
            return {
                "provider": provider,
                "model": runtime.get("model"),
                "reachable": False,
                "checked": True,
                "message": f"连接本地 Ollama 失败: {exc}",
                "runtime": runtime,
            }

        models = [item.get("name", "") for item in payload.get("models", []) if isinstance(item, dict)]
        expected_model = str(runtime.get("model", "")).strip()
        has_expected = expected_model in models if expected_model else False
        return {
            "provider": provider,
            "model": runtime.get("model"),
            "reachable": True,
            "checked": True,
            "message": "本地 Ollama 可用" + ("，目标模型已就绪" if has_expected else "，但目标模型尚未拉取"),
            "runtime": runtime,
            "ollama_models": models,
            "expected_model_ready": has_expected,
        }

    try:
        response = await llm_invoke(
            "你是健康检查助手。只输出 OK。",
            "请只输出 OK。",
            temperature=0,
        )
    except Exception as exc:
        return {
            "provider": provider,
            "model": runtime.get("model"),
            "reachable": False,
            "checked": True,
            "message": str(exc),
            "runtime": runtime,
        }

    reachable = "OK" in response.upper()
    return {
        "provider": provider,
        "model": runtime.get("model"),
        "reachable": reachable,
        "checked": True,
        "message": "云端模型健康检查通过" if reachable else f"模型响应未包含 OK: {response[:120]}",
        "runtime": runtime,
    }


async def llm_invoke(system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
    """Invoke the active LLM and return plain text content."""
    llm = get_llm(temperature)
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]
    response = await llm.ainvoke(messages)
    content = response.content
    if isinstance(content, str):
        return content
    return "\n".join(item if isinstance(item, str) else str(item) for item in content)
