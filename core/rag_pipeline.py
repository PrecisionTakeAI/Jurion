# Vector database and RAG components with graceful fallbacks
import logging

logger = logging.getLogger(__name__)

# Try to import vector database components
try:
    from langchain_community.document_loaders import TextLoader
    from langchain_text_splitters import CharacterTextSplitter
    from langchain_chroma import Chroma
    from langchain_ollama import OllamaEmbeddings, ChatOllama
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.runnables import RunnablePassthrough
    from langchain_core.output_parsers import StrOutputParser
    VECTOR_DB_AVAILABLE = True
    logger.info("Vector database components loaded successfully")
except ImportError as e:
    VECTOR_DB_AVAILABLE = False
    logger.warning(f"Vector database components not available: {e}")
    logger.info("RAG pipeline will operate in fallback mode without vector search")

def index_documents(doc_paths, persist_dir="./legal_db"):
    """Index documents for vector search with fallback support"""
    
    if not VECTOR_DB_AVAILABLE:
        logger.warning("Vector database not available. Document indexing skipped.")
        return None
    
    docs = []
    try:
        for path in doc_paths:
            loader = TextLoader(path)  # Integrate with my existing extractors like pdfplumber
            docs.extend(loader.load())
    except Exception as e:
        logger.error(f"Error loading documents: {e}")
        return None
    
    try:
        splitter = CharacterTextSplitter(chunk_size=1500, chunk_overlap=300)
        splits = splitter.split_documents(docs)
        
        embeddings = OllamaEmbeddings(model="nomic-embed-text")
        vectorstore = Chroma.from_documents(documents=splits, embedding=embeddings, persist_directory=persist_dir)
        logger.info(f"Successfully indexed {len(splits)} document chunks")
        return vectorstore
    except Exception as e:
        logger.error(f"Error creating vector store: {e}")
        return None

def answer_question(question, vectorstore=None):
    """Answer questions using RAG pipeline with fallback support"""
    
    if not VECTOR_DB_AVAILABLE:
        logger.warning("Vector database not available. Returning generic legal disclaimer.")
        return ("I apologize, but the advanced document search functionality is not available. "
                "Please consult with a qualified legal professional for specific legal advice. "
                "This system requires additional dependencies to be installed for full functionality.")
    
    if vectorstore is None:
        logger.warning("No vector store provided. Cannot perform document-based search.")
        return ("No document index is available for search. Please index documents first using "
                "the index_documents function, or consult with a legal professional.")
    
    try:
        llm = ChatOllama(model="deepseek-r1:8b")  # Use DeepSeek R1 8B variant
        
        retriever = vectorstore.as_retriever(search_type="mmr", search_kwargs={"k": 5})
        
        template = """You are an expert legal assistant specializing in contract and loan analysis. Use only the provided context to answer. Be precise, cite sources, and highlight risks.
        Context: {context}
        Question: {question}
        Answer:"""
        prompt = ChatPromptTemplate.from_template(template)
        
        chain = (
            {"context": retriever | (lambda docs: "\n\n".join(doc.page_content for doc in docs)),
             "question": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
        )
        
        result = chain.invoke(question)
        logger.info(f"Successfully answered question using RAG pipeline")
        return result
        
    except Exception as e:
        logger.error(f"Error in RAG pipeline: {e}")
        return (f"An error occurred while processing your question: {str(e)}. "
                "Please consult with a qualified legal professional for assistance.")

# Export availability status for other modules to check
def is_vector_db_available():
    """Check if vector database functionality is available"""
    return VECTOR_DB_AVAILABLE
