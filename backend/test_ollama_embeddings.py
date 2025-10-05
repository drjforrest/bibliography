#!/usr/bin/env python3
"""
Test Ollama embedding model configuration
"""

import asyncio
import logging
import os
import sys

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_ollama_embeddings():
    """Test Ollama embedding model"""
    
    print("=== Testing Ollama Embedding Model Configuration ===")
    
    try:
        # Get config
        config = Config()
        
        print(f"Embedding Model: {config.EMBEDDING_MODEL}")
        print(f"OpenAI API Base: {os.getenv('OPENAI_API_BASE')}")
        print(f"OpenAI API Key: {os.getenv('OPENAI_API_KEY')}")
        
        # Test embedding model
        print("\nTesting embedding model...")
        embedding_model = config.embedding_model_instance
        
        # Test embedding generation
        test_text = "This is a test document for embedding generation."
        print(f"Testing with text: '{test_text}'")
        
        # Check available methods
        print(f"Available methods: {[method for method in dir(embedding_model) if not method.startswith('_')]}")
        
        # Generate embeddings
        if hasattr(embedding_model, 'embed'):
            embedding = embedding_model.embed(test_text)
            print(f"Generated embedding with dimension: {len(embedding)}")
            print(f"First few values: {embedding[:5]}")
            print(f"Embedding model dimension: {embedding_model.dimension}")
        elif hasattr(embedding_model, 'embed_documents'):
            embeddings = embedding_model.embed_documents([test_text])
            print(f"Generated embedding with dimension: {len(embeddings[0])}")
            print(f"First few values: {embeddings[0][:5]}")
        elif hasattr(embedding_model, 'embed_query'):
            embedding = embedding_model.embed_query(test_text)
            print(f"Generated embedding with dimension: {len(embedding)}")
            print(f"First few values: {embedding[:5]}")
        elif hasattr(embedding_model, 'encode'):
            embedding = embedding_model.encode([test_text])
            print(f"Generated embedding with dimension: {len(embedding[0])}")
            print(f"First few values: {embedding[0][:5]}")
        else:
            print("Could not find embedding method")
            print(f"Type: {type(embedding_model)}")
            return
        
        print("\n✅ Ollama embedding model is working correctly!")
        
    except Exception as e:
        logger.error(f"Error testing Ollama embeddings: {str(e)}")
        print(f"\nERROR: {str(e)}")
        print("\nMake sure:")
        print("1. Ollama is running (ollama serve)")
        print("2. nomic-embed-text model is pulled (ollama pull nomic-embed-text)")
        print("3. Ollama is accessible at http://localhost:11434")


if __name__ == "__main__":
    asyncio.run(test_ollama_embeddings())