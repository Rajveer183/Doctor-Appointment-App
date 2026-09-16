"""Thin async wrapper around the NVIDIA NIM (build.nvidia.com) API.

Embeddings: OpenAI-compatible `/embeddings` endpoint, plus an NVIDIA-specific
required field, `input_type` ("query" for a live user search, "passage" for
text being indexed) — the E5/NV-Embed-QA family are asymmetric embedding
models, so query and document text are embedded differently, and NVIDIA
punts that on to the caller instead of making it symmetric.

Chat completions: OpenAI-compatible `/chat/completions` endpoint including
`tools` / `tool_choice` / `tool_calls`, used by the chatbot service in
Phase 5 for tool calling.
"""
import httpx

from app.config import settings


class NvidiaAPIError(RuntimeError):
    pass


def _client() -> httpx.AsyncClient:
    if not settings.nvidia_api_key:
        raise NvidiaAPIError("NVIDIA_API_KEY is not set")
    return httpx.AsyncClient(
        base_url=settings.nvidia_base_url,
        headers={"Authorization": f"Bearer {settings.nvidia_api_key}"},
        timeout=30.0,
    )


async def embed(texts: list[str], input_type: str) -> list[list[float]]:
    """input_type must be "query" (live search text) or "passage" (taxonomy text being indexed)."""
    async with _client() as client:
        response = await client.post(
            "/embeddings",
            json={
                "input": texts,
                "model": settings.nvidia_embed_model,
                "input_type": input_type,
                "encoding_format": "float",
            },
        )
        if response.status_code >= 400:
            raise NvidiaAPIError(f"NVIDIA embeddings API error {response.status_code}: {response.text}")
        data = response.json()
        return [item["embedding"] for item in sorted(data["data"], key=lambda d: d["index"])]


async def chat_completion(messages: list[dict], tools: list[dict] | None = None, tool_choice: str = "auto") -> dict:
    payload = {"model": settings.nvidia_chat_model, "messages": messages}
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = tool_choice

    async with _client() as client:
        response = await client.post("/chat/completions", json=payload)
        if response.status_code >= 400:
            raise NvidiaAPIError(f"NVIDIA chat API error {response.status_code}: {response.text}")
        return response.json()
