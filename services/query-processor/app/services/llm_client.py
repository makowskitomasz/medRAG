import instructor
from openai import AsyncOpenAI

_raw_client: AsyncOpenAI | None = None
_instructor_client: instructor.AsyncInstructor | None = None


def get_llm_client(base_url: str, api_key: str) -> AsyncOpenAI:
    global _raw_client
    if _raw_client is None:
        _raw_client = AsyncOpenAI(base_url=base_url, api_key=api_key)
    return _raw_client


def get_instructor_client(base_url: str, api_key: str) -> instructor.AsyncInstructor:
    global _instructor_client
    if _instructor_client is None:
        raw = get_llm_client(base_url, api_key)
        _instructor_client = instructor.from_openai(raw, mode=instructor.Mode.JSON)
    return _instructor_client


async def chat_complete(client: AsyncOpenAI, model: str, system: str, user: str) -> str:
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return response.choices[0].message.content or ""
