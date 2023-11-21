import os

from langchain.chat_models import ChatOpenAI
from langchain.embeddings import OpenAIEmbeddings
from langchain.prompts import ChatPromptTemplate
from langchain.pydantic_v1 import BaseModel
from langchain.schema.output_parser import StrOutputParser
from langchain.schema.runnable import RunnablePassthrough
from langchain.vectorstores import MomentoVectorIndex
from momento import (
    CredentialProvider,
    PreviewVectorIndexClient,
    VectorIndexConfigurations,
)

API_KEY_ENV_VAR_NAME = "MOMENTO_API_KEY"
if os.environ.get(API_KEY_ENV_VAR_NAME, None) is None:
    raise Exception(f"Missing `{API_KEY_ENV_VAR_NAME}` environment variable.")

MOMENTO_INDEX_NAME = os.environ.get("MOMENTO_INDEX_NAME", "langchain-test")

### Sample Ingest Code - this populates the vector index with data
### Run this on the first time to seed with data
# from rag_momento_vector_index import ingest
# ingest.load(API_KEY_ENV_VAR_NAME, MOMENTO_INDEX_NAME)


vectorstore = MomentoVectorIndex(
    embedding=OpenAIEmbeddings(),
    client=PreviewVectorIndexClient(
        configuration=VectorIndexConfigurations.Default.latest(),
        credential_provider=CredentialProvider.from_environment_variable(
            API_KEY_ENV_VAR_NAME
        ),
    ),
    index_name=MOMENTO_INDEX_NAME,
)
retriever = vectorstore.as_retriever()

# RAG prompt
template = """Answer the question based only on the following context:
{context}
Question: {question}
"""
prompt = ChatPromptTemplate.from_template(template)

# RAG
model = ChatOpenAI()
chain = (
    {"context": retriever, "question": RunnablePassthrough()}
    | prompt
    | model
    | StrOutputParser()
)


# Add typing for input
class Question(BaseModel):
    __root__: str


chain = chain.with_types(input_type=Question)
