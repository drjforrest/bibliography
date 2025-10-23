"""
Embedding Service for handling embeddings with Ollama and pgvector
"""

import logging
import asyncio
from typing import List, Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.config import config
from app.db import Document, Chunk

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating and managing embeddings using the configured embedding model"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.embedding_model = config.embedding_model_instance
        self.chunker = config.chunker_instance
    
    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text string
        
        Args:
            text: Text to embed
            
        Returns:
            List of embedding floats
        """
        try:
            if not text or not text.strip():
                logger.warning("Empty text provided for embedding")
                return []
            
            # Use the configured embedding model - handle different APIs
            if hasattr(self.embedding_model, 'embed'):
                # Chonkie SentenceTransformerEmbeddings
                embedding = await asyncio.to_thread(
                    self.embedding_model.embed,
                    text.strip()
                )
            elif hasattr(self.embedding_model, 'embed_query'):
                # LangChain OpenAI embeddings
                embedding = await asyncio.to_thread(
                    self.embedding_model.embed_query,
                    text.strip()
                )
            else:
                raise ValueError(f"Unknown embedding model interface: {type(self.embedding_model)}")
            
            # Handle numpy array validation properly
            try:
                if embedding is None:
                    logger.error("None embedding returned from model")
                    return []
                if hasattr(embedding, '__len__') and len(embedding) == 0:
                    logger.error("Empty embedding returned from model")
                    return []
                # Convert numpy array to list if needed
                if hasattr(embedding, 'tolist'):
                    embedding = embedding.tolist()
            except Exception as validation_error:
                logger.error(f"Error validating embedding: {str(validation_error)}")
                return []
            
            logger.debug(f"Generated embedding of dimension {len(embedding)}")
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            return []
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        try:
            if not texts:
                return []
            
            # Filter out empty texts
            valid_texts = [text.strip() for text in texts if text and text.strip()]
            if not valid_texts:
                logger.warning("No valid texts provided for embedding")
                return []
            
            # Use the configured embedding model for batch processing
            if hasattr(self.embedding_model, 'embed_batch'):
                # Chonkie SentenceTransformerEmbeddings
                embeddings = await asyncio.to_thread(
                    self.embedding_model.embed_batch,
                    valid_texts
                )
            elif hasattr(self.embedding_model, 'embed_documents'):
                # LangChain embeddings
                embeddings = await asyncio.to_thread(
                    self.embedding_model.embed_documents,
                    valid_texts
                )
            else:
                # Fallback: use single embedding method for each text
                embeddings = []
                for text in valid_texts:
                    if hasattr(self.embedding_model, 'embed'):
                        emb = await asyncio.to_thread(self.embedding_model.embed, text)
                    else:
                        emb = await asyncio.to_thread(self.embedding_model.embed_query, text)
                    embeddings.append(emb)
            
            # Convert numpy arrays to lists if needed
            if embeddings is not None:
                # Handle numpy array or similar structures
                if hasattr(embeddings, 'tolist'):
                    embeddings = embeddings.tolist()
                elif isinstance(embeddings, (list, tuple)):
                    # Ensure each embedding is also converted if needed
                    embeddings = [emb.tolist() if hasattr(emb, 'tolist') else emb for emb in embeddings]
                
                logger.info(f"Generated {len(embeddings)} embeddings")
                return embeddings
            else:
                logger.error("No embeddings returned from batch processing")
                return []
            
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {str(e)}")
            return []
    
    async def embed_document(self, document_id: int, force_update: bool = False) -> bool:
        """
        Generate and store embedding for a document
        
        Args:
            document_id: ID of the document to embed
            force_update: Whether to regenerate existing embeddings
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get document
            stmt = select(Document).where(Document.id == document_id)
            result = await self.session.execute(stmt)
            document = result.scalar_one_or_none()
            
            if not document:
                logger.error(f"Document {document_id} not found")
                return False
            
            # Check if embedding already exists
            if document.embedding and not force_update:
                logger.debug(f"Document {document_id} already has embedding, skipping")
                return True
            
            if not document.content:
                logger.warning(f"Document {document_id} has no content to embed")
                return False
            
            # Generate embedding
            embedding = await self.embed_text(document.content)
            if not embedding:
                logger.error(f"Failed to generate embedding for document {document_id}")
                return False
            
            # Update document with embedding
            document.embedding = embedding
            await self.session.commit()
            
            logger.info(f"Successfully embedded document {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error embedding document {document_id}: {str(e)}")
            await self.session.rollback()
            return False
    
    async def embed_document_chunks(self, document_id: int, force_update: bool = False) -> bool:
        """
        Generate and store embeddings for all chunks of a document
        
        Args:
            document_id: ID of the document whose chunks to embed
            force_update: Whether to regenerate existing embeddings
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get document and its chunks
            stmt = (select(Document)
                   .where(Document.id == document_id))
            result = await self.session.execute(stmt)
            document = result.scalar_one_or_none()
            
            if not document:
                logger.error(f"Document {document_id} not found")
                return False
            
            # Get chunks
            chunks_stmt = select(Chunk).where(Chunk.document_id == document_id)
            chunks_result = await self.session.execute(chunks_stmt)
            chunks = chunks_result.scalars().all()
            
            if not chunks:
                logger.warning(f"No chunks found for document {document_id}")
                return True
            
            # Filter chunks that need embedding
            chunks_to_embed = []
            for chunk in chunks:
                if not chunk.embedding or force_update:
                    if chunk.content and chunk.content.strip():
                        chunks_to_embed.append(chunk)
            
            if not chunks_to_embed:
                logger.debug(f"All chunks for document {document_id} already have embeddings")
                return True
            
            # Generate embeddings in batch
            texts = [chunk.content for chunk in chunks_to_embed]
            embeddings = await self.embed_texts(texts)
            
            if len(embeddings) != len(chunks_to_embed):
                logger.error(f"Mismatch in embeddings count: got {len(embeddings)}, expected {len(chunks_to_embed)}")
                return False
            
            # Update chunks with embeddings
            for chunk, embedding in zip(chunks_to_embed, embeddings):
                if embedding:  # Only update if we got a valid embedding
                    chunk.embedding = embedding
            
            await self.session.commit()
            
            logger.info(f"Successfully embedded {len(chunks_to_embed)} chunks for document {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error embedding chunks for document {document_id}: {str(e)}")
            await self.session.rollback()
            return False
    
    async def create_and_embed_chunks(self, document: Document) -> bool:
        """
        Create chunks from document content and embed them
        
        Args:
            document: Document to chunk and embed
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not document.content:
                logger.warning(f"Document {document.id} has no content to chunk")
                return False
            
            # Create chunks using the configured chunker
            if hasattr(self.chunker, 'chunk'):
                chunk_texts = await asyncio.to_thread(
                    self.chunker.chunk,
                    document.content
                )
            elif callable(self.chunker):
                chunk_texts = await asyncio.to_thread(
                    self.chunker,
                    document.content
                )
            else:
                raise ValueError(f"Unknown chunker interface: {type(self.chunker)}")
            
            if not chunk_texts:
                logger.warning(f"No chunks created for document {document.id}")
                return False
            
            # Generate embeddings for all chunks
            embeddings = await self.embed_texts(chunk_texts)
            
            if len(embeddings) != len(chunk_texts):
                logger.error(f"Mismatch in chunk embeddings: got {len(embeddings)}, expected {len(chunk_texts)}")
                # Continue with partial embeddings rather than failing completely
            
            # Create chunk records
            chunks_created = 0
            for i, (chunk_text, embedding) in enumerate(zip(chunk_texts, embeddings)):
                if embedding:  # Only create chunk if we have a valid embedding
                    chunk = Chunk(
                        content=chunk_text,
                        embedding=embedding,
                        document_id=document.id
                    )
                    self.session.add(chunk)
                    chunks_created += 1
            
            await self.session.commit()
            
            logger.info(f"Created and embedded {chunks_created} chunks for document {document.id}")
            return chunks_created > 0
            
        except Exception as e:
            logger.error(f"Error creating and embedding chunks for document {document.id}: {str(e)}")
            await self.session.rollback()
            return False
    
    async def populate_missing_embeddings(self, limit: Optional[int] = None) -> dict:
        """
        Populate embeddings for documents and chunks that don't have them
        
        Args:
            limit: Maximum number of documents to process (None for all)
            
        Returns:
            Dict with statistics about the operation
        """
        stats = {
            "documents_processed": 0,
            "documents_embedded": 0,
            "chunks_created": 0,
            "chunks_embedded": 0,
            "errors": 0
        }
        
        try:
            # Get documents without embeddings
            stmt = select(Document).where(Document.embedding.is_(None))
            if limit:
                stmt = stmt.limit(limit)
            
            result = await self.session.execute(stmt)
            documents = result.scalars().all()
            
            logger.info(f"Found {len(documents)} documents without embeddings")
            
            for document in documents:
                stats["documents_processed"] += 1
                
                try:
                    # Embed the document itself
                    if await self.embed_document(document.id):
                        stats["documents_embedded"] += 1
                    
                    # Check if document has chunks
                    chunks_stmt = select(Chunk).where(Chunk.document_id == document.id)
                    chunks_result = await self.session.execute(chunks_stmt)
                    existing_chunks = chunks_result.scalars().all()
                    
                    if not existing_chunks:
                        # Create and embed chunks
                        if await self.create_and_embed_chunks(document):
                            # Count the chunks we just created
                            new_chunks_stmt = select(Chunk).where(Chunk.document_id == document.id)
                            new_chunks_result = await self.session.execute(new_chunks_stmt)
                            new_chunks = new_chunks_result.scalars().all()
                            stats["chunks_created"] += len(new_chunks)
                    else:
                        # Embed existing chunks that don't have embeddings
                        if await self.embed_document_chunks(document.id):
                            chunks_embedded = len([c for c in existing_chunks if not c.embedding])
                            stats["chunks_embedded"] += chunks_embedded
                    
                except Exception as e:
                    logger.error(f"Error processing document {document.id}: {str(e)}")
                    stats["errors"] += 1
                    continue
            
            return stats
            
        except Exception as e:
            logger.error(f"Error in populate_missing_embeddings: {str(e)}")
            stats["errors"] += 1
            return stats
    
    def get_embedding_stats(self) -> dict:
        """Get statistics about embeddings in the database"""
        return {
            "embedding_model": config.EMBEDDING_MODEL,
            "embedding_dimension": getattr(config.embedding_model_instance, 'dimension', 'unknown'),
            "chunker_type": type(config.chunker_instance).__name__
        }