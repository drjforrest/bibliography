#!/usr/bin/env python3
"""
Check what methods are available on the embedding model
"""

import sys
sys.path.append('/Users/drjforrest/dev/devprojects/bibliography/backend')

from app.config import config

print(f"Embedding model: {config.EMBEDDING_MODEL}")
print(f"Model type: {type(config.embedding_model_instance)}")
print(f"Available methods: {[method for method in dir(config.embedding_model_instance) if not method.startswith('_')]}")

# Try to get dimensions
if hasattr(config.embedding_model_instance, 'dimension'):
    print(f"Dimension: {config.embedding_model_instance.dimension}")

# Try to call the appropriate method
test_text = "This is a test"

if hasattr(config.embedding_model_instance, 'embed'):
    try:
        result = config.embedding_model_instance.embed(test_text)
        print(f"embed() works: {len(result)} dimensions")
    except Exception as e:
        print(f"embed() failed: {e}")

if hasattr(config.embedding_model_instance, 'embed_text'):
    try:
        result = config.embedding_model_instance.embed_text(test_text)
        print(f"embed_text() works: {len(result)} dimensions")
    except Exception as e:
        print(f"embed_text() failed: {e}")

if hasattr(config.embedding_model_instance, '__call__'):
    try:
        result = config.embedding_model_instance(test_text)
        print(f"__call__() works: {len(result)} dimensions")
    except Exception as e:
        print(f"__call__() failed: {e}")