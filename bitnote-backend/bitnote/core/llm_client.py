import json
import os

# Which backend to use: "ollama" (default, local, free, no API key) or
# "gemini" (hosted, needs GEMINI_API_KEY). Anyone running the app with no
# env vars set gets the original local-Ollama behavior unchanged.
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").strip().lower()


def generate_text(system_prompt: str, user_prompt: str) -> str:
    """Single-turn system+user prompt -> text. Used for structured/JSON generation."""
    if LLM_PROVIDER == "gemini":
        return _gemini_generate_text(system_prompt, user_prompt)
    return _ollama_generate_text(system_prompt, user_prompt)


def generate_chat(messages: list) -> str:
    """
    Multi-turn chat -> text.
    `messages` is a list of {"role": "system"|"user"|"assistant", "content": str}.
    """
    if LLM_PROVIDER == "gemini":
        return _gemini_generate_chat(messages)
    return _ollama_generate_chat(messages)


def generate_json(system_prompt: str, user_prompt: str, schema=None, max_retries: int = 1):
    """
    Single-turn system+user prompt -> parsed JSON (dict or list).

    Both Ollama (0.3+) and Gemini support constraining decoding to a JSON
    schema natively, so callers don't need to scrape/regex JSON out of free
    text — this always returns already-parsed, already-conformant data.

    `schema`, if given, is a Pydantic model class or a generic type built
    from one (e.g. `list[SomeModel]`). Omit it for "must be valid JSON, any
    shape" mode.

    Retries the whole generation (not just the parse) up to `max_retries`
    times if the model's output isn't valid JSON — small local models
    occasionally truncate output under constrained decoding; a fresh
    generation attempt is what actually fixes it, re-parsing the same
    truncated text won't. Hosted models rarely need this, but it costs
    nothing extra when they don't.
    """
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            if LLM_PROVIDER == "gemini":
                return _gemini_generate_json(system_prompt, user_prompt, schema)
            return _ollama_generate_json(system_prompt, user_prompt, schema)
        except json.JSONDecodeError as e:
            last_error = e
            if attempt < max_retries:
                print(
                    f"generate_json: malformed JSON from {LLM_PROVIDER} "
                    f"(attempt {attempt + 1}/{max_retries + 1}), retrying..."
                )
    raise last_error


# ------------------------- Ollama backend -------------------------


def _ollama_model() -> str:
    return os.getenv("OLLAMA_MODEL", "gemma3")


def _ollama_generate_text(system_prompt: str, user_prompt: str) -> str:
    import ollama

    response = ollama.chat(
        model=_ollama_model(),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response["message"]["content"]


def _ollama_generate_chat(messages: list) -> str:
    import ollama

    response = ollama.chat(model=_ollama_model(), messages=messages)
    return response["message"]["content"]


def _ollama_generate_json(system_prompt: str, user_prompt: str, schema):
    import ollama

    response = ollama.chat(
        model=_ollama_model(),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        format=_json_schema_for(schema) if schema is not None else "json",
    )
    return json.loads(response["message"]["content"])


def _json_schema_for(schema) -> dict:
    from pydantic import TypeAdapter

    return TypeAdapter(schema).json_schema()


# ------------------------- Gemini backend -------------------------

_gemini_client = None


def _gemini_model() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")


def _get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        from google import genai

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "LLM_PROVIDER=gemini but GEMINI_API_KEY is not set. "
                "Add it to your .env file (see .env.example)."
            )
        _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client


def _gemini_generate_text(system_prompt: str, user_prompt: str) -> str:
    from google.genai import types

    client = _get_gemini_client()
    response = client.models.generate_content(
        model=_gemini_model(),
        contents=user_prompt,
        config=types.GenerateContentConfig(system_instruction=system_prompt or None),
    )
    return response.text


def _gemini_generate_chat(messages: list) -> str:
    from google.genai import types

    client = _get_gemini_client()

    system_instruction = None
    contents = []
    for msg in messages:
        role = msg["role"]
        if role == "system":
            system_instruction = msg["content"]
            continue
        contents.append(
            types.Content(
                role="model" if role == "assistant" else "user",
                parts=[types.Part(text=msg["content"])],
            )
        )

    response = client.models.generate_content(
        model=_gemini_model(),
        contents=contents,
        config=types.GenerateContentConfig(system_instruction=system_instruction),
    )
    return response.text


def _gemini_generate_json(system_prompt: str, user_prompt: str, schema):
    from google.genai import types

    client = _get_gemini_client()

    config_kwargs = {
        "system_instruction": system_prompt or None,
        "response_mime_type": "application/json",
    }
    if schema is not None:
        config_kwargs["response_schema"] = schema

    response = client.models.generate_content(
        model=_gemini_model(),
        contents=user_prompt,
        config=types.GenerateContentConfig(**config_kwargs),
    )
    return json.loads(response.text)
