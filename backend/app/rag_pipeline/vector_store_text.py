import faiss
import numpy as np
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.schema import Document
from pathlib import Path
from loguru import logger
import json
import pickle

import config


def build_index(embeddings):
    """Build a basic FAISS index from embeddings."""
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)
    return index


def save_vector_store(embeddings, chunks, metadata_list):
    """Save embeddings and chunks to a FAISS vector store."""
    try:
        logger.info("Creating vector store from embeddings")

        # Create embedding model instance
        embedding_model = HuggingFaceEmbeddings(
            model_name=config.EMBEDDING_MODEL, model_kwargs={"device": "cpu"}
        )

        # Create Document objects
        documents = []
        for i, (chunk, metadata) in enumerate(zip(chunks, metadata_list)):
            doc = Document(page_content=chunk, metadata=metadata)
            documents.append(doc)

        logger.info(f"Created {len(documents)} documents")

        # Create FAISS vector store
        vectorstore = FAISS.from_documents(
            documents=documents, embedding=embedding_model
        )

        # Save to disk
        index_path = config.INDEX_DIR / "faiss_index"
        vectorstore.save_local(str(index_path))

        # Update metadata file
        metadata_file = config.INDEX_DIR / "text_metadata.json"
        if metadata_file.exists():
            with open(metadata_file, "r") as f:
                metadata = json.load(f)
        else:
            metadata = {
                "embedding_model": config.EMBEDDING_MODEL,
                "chunk_size": config.CHUNK_SIZE,
                "chunk_overlap": config.CHUNK_OVERLAP,
                "created_at": None,
                "total_documents": 0,
                "total_chunks": 0,
            }

        from datetime import datetime

        metadata["created_at"] = datetime.now().isoformat()
        metadata["total_chunks"] = len(chunks)
        metadata["total_documents"] = len(set(m["file"] for m in metadata_list))

        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Vector store saved successfully to {index_path}")
        return True

    except Exception as e:
        logger.error(f"Error saving vector store: {e}")
        return False


def load_vector_store():
    """Load the FAISS vector store from disk."""
    try:
        index_path = config.INDEX_DIR / "faiss_index"

        if not index_path.exists():
            logger.warning("No vector store found")
            return None

        embedding_model = HuggingFaceEmbeddings(
            model_name=config.EMBEDDING_MODEL, model_kwargs={"device": "cpu"}
        )

        vectorstore = FAISS.load_local(
            str(index_path),
            embeddings=embedding_model,
            allow_dangerous_deserialization=True,
        )

        logger.info("Vector store loaded successfully")
        return vectorstore

    except Exception as e:
        logger.error(f"Error loading vector store: {e}")
        return None
