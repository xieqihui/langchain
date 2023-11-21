import os

from langchain.embeddings import VertexAIEmbeddings
from langchain.llms import VertexAI
from langchain.prompts import PromptTemplate
from langchain.schema.output_parser import StrOutputParser
from langchain.schema.runnable import RunnableParallel, RunnablePassthrough
from langchain.vectorstores import MatchingEngine

# you need to preate the index first, for example, as described here:
# https://github.com/GoogleCloudPlatform/generative-ai/blob/main/language/use-cases/document-qa/question_answering_documents_langchain_matching_engine.ipynb
expected_variables = [
    "project_id",
    "me_region",
    "gcs_bucket",
    "me_index_id",
    "me_endpoint_id",
]
variables = []
for variable_name in expected_variables:
    variable = os.environ.get(variable_name.upper())
    if not variable:
        raise Exception(f"Missing `{variable_name}` environment variable.")
    variables.append(variable)

project_id, me_region, gcs_bucket, me_index_id, me_endpoint_id = variables


vectorstore = MatchingEngine.from_components(
    project_id=project_id,
    region=me_region,
    gcs_bucket_name=gcs_bucket,
    embedding=VertexAIEmbeddings(),
    index_id=me_index_id,
    endpoint_id=me_endpoint_id,
)

model = VertexAI()

template = (
    "SYSTEM: You are an intelligent assistant helping the users with their questions"
    "on research papers.\n\n"
    "Question: {question}\n\n"
    "Strictly Use ONLY the following pieces of context to answer the question at the "
    "end. Think step-by-step and then answer.\n\n"
    "Do not try to make up an answer:\n"
    "- If the answer to the question cannot be determined from the context alone, "
    'say \n"I cannot determine the answer to that."\n'
    '- If the context is empty, just say "I do not know the answer to that."\n\n'
    "=============\n{context}\n=============\n\n"
    "Question: {question}\nHelpful Answer: "
)

prompt = PromptTemplate.from_template(template)

retriever = vectorstore.as_retriever(
    search_type="similarity",
    search_kwargs={
        "k": 10,
        "search_distance": 0.6,
    },
)

chain = (
    RunnableParallel({"context": retriever, "question": RunnablePassthrough()})
    | prompt
    | model
    | StrOutputParser()
)
