from langchain.chains import RetrievalQA
from langchain_community.vectorstores import FAISS
from langchain_community.llms import Ollama
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.schema import Document
from pathlib import Path
from loguru import logger

import config
from long_term_memory import save_interaction


class QASystem:
    """Question-Answering system using RAG architecture."""

    def __init__(self):
        self.embeddings = None
        self.vectorstore = None
        self.llm = None
        self.qa_chain = None
        self._initialize_models()

    def _initialize_models(self):
        """Initialize the embedding model, LLM, and vector store."""
        try:
            # Initialize embedding model
            logger.info(f"Loading embedding model: {config.EMBEDDING_MODEL}")
            self.embeddings = HuggingFaceEmbeddings(
                model_name=config.EMBEDDING_MODEL, model_kwargs={"device": "cpu"}
            )

            # Initialize LLM
            logger.info(f"Connecting to LLM: {config.LLM_MODEL}")
            self.llm = Ollama(model=config.LLM_MODEL, base_url=config.LLM_BASE_URL)

            # Load vector store if it exists
            self._load_vector_store()

        except Exception as e:
            logger.error(f"Failed to initialize models: {e}")
            raise

    def _load_vector_store(self):
        """Load the FAISS vector store if it exists."""
        index_path = config.INDEX_DIR / "faiss_index"

        if index_path.exists():
            try:
                logger.info("Loading existing vector store")
                self.vectorstore = FAISS.load_local(
                    str(index_path),
                    embeddings=self.embeddings,
                    allow_dangerous_deserialization=True,
                )

                # Create QA chain
                self.qa_chain = RetrievalQA.from_chain_type(
                    llm=self.llm,
                    chain_type="stuff",
                    retriever=self.vectorstore.as_retriever(search_kwargs={"k": 3}),
                    return_source_documents=True,
                )

                logger.info("Vector store loaded successfully")

            except Exception as e:
                logger.error(f"Failed to load vector store: {e}")
                self.vectorstore = None
                self.qa_chain = None
        else:
            logger.warning(
                "No existing vector store found. Please process some documents first."
            )

    def run(self, question: str) -> str:
        """Run a question against the QA system."""
        if not self.qa_chain:
            return "❌ No documents have been processed yet. Please upload and process some documents first."

        try:
            logger.info(f"Processing question: {question[:50]}...")

            # Get answer with source documents
            result = self.qa_chain({"query": question})
            answer = result["result"]
            source_docs = result.get("source_documents", [])

            # Format response with sources
            formatted_response = self._format_response(answer, source_docs)

            # Save to memory
            save_interaction(question, formatted_response)

            logger.info("Question processed successfully")
            return formatted_response

        except Exception as e:
            error_msg = f"Error processing question: {str(e)}"
            logger.error(error_msg)
            return error_msg

    def _format_response(self, answer: str, docs: list) -> str:
        """Format the response with source citations."""
        if not docs:
            return answer

        # Create source references
        refs = []
        seen_sources = set()

        for doc in docs:
            metadata = doc.metadata
            source_key = f"{metadata.get('file', 'Unknown')}_{metadata.get('page', 0)}"

            if source_key not in seen_sources:
                file_name = Path(metadata.get("file", "Unknown")).name
                page = metadata.get("page", "Unknown")
                refs.append(f"📄 {file_name} (page {page})")
                seen_sources.add(source_key)

        if refs:
            sources_text = "\n".join(refs)
            return f"{answer}\n\n**Sources:**\n{sources_text}"

        return answer

    def get_stats(self) -> dict:
        """Get statistics about the current vector store."""
        if not self.vectorstore:
            return {"status": "No vector store loaded", "documents": 0}

        try:
            # Try to get document count
            doc_count = (
                self.vectorstore.index.ntotal
                if hasattr(self.vectorstore, "index")
                else 0
            )
            return {
                "status": "Active",
                "documents": doc_count,
                "model": config.EMBEDDING_MODEL,
                "llm": config.LLM_MODEL,
            }
        except:
            return {"status": "Active", "documents": "Unknown"}


# Global QA system instance
_qa_system = None


def get_qa_system() -> QASystem:
    """Get or create the global QA system instance."""
    global _qa_system
    if _qa_system is None:
        _qa_system = QASystem()
    return _qa_system


# For backward compatibility
def create_qa_chain():
    """Create and return QA system (backward compatibility)."""
    return get_qa_system()


qa = get_qa_system()  # For backward compatibility
