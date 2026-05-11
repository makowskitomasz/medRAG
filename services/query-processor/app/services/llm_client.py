from openai import AsyncOpenAI

_client: AsyncOpenAI | None = None


def get_llm_client(base_url: str, api_key: str) -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(base_url=base_url, api_key=api_key)
    return _client


async def chat_complete(client: AsyncOpenAI, model: str, system: str, user: str) -> str:
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return response.choices[0].message.content or ""
