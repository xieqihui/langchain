"""Test Vertex AI API wrapper.
In order to run this test, you need to install VertexAI SDK (that is is the private
preview)  and be whitelisted to list the models themselves:
In order to run this test, you need to install VertexAI SDK 
pip install google-cloud-aiplatform>=1.35.0

Your end-user credentials would be used to make the calls (make sure you've run 
`gcloud auth login` first).
"""
from typing import Optional
from unittest.mock import MagicMock, Mock, patch

import pytest

from langchain.chat_models import ChatVertexAI
from langchain.chat_models.vertexai import _parse_chat_history, _parse_examples
from langchain.schema import LLMResult
from langchain.schema.messages import AIMessage, HumanMessage, SystemMessage


@pytest.mark.parametrize("model_name", [None, "codechat-bison", "chat-bison"])
def test_vertexai_instantiation(model_name: str) -> None:
    if model_name:
        model = ChatVertexAI(model_name=model_name)
    else:
        model = ChatVertexAI()
    assert model._llm_type == "vertexai"
    assert model.model_name == model.client._model_id


@pytest.mark.scheduled
@pytest.mark.parametrize("model_name", [None, "codechat-bison", "chat-bison"])
def test_vertexai_single_call(model_name: str) -> None:
    if model_name:
        model = ChatVertexAI(model_name=model_name)
    else:
        model = ChatVertexAI()
    message = HumanMessage(content="Hello")
    response = model([message])
    assert isinstance(response, AIMessage)
    assert isinstance(response.content, str)


def test_candidates() -> None:
    model = ChatVertexAI(model_name="chat-bison@001", temperature=0.3, n=2)
    message = HumanMessage(content="Hello")
    response = model.generate(messages=[[message]])
    assert isinstance(response, LLMResult)
    assert len(response.generations) == 1
    assert len(response.generations[0]) == 2


@pytest.mark.scheduled
@pytest.mark.asyncio
async def test_vertexai_agenerate() -> None:
    model = ChatVertexAI(temperature=0)
    message = HumanMessage(content="Hello")
    response = await model.agenerate([[message]])
    assert isinstance(response, LLMResult)
    assert isinstance(response.generations[0][0].message, AIMessage)  # type: ignore

    sync_response = model.generate([[message]])
    assert response.generations[0][0] == sync_response.generations[0][0]


@pytest.mark.scheduled
def test_vertexai_single_call_with_context() -> None:
    model = ChatVertexAI()
    raw_context = (
        "My name is Ned. You are my personal assistant. My favorite movies "
        "are Lord of the Rings and Hobbit."
    )
    question = (
        "Hello, could you recommend a good movie for me to watch this evening, please?"
    )
    context = SystemMessage(content=raw_context)
    message = HumanMessage(content=question)
    response = model([context, message])
    assert isinstance(response, AIMessage)
    assert isinstance(response.content, str)


@pytest.mark.scheduled
def test_vertexai_single_call_with_examples() -> None:
    model = ChatVertexAI()
    raw_context = "My name is Ned. You are my personal assistant."
    question = "2+2"
    text_question, text_answer = "4+4", "8"
    inp = HumanMessage(content=text_question)
    output = AIMessage(content=text_answer)
    context = SystemMessage(content=raw_context)
    message = HumanMessage(content=question)
    response = model([context, message], examples=[inp, output])
    assert isinstance(response, AIMessage)
    assert isinstance(response.content, str)


@pytest.mark.scheduled
@pytest.mark.parametrize("model_name", [None, "codechat-bison", "chat-bison"])
def test_vertexai_single_call_with_history(model_name: str) -> None:
    if model_name:
        model = ChatVertexAI(model_name=model_name)
    else:
        model = ChatVertexAI()
    text_question1, text_answer1 = "How much is 2+2?", "4"
    text_question2 = "How much is 3+3?"
    message1 = HumanMessage(content=text_question1)
    message2 = AIMessage(content=text_answer1)
    message3 = HumanMessage(content=text_question2)
    response = model([message1, message2, message3])
    assert isinstance(response, AIMessage)
    assert isinstance(response.content, str)


def test_parse_chat_history_correct() -> None:
    from vertexai.language_models import ChatMessage

    text_context = (
        "My name is Ned. You are my personal assistant. My "
        "favorite movies are Lord of the Rings and Hobbit."
    )
    context = SystemMessage(content=text_context)
    text_question = (
        "Hello, could you recommend a good movie for me to watch this evening, please?"
    )
    question = HumanMessage(content=text_question)
    text_answer = (
        "Sure, You might enjoy The Lord of the Rings: The Fellowship of the Ring "
        "(2001): This is the first movie in the Lord of the Rings trilogy."
    )
    answer = AIMessage(content=text_answer)
    history = _parse_chat_history([context, question, answer, question, answer])
    assert history.context == context.content
    assert len(history.history) == 4
    assert history.history == [
        ChatMessage(content=text_question, author="user"),
        ChatMessage(content=text_answer, author="bot"),
        ChatMessage(content=text_question, author="user"),
        ChatMessage(content=text_answer, author="bot"),
    ]


def test_vertexai_single_call_fails_no_message() -> None:
    chat = ChatVertexAI()
    with pytest.raises(ValueError) as exc_info:
        _ = chat([])
    assert (
        str(exc_info.value)
        == "You should provide at least one message to start the chat!"
    )


@pytest.mark.parametrize("stop", [None, "stop1"])
def test_vertexai_args_passed(stop: Optional[str]) -> None:
    response_text = "Goodbye"
    user_prompt = "Hello"
    prompt_params = {
        "max_output_tokens": 1,
        "temperature": 10000.0,
        "top_k": 10,
        "top_p": 0.5,
    }

    # Mock the library to ensure the args are passed correctly
    with patch(
        "vertexai.language_models._language_models.ChatModel.start_chat"
    ) as start_chat:
        mock_response = MagicMock()
        mock_response.candidates = [Mock(text=response_text)]
        mock_chat = MagicMock()
        start_chat.return_value = mock_chat
        mock_send_message = MagicMock(return_value=mock_response)
        mock_chat.send_message = mock_send_message

        model = ChatVertexAI(**prompt_params)
        message = HumanMessage(content=user_prompt)
        if stop:
            response = model([message], stop=[stop])
        else:
            response = model([message])

        assert response.content == response_text
        mock_send_message.assert_called_once_with(user_prompt, candidate_count=1)
        expected_stop_sequence = [stop] if stop else None
        start_chat.assert_called_once_with(
            context=None,
            message_history=[],
            **prompt_params,
            stop_sequences=expected_stop_sequence,
        )


def test_parse_examples_correct() -> None:
    from vertexai.language_models import InputOutputTextPair

    text_question = (
        "Hello, could you recommend a good movie for me to watch this evening, please?"
    )
    question = HumanMessage(content=text_question)
    text_answer = (
        "Sure, You might enjoy The Lord of the Rings: The Fellowship of the Ring "
        "(2001): This is the first movie in the Lord of the Rings trilogy."
    )
    answer = AIMessage(content=text_answer)
    examples = _parse_examples([question, answer, question, answer])
    assert len(examples) == 2
    assert examples == [
        InputOutputTextPair(input_text=text_question, output_text=text_answer),
        InputOutputTextPair(input_text=text_question, output_text=text_answer),
    ]


def test_parse_examples_failes_wrong_sequence() -> None:
    with pytest.raises(ValueError) as exc_info:
        _ = _parse_examples([AIMessage(content="a")])
    print(str(exc_info.value))
    assert (
        str(exc_info.value)
        == "Expect examples to have an even amount of messages, got 1."
    )
