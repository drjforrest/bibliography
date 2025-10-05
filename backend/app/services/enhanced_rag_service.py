"""
Enhanced RAG Service that integrates the working AI Document Assistant pipeline
with the Bibliography app's database and semantic search capabilities.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload

from langchain.chains import RetrievalQA
from langchain_community.vectorstores import FAISS
from langchain_community.llms import Ollama
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.schema import Document as LangChainDocument

from app.db import ScientificPaper, Document, SearchSpace, Chunk
from app.config import config

logger = logging.getLogger(__name__)


class EnhancedRAGService:
    """
    Enhanced RAG service that combines:
    1. Working FAISS vector store with HuggingFace embeddings
    2. Bibliography app's database structure
    3. Ollama LLM for question answering
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.embeddings = None
        self.vectorstore = None
        self.llm = None
        self.qa_chain = None
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize the embedding model, LLM, and create empty vector store."""
        try:
            # Initialize embedding model (same as working pipeline)
            logger.info("Loading HuggingFace embedding model: all-MiniLM-L6-v2")
            self.embeddings = HuggingFaceEmbeddings(
                model_name="all-MiniLM-L6-v2",
                model_kwargs={"device": "cpu"}
            )
            
            # Initialize LLM (Ollama)
            logger.info("Connecting to Ollama LLM: mistral")
            self.llm = Ollama(
                model="mistral", 
                base_url="http://localhost:11434"
            )
            
            logger.info("Enhanced RAG Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Enhanced RAG Service: {e}")
            raise
    
    async def build_vector_store_from_papers(self, user_id: str, search_space_id: Optional[int] = None) -> bool:
        """
        Build FAISS vector store from scientific papers in the database.
        
        Args:
            user_id: User ID to filter papers
            search_space_id: Optional search space filter
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Building vector store for user {user_id}")
            
            # Get papers from database
            query_conditions = []
            
            # Build query to get papers with their documents
            papers_stmt = select(ScientificPaper).options(
                joinedload(ScientificPaper.document)
            ).join(
                Document, ScientificPaper.document_id == Document.id
            ).join(
                SearchSpace, Document.search_space_id == SearchSpace.id
            ).where(
                SearchSpace.user_id == user_id
            )
            
            if search_space_id:
                papers_stmt = papers_stmt.where(Document.search_space_id == search_space_id)
            
            result = await self.session.execute(papers_stmt)
            papers = result.scalars().all()
            
            if not papers:
                logger.warning("No papers found to build vector store")
                return False
            
            # Prepare documents for FAISS
            documents = []
            
            for paper in papers:
                if not paper.document or not paper.document.content:
                    continue
                
                # Create content for embedding
                content_parts = []
                if paper.title:
                    content_parts.append(f"Title: {paper.title}")
                if paper.abstract:
                    content_parts.append(f"Abstract: {paper.abstract}")
                if paper.authors:
                    content_parts.append(f"Authors: {', '.join(paper.authors)}")
                if paper.keywords:
                    content_parts.append(f"Keywords: {', '.join(paper.keywords)}")
                
                # Add document content (truncated for efficiency)
                content_parts.append(paper.document.content[:2000])
                
                full_content = "\n\n".join(content_parts)
                
                # Create LangChain document with metadata
                doc = LangChainDocument(
                    page_content=full_content,
                    metadata={
                        "paper_id": paper.id,
                        "document_id": paper.document_id,
                        "title": paper.title or "Unknown",
                        "authors": paper.authors or [],
                        "journal": paper.journal,
                        "publication_year": paper.publication_year,
                        "doi": paper.doi,
                        "confidence_score": paper.confidence_score or 0.0,
                        "file_path": paper.file_path
                    }
                )
                documents.append(doc)
            
            if not documents:
                logger.warning("No valid documents found for vector store")
                return False
            
            # Create FAISS vector store
            logger.info(f"Creating FAISS vector store with {len(documents)} documents")
            self.vectorstore = FAISS.from_documents(
                documents=documents,
                embedding=self.embeddings
            )
            
            # Create QA chain
            self.qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=self.vectorstore.as_retriever(search_kwargs={"k": 5}),
                return_source_documents=True,
            )
            
            logger.info(f"Successfully built vector store with {len(documents)} documents")
            return True
            
        except Exception as e:
            logger.error(f"Error building vector store: {str(e)}")
            return False
    
    async def semantic_search(
        self,
        query: str,
        user_id: str,
        search_space_id: Optional[int] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Perform enhanced semantic search using FAISS vector store.
        
        Args:
            query: Search query
            user_id: User performing search
            search_space_id: Optional search space filter
            limit: Number of results to return
            
        Returns:
            Dictionary with enhanced search results
        """
        try:
            # Build vector store if not exists
            if not self.vectorstore:
                success = await self.build_vector_store_from_papers(user_id, search_space_id)
                if not success:
                    return {
                        "query": query,
                        "total_results": 0,
                        "results": [],
                        "error": "No vector store available"
                    }
            
            # Perform similarity search
            docs_with_scores = self.vectorstore.similarity_search_with_score(query, k=limit)
            
            # Format results
            results = []
            for doc, score in docs_with_scores:
                metadata = doc.metadata
                
                result = {
                    "paper_id": metadata.get("paper_id"),
                    "document_id": metadata.get("document_id"),
                    "title": metadata.get("title"),
                    "authors": metadata.get("authors", []),
                    "journal": metadata.get("journal"),
                    "publication_year": metadata.get("publication_year"),
                    "doi": metadata.get("doi"),
                    "confidence_score": metadata.get("confidence_score", 0.0),
                    "similarity_score": float(1 - score),  # Convert distance to similarity
                    "content_preview": doc.page_content[:300] + "..." if len(doc.page_content) > 300 else doc.page_content,
                    "file_path": metadata.get("file_path")
                }
                results.append(result)
            
            # Generate insights
            insights = self._generate_search_insights(results, query)
            
            return {
                "query": query,
                "search_type": "enhanced_semantic",
                "total_results": len(results),
                "results": results,
                "insights": insights,
                "search_metadata": {
                    "user_id": user_id,
                    "search_space_id": search_space_id,
                    "vector_store": "FAISS",
                    "embedding_model": "all-MiniLM-L6-v2"
                }
            }
            
        except Exception as e:
            logger.error(f"Error in enhanced semantic search: {str(e)}")
            return {
                "query": query,
                "total_results": 0,
                "results": [],
                "error": str(e)
            }
    
    async def ask_question(
        self,
        question: str,
        user_id: str,
        search_space_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Ask a question about the research papers using RAG.
        
        Args:
            question: Question to ask
            user_id: User asking the question
            search_space_id: Optional search space filter
            
        Returns:
            Dictionary with answer and sources
        """
        try:
            # Build vector store if not exists
            if not self.qa_chain:
                success = await self.build_vector_store_from_papers(user_id, search_space_id)
                if not success:
                    return {
                        "question": question,
                        "answer": "No research papers available to answer questions. Please upload and process some papers first.",
                        "sources": [],
                        "error": "No vector store available"
                    }
            
            # Get answer with source documents
            logger.info(f"Processing question: {question[:50]}...")
            result = self.qa_chain({"query": question})
            answer = result["result"]
            source_docs = result.get("source_documents", [])
            
            # Format sources
            sources = []
            seen_papers = set()
            
            for doc in source_docs:
                metadata = doc.metadata
                paper_id = metadata.get("paper_id")
                
                if paper_id and paper_id not in seen_papers:
                    source = {
                        "paper_id": paper_id,
                        "title": metadata.get("title", "Unknown"),
                        "authors": metadata.get("authors", []),
                        "journal": metadata.get("journal"),
                        "publication_year": metadata.get("publication_year"),
                        "doi": metadata.get("doi"),
                        "relevance_snippet": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
                    }
                    sources.append(source)
                    seen_papers.add(paper_id)
            
            logger.info("Question processed successfully")
            
            return {
                "question": question,
                "answer": answer,
                "sources": sources,
                "metadata": {
                    "user_id": user_id,
                    "search_space_id": search_space_id,
                    "num_sources": len(sources),
                    "model": "mistral"
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing question: {str(e)}")
            return {
                "question": question,
                "answer": f"Error processing question: {str(e)}",
                "sources": [],
                "error": str(e)
            }
    
    async def add_paper_to_vector_store(self, paper: ScientificPaper):
        """
        Add a single paper to the existing vector store.
        
        Args:
            paper: ScientificPaper instance to add
        """
        try:
            if not paper.document or not paper.document.content:
                logger.warning(f"Skipping paper {paper.id} - no content available")
                return
            
            # Create content for embedding
            content_parts = []
            if paper.title:
                content_parts.append(f"Title: {paper.title}")
            if paper.abstract:
                content_parts.append(f"Abstract: {paper.abstract}")
            if paper.authors:
                content_parts.append(f"Authors: {', '.join(paper.authors)}")
            if paper.keywords:
                content_parts.append(f"Keywords: {', '.join(paper.keywords)}")
            
            # Add document content (truncated for efficiency)
            content_parts.append(paper.document.content[:2000])
            
            full_content = "\n\n".join(content_parts)
            
            # Create LangChain document
            doc = LangChainDocument(
                page_content=full_content,
                metadata={
                    "paper_id": paper.id,
                    "document_id": paper.document_id,
                    "title": paper.title or "Unknown",
                    "authors": paper.authors or [],
                    "journal": paper.journal,
                    "publication_year": paper.publication_year,
                    "doi": paper.doi,
                    "confidence_score": paper.confidence_score or 0.0,
                    "file_path": paper.file_path
                }
            )
            
            # Add to vector store
            if self.vectorstore:
                self.vectorstore.add_documents([doc])
                logger.info(f"Added paper {paper.id} to vector store")
            else:
                logger.warning("No vector store available - cannot add paper")
                
        except Exception as e:
            logger.error(f"Error adding paper {paper.id} to vector store: {str(e)}")
    
    def _generate_search_insights(self, results: List[Dict], query: str) -> Dict[str, Any]:
        """Generate insights from search results."""
        if not results:
            return {
                "total_papers": 0,
                "avg_similarity": 0.0,
                "top_journals": [],
                "publication_years": [],
                "top_authors": []
            }
        
        # Calculate insights
        total_papers = len(results)
        avg_similarity = sum(r.get("similarity_score", 0.0) for r in results) / total_papers
        
        # Top journals
        journals = [r.get("journal") for r in results if r.get("journal")]
        journal_counts = {}
        for journal in journals:
            journal_counts[journal] = journal_counts.get(journal, 0) + 1
        top_journals = sorted(journal_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Publication years
        years = [r.get("publication_year") for r in results if r.get("publication_year")]
        year_counts = {}
        for year in years:
            year_counts[year] = year_counts.get(year, 0) + 1
        publication_years = sorted(year_counts.items(), key=lambda x: x[0], reverse=True)[:10]
        
        # Top authors
        all_authors = []
        for result in results:
            if result.get("authors"):
                all_authors.extend(result["authors"])
        author_counts = {}
        for author in all_authors:
            author_counts[author] = author_counts.get(author, 0) + 1
        top_authors = sorted(author_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "total_papers": total_papers,
            "avg_similarity": round(avg_similarity, 3),
            "top_journals": top_journals,
            "publication_years": publication_years,
            "top_authors": top_authors
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the RAG system."""
        try:
            stats = {
                "status": "active" if self.vectorstore else "no_vector_store",
                "embedding_model": "all-MiniLM-L6-v2",
                "llm_model": "mistral",
                "vector_store_type": "FAISS",
                "documents_indexed": 0
            }
            
            if self.vectorstore:
                stats["documents_indexed"] = self.vectorstore.index.ntotal if hasattr(self.vectorstore, "index") else 0
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting RAG stats: {str(e)}")
            return {"status": "error", "error": str(e)}