import logging
from typing import Dict, List, Optional, Any
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db import ScientificPaper, Document, SearchSpace, Chunk
from app.config import config
from app.retriver.documents_hybrid_search import DocumentHybridSearchRetriever

logger = logging.getLogger(__name__)


class SemanticSearchService:
    """Enhanced semantic search service specifically for scientific papers."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.document_retriever = DocumentHybridSearchRetriever(session)
    
    async def semantic_paper_search(
        self,
        query: str,
        user_id: str,
        search_space_id: Optional[int] = None,
        search_type: str = "hybrid",
        limit: int = 10,
        min_confidence: float = 0.0,
        include_abstracts: bool = True
    ) -> Dict[str, Any]:
        """
        Perform semantic search on scientific papers with enhanced results.
        
        Args:
            query: Search query
            user_id: User performing search
            search_space_id: Optional search space filter
            search_type: 'semantic', 'keyword', or 'hybrid'
            limit: Number of results to return
            min_confidence: Minimum extraction confidence score
            include_abstracts: Whether to search in abstracts as well
            
        Returns:
            Dictionary with search results and metadata
        """
        try:
            # Build the query based on search type
            if search_type == "semantic":
                results = await self._semantic_search(query, user_id, search_space_id, limit)
            elif search_type == "keyword":
                results = await self._keyword_search(query, user_id, search_space_id, limit)
            else:  # hybrid
                results = await self._hybrid_search(query, user_id, search_space_id, limit)
            
            # Filter by confidence if specified
            if min_confidence > 0.0:
                results = [r for r in results if r.get("paper_confidence", 0.0) >= min_confidence]
            
            # Enhance results with paper-specific information
            enhanced_results = await self._enhance_paper_results(results, include_abstracts)
            
            # Generate search insights
            insights = await self._generate_search_insights(enhanced_results, query)
            
            return {
                "query": query,
                "search_type": search_type,
                "total_results": len(enhanced_results),
                "results": enhanced_results,
                "insights": insights,
                "search_metadata": {
                    "user_id": user_id,
                    "search_space_id": search_space_id,
                    "min_confidence": min_confidence,
                    "include_abstracts": include_abstracts
                }
            }
            
        except Exception as e:
            logger.error(f"Error in semantic paper search: {str(e)}")
            raise
    
    async def _semantic_search(self, query: str, user_id: str, search_space_id: Optional[int], limit: int) -> List[Dict]:
        """Perform pure semantic vector search."""
        return await self.document_retriever.vector_search(
            query_text=query,
            top_k=limit,
            user_id=user_id,
            search_space_id=search_space_id
        )
    
    async def _keyword_search(self, query: str, user_id: str, search_space_id: Optional[int], limit: int) -> List[Dict]:
        """Perform pure keyword search."""
        return await self.document_retriever.full_text_search(
            query_text=query,
            top_k=limit,
            user_id=user_id,
            search_space_id=search_space_id
        )
    
    async def _hybrid_search(self, query: str, user_id: str, search_space_id: Optional[int], limit: int) -> List[Dict]:
        """Perform hybrid search combining semantic and keyword."""
        return await self.document_retriever.hybrid_search(
            query_text=query,
            top_k=limit,
            user_id=user_id,
            search_space_id=search_space_id,
            document_type="SCIENTIFIC_PAPER"
        )
    
    async def _enhance_paper_results(self, results: List[Dict], include_abstracts: bool) -> List[Dict]:
        """Enhance search results with scientific paper specific information."""
        if not results:
            return []
        
        enhanced_results = []
        
        for result in results:
            document_id = result.get("document_id")
            if not document_id:
                continue
            
            # Get the scientific paper record
            paper_stmt = select(ScientificPaper).where(ScientificPaper.document_id == document_id)
            paper_result = await self.session.execute(paper_stmt)
            paper = paper_result.scalar_one_or_none()
            
            enhanced_result = {
                **result,
                "paper_confidence": paper.confidence_score if paper else 0.0,
                "paper_info": None
            }
            
            if paper:
                # Build enhanced paper information
                paper_info = {
                    "id": paper.id,
                    "title": paper.title,
                    "authors": paper.authors or [],
                    "journal": paper.journal,
                    "publication_year": paper.publication_year,
                    "doi": paper.doi,
                    "abstract": paper.abstract if include_abstracts else None,
                    "keywords": paper.keywords or [],
                    "subject_areas": paper.subject_areas or [],
                    "confidence_score": paper.confidence_score,
                    "citation_count": paper.citation_count,
                    "is_open_access": paper.is_open_access
                }
                enhanced_result["paper_info"] = paper_info
            
            enhanced_results.append(enhanced_result)
        
        return enhanced_results
    
    async def _generate_search_insights(self, results: List[Dict], query: str) -> Dict[str, Any]:
        """Generate insights from search results."""
        if not results:
            return {
                "total_papers": 0,
                "avg_confidence": 0.0,
                "top_journals": [],
                "publication_years": [],
                "top_authors": [],
                "subject_areas": []
            }
        
        # Extract paper information
        papers = [r["paper_info"] for r in results if r.get("paper_info")]
        
        # Calculate insights
        total_papers = len(papers)
        avg_confidence = sum(p.get("confidence_score", 0.0) for p in papers) / total_papers if total_papers > 0 else 0.0
        
        # Top journals
        journals = [p.get("journal") for p in papers if p.get("journal")]
        journal_counts = {}
        for journal in journals:
            journal_counts[journal] = journal_counts.get(journal, 0) + 1
        top_journals = sorted(journal_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Publication years distribution
        years = [p.get("publication_year") for p in papers if p.get("publication_year")]
        year_counts = {}
        for year in years:
            year_counts[year] = year_counts.get(year, 0) + 1
        publication_years = sorted(year_counts.items(), key=lambda x: x[0], reverse=True)[:10]
        
        # Top authors (flatten author lists)
        all_authors = []
        for paper in papers:
            if paper.get("authors"):
                all_authors.extend(paper["authors"])
        author_counts = {}
        for author in all_authors:
            author_counts[author] = author_counts.get(author, 0) + 1
        top_authors = sorted(author_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Subject areas
        all_subjects = []
        for paper in papers:
            if paper.get("subject_areas"):
                all_subjects.extend(paper["subject_areas"])
        subject_counts = {}
        for subject in all_subjects:
            subject_counts[subject] = subject_counts.get(subject, 0) + 1
        subject_areas = sorted(subject_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "total_papers": total_papers,
            "avg_confidence": round(avg_confidence, 3),
            "avg_search_score": round(sum(r.get("score", 0.0) for r in results) / len(results), 3),
            "top_journals": [{"journal": j, "count": c} for j, c in top_journals],
            "publication_years": [{"year": y, "count": c} for y, c in publication_years],
            "top_authors": [{"author": a, "count": c} for a, c in top_authors],
            "subject_areas": [{"area": s, "count": c} for s, c in subject_areas]
        }
    
    async def similar_papers_search(
        self,
        paper_id: int,
        user_id: str,
        limit: int = 5
    ) -> List[Dict]:
        """
        Find papers similar to a given paper using semantic similarity.
        
        Args:
            paper_id: ID of the reference paper
            user_id: User performing the search
            limit: Number of similar papers to return
            
        Returns:
            List of similar papers with similarity scores
        """
        # Get the reference paper
        paper_stmt = select(ScientificPaper).options(
            joinedload(ScientificPaper.document)
        ).where(ScientificPaper.id == paper_id)
        paper_result = await self.session.execute(paper_stmt)
        paper = paper_result.scalar_one_or_none()
        
        if not paper or not paper.document:
            return []
        
        # Use the paper's content for similarity search
        search_text = ""
        if paper.abstract:
            search_text += paper.abstract + " "
        if paper.title:
            search_text += paper.title + " "
        if paper.keywords:
            search_text += " ".join(paper.keywords)
        
        if not search_text.strip():
            search_text = paper.document.content[:500]  # Use first 500 chars as fallback
        
        # Perform semantic search excluding the original paper
        results = await self.document_retriever.vector_search(
            query_text=search_text,
            top_k=limit + 5,  # Get extra to filter out the original
            user_id=user_id
        )
        
        # Filter out the original paper and enhance results
        similar_papers = []
        for result in results:
            if result.get("document_id") == paper.document_id:
                continue  # Skip the original paper
            
            enhanced_result = await self._enhance_paper_results([result], include_abstracts=True)
            if enhanced_result:
                similar_papers.append(enhanced_result[0])
            
            if len(similar_papers) >= limit:
                break
        
        return similar_papers
    
    async def get_search_suggestions(
        self,
        partial_query: str,
        user_id: str,
        search_space_id: Optional[int] = None,
        limit: int = 5
    ) -> List[str]:
        """
        Get search suggestions based on partial query.
        
        Args:
            partial_query: Partial search query
            user_id: User requesting suggestions
            search_space_id: Optional search space filter
            limit: Number of suggestions to return
            
        Returns:
            List of search suggestions
        """
        if len(partial_query.strip()) < 2:
            return []
        
        # Get suggestions from paper titles and keywords
        suggestions = set()
        
        # Build base query
        base_conditions = [SearchSpace.user_id == user_id]
        if search_space_id:
            base_conditions.append(Document.search_space_id == search_space_id)
        
        # Search in titles
        title_stmt = select(ScientificPaper.title).join(
            Document, ScientificPaper.document_id == Document.id
        ).join(
            SearchSpace, Document.search_space_id == SearchSpace.id
        ).where(
            *base_conditions,
            ScientificPaper.title.ilike(f"%{partial_query}%")
        ).limit(limit * 2)
        
        title_result = await self.session.execute(title_stmt)
        titles = title_result.scalars().all()
        
        for title in titles:
            if title and partial_query.lower() in title.lower():
                suggestions.add(title)
        
        # Search in keywords
        keyword_stmt = select(ScientificPaper.keywords).join(
            Document, ScientificPaper.document_id == Document.id
        ).join(
            SearchSpace, Document.search_space_id == SearchSpace.id
        ).where(
            *base_conditions,
            ScientificPaper.keywords.op("&&")(
                func.array([f"%{partial_query}%"])
            )
        ).limit(limit * 2)
        
        keyword_result = await self.session.execute(keyword_stmt)
        keyword_arrays = keyword_result.scalars().all()
        
        for keyword_array in keyword_arrays:
            if keyword_array:
                for keyword in keyword_array:
                    if keyword and partial_query.lower() in keyword.lower():
                        suggestions.add(keyword)
        
        return list(suggestions)[:limit]