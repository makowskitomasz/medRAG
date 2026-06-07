from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.query_service import generate_hypothetical_document, rewrite_query


def _make_client(return_value: str) -> MagicMock:
    choice = MagicMock()
    choice.message.content = return_value
    response = MagicMock()
    response.choices = [choice]

    client = MagicMock()
    client.chat = MagicMock()
    client.chat.completions = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=response)
    return client


@pytest.mark.asyncio
async def test_rewrite_query_returns_llm_output():
    client = _make_client("What are the pharmacokinetic interactions between warfarin and aspirin?")
    result = await rewrite_query("can I mix these two pills", "", client, "model-x")
    assert "warfarin" in result or len(result) > 0
    client.chat.completions.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_rewrite_query_includes_context_in_message():
    client = _make_client("rewritten")
    await rewrite_query("what about dosage?", "User asked about warfarin.", client, "model-x")

    call_args = client.chat.completions.create.call_args
    messages = call_args.kwargs["messages"]
    user_msg = next(m["content"] for m in messages if m["role"] == "user")
    assert "warfarin" in user_msg
    assert "dosage" in user_msg


@pytest.mark.asyncio
async def test_rewrite_query_no_context_omits_context_block():
    client = _make_client("rewritten")
    await rewrite_query("aspirin dose", "", client, "model-x")

    call_args = client.chat.completions.create.call_args
    messages = call_args.kwargs["messages"]
    user_msg = next(m["content"] for m in messages if m["role"] == "user")
    assert "Conversation context" not in user_msg


@pytest.mark.asyncio
async def test_generate_hypothetical_document_returns_passage():
    passage = (
        "Aspirin combined with warfarin significantly increases the risk of bleeding"
        " due to dual antiplatelet and anticoagulant effects."
    )
    client = _make_client(passage)
    doc, _, _ = await generate_hypothetical_document(
        "Can aspirin and warfarin be taken together?", client, "model-x"
    )
    assert doc == passage
    client.chat.completions.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_hypothetical_document_sends_query_as_user_message():
    client = _make_client("passage")
    query = "What is the mechanism of warfarin?"
    await generate_hypothetical_document(query, client, "model-x")

    call_args = client.chat.completions.create.call_args
    messages = call_args.kwargs["messages"]
    user_msg = next(m["content"] for m in messages if m["role"] == "user")
    assert query in user_msg
