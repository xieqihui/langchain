from langchain import hub
from langchain.chat_models import ChatAnthropic
from langchain.pydantic_v1 import BaseModel
from langchain.schema import StrOutputParser
from langchain.schema.runnable import RunnableLambda, RunnablePassthrough
from langchain.utilities import WikipediaAPIWrapper


class Question(BaseModel):
    __root__: str


wiki = WikipediaAPIWrapper(top_k_results=5)
prompt = hub.pull("bagatur/chain-of-note-wiki")

llm = ChatAnthropic(model="claude-2")


def format_docs(docs):
    return "\n\n".join(
        f"Wikipedia {i+1}:\n{doc.page_content}" for i, doc in enumerate(docs)
    )


chain = (
    {
        "passages": RunnableLambda(wiki.load) | format_docs,
        "question": RunnablePassthrough(),
    }
    | prompt
    | llm
    | StrOutputParser()
).with_types(input_type=Question)
