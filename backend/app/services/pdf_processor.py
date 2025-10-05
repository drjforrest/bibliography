import hashlib
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import fitz  # PyMuPDF
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class PDFProcessor:
    """Service for processing PDF files and extracting metadata for scientific papers."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        
    async def process_pdf(self, file_path: str) -> Dict:
        """
        Process a PDF file and extract all relevant information for scientific papers.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Dictionary containing extracted information
        """
        try:
            # Check if file exists and is readable
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"PDF file not found: {file_path}")
                
            # Calculate file hash for deduplication
            file_hash = self._calculate_file_hash(file_path)
            file_size = os.path.getsize(file_path)
            
            # Open PDF document
            doc = fitz.open(file_path)
            
            # Extract basic metadata
            metadata = doc.metadata
            
            # Extract full text
            full_text = self._extract_full_text(doc)
            
            # Extract title (try multiple methods)
            title = self._extract_title(doc, metadata, full_text)
            
            # Extract authors
            authors = self._extract_authors(doc, metadata, full_text)
            
            # Extract abstract
            abstract = self._extract_abstract(full_text)
            
            # Extract DOI
            doi = self._extract_doi(full_text, metadata)
            
            # Extract publication year
            pub_year = self._extract_publication_year(metadata, full_text)
            
            # Extract journal information
            journal_info = self._extract_journal_info(full_text, metadata)
            
            # Extract keywords
            keywords = self._extract_keywords(full_text)
            
            # Extract references (basic implementation)
            references = self._extract_references(full_text)
            
            # Get page count before closing
            page_count = len(doc)
            
            # Close the document
            doc.close()
            
            return {
                'title': title,
                'authors': authors,
                'journal': journal_info.get('journal'),
                'volume': journal_info.get('volume'),
                'issue': journal_info.get('issue'),
                'pages': journal_info.get('pages'),
                'publication_year': pub_year,
                'doi': doi,
                'abstract': abstract,
                'keywords': keywords,
                'full_text': full_text,
                'file_path': file_path,
                'file_size': file_size,
                'file_hash': file_hash,
                'references': references,
                'extraction_metadata': {
                    'processed_at': datetime.utcnow().isoformat(),
                    'pdf_pages': page_count,
                    'pdf_metadata': metadata,
                    'extraction_confidence': self._calculate_confidence_score(title, authors, abstract)
                },
                'processing_status': 'completed'
            }
            
        except Exception as e:
            logger.error(f"Error processing PDF {file_path}: {str(e)}")
            return {
                'file_path': file_path,
                'processing_status': 'failed',
                'extraction_metadata': {
                    'error': str(e),
                    'processed_at': datetime.utcnow().isoformat()
                }
            }
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of the file for deduplication."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    def _extract_full_text(self, doc: fitz.Document) -> str:
        """Extract full text from all pages of the PDF."""
        full_text = ""
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text()
            # Clean null bytes and other problematic characters for PostgreSQL
            text = text.replace('\x00', '').replace('\ufffd', '')
            full_text += f"\n--- Page {page_num + 1} ---\n{text}\n"
        # Final cleanup of null bytes and replacement characters
        return full_text.replace('\x00', '').replace('\ufffd', '').strip()
    
    def _extract_title(self, doc: fitz.Document, metadata: Dict, full_text: str) -> Optional[str]:
        """Extract title from PDF using multiple strategies."""
        # Strategy 1: PDF metadata
        if metadata.get('title'):
            title = metadata['title'].strip()
            if len(title) > 10:  # Basic validation
                return title
        
        # Strategy 2: Extract from first page (common pattern)
        first_page = doc.load_page(0)
        first_page_text = first_page.get_text()
        
        # Look for title in first few lines (usually largest font)
        lines = first_page_text.split('\n')[:10]
        for line in lines:
            line = line.strip()
            if len(line) > 20 and len(line) < 200:  # Reasonable title length
                # Check if it looks like a title (no weird characters, proper capitalization)
                if re.match(r'^[A-Z].*[a-zA-Z].*$', line) and not re.search(r'^\d+$|^Page \d+|^Abstract|^Introduction', line):
                    return line
        
        # Strategy 3: Look for common title patterns in full text
        title_patterns = [
            r'^([A-Z][^.\n]*?[a-zA-Z][^.\n]*?)(?:\n|Abstract|ABSTRACT)',
            r'Title:\s*(.+?)(?:\n|Author)',
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, full_text, re.MULTILINE | re.IGNORECASE)
            if match:
                title = match.group(1).strip()
                if 20 <= len(title) <= 200:
                    return title
        
        return None
    
    def _extract_authors(self, doc: fitz.Document, metadata: Dict, full_text: str) -> List[str]:
        """Extract authors from PDF."""
        authors = []
        
        # Strategy 1: PDF metadata
        if metadata.get('author'):
            author_str = metadata['author'].strip()
            if author_str:
                # Split by common separators
                authors = re.split(r',|;|\sand\s|\n', author_str)
                authors = [a.strip() for a in authors if a.strip()]
        
        # Strategy 2: Extract from first page text
        if not authors:
            first_page = doc.load_page(0)
            first_page_text = first_page.get_text()
            
            # Look for author patterns
            author_patterns = [
                r'Authors?:\s*(.+?)(?:\n\n|\n[A-Z])',
                r'By:\s*(.+?)(?:\n\n|\n[A-Z])',
                r'^\s*([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*(?:\n|,|\sand\s)',
            ]
            
            for pattern in author_patterns:
                matches = re.finditer(pattern, first_page_text, re.MULTILINE)
                for match in matches:
                    author_text = match.group(1).strip()
                    # Split multiple authors
                    potential_authors = re.split(r',|\sand\s|;', author_text)
                    for author in potential_authors:
                        author = author.strip()
                        if self._is_valid_author_name(author):
                            authors.append(author)
        
        return authors[:10]  # Limit to reasonable number
    
    async def extract_text_from_file(self, file_path: str) -> str:
        """Extract text from PDF file - wrapper for sync service compatibility"""
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"PDF file not found: {file_path}")
            
            doc = fitz.open(file_path)
            full_text = self._extract_full_text(doc)
            doc.close()
            return full_text
            
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {str(e)}")
            return ""
    
    async def extract_metadata(self, file_path: str) -> Dict:
        """Extract metadata from PDF file - wrapper for sync service compatibility"""
        try:
            result = await self.process_pdf(file_path)
            
            # Return simplified metadata format expected by sync service
            return {
                'title': result.get('title'),
                'authors': result.get('authors', []),
                'doi': result.get('doi'),
                'abstract': result.get('abstract'),
                'publication_year': result.get('publication_year'),
                'publication_date': None,  # Would need date parsing from year
                'journal': result.get('journal'),
                'keywords': result.get('keywords', []),
                'confidence_score': result.get('extraction_metadata', {}).get('extraction_confidence')
            }
            
        except Exception as e:
            logger.error(f"Error extracting metadata from {file_path}: {str(e)}")
            return {}
    
    def _is_valid_author_name(self, name: str) -> bool:
        """Check if a string looks like a valid author name."""
        # Basic validation for author names
        if not name or len(name) < 3 or len(name) > 50:
            return False
        # Should contain letters and reasonable characters
        if not re.match(r'^[A-Za-z\s\.-]+$', name):
            return False
        # Should have at least two words (first and last name)
        if len(name.split()) < 2:
            return False
        return True
    
    def _extract_abstract(self, full_text: str) -> Optional[str]:
        """Extract abstract from the paper."""
        # Look for abstract section
        abstract_patterns = [
            r'ABSTRACT\s*\n(.*?)(?:\n\s*\n|\n\s*1\.\s|Keywords?:|\nINTRODUCTION)',
            r'Abstract\s*\n(.*?)(?:\n\s*\n|\n\s*1\.\s|Keywords?:|\nIntroduction)',
            r'Abstract:\s*(.*?)(?:\n\s*\n|\n\s*1\.\s|Keywords?:|\nIntroduction)',
        ]
        
        for pattern in abstract_patterns:
            match = re.search(pattern, full_text, re.DOTALL | re.IGNORECASE)
            if match:
                abstract = match.group(1).strip()
                # Clean up the abstract
                abstract = re.sub(r'\n+', ' ', abstract)
                abstract = re.sub(r'\s+', ' ', abstract)
                if 50 <= len(abstract) <= 2000:  # Reasonable abstract length
                    return abstract
        
        return None
    
    def _extract_doi(self, full_text: str, metadata: Dict) -> Optional[str]:
        """Extract DOI from the paper."""
        # DOI patterns
        doi_patterns = [
            r'DOI:\s*(10\.\d+/[^\s\n]+)',
            r'doi:\s*(10\.\d+/[^\s\n]+)',
            r'https?://(?:dx\.)?doi\.org/(10\.\d+/[^\s\n]+)',
            r'\b(10\.\d+/[^\s\n]+)\b',
        ]
        
        for pattern in doi_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                doi = match.group(1).strip()
                # Validate DOI format
                if re.match(r'^10\.\d+/.+', doi):
                    return doi
        
        return None
    
    def _extract_publication_year(self, metadata: Dict, full_text: str) -> Optional[int]:
        """Extract publication year."""
        # Check PDF creation date
        if metadata.get('creationDate'):
            try:
                # PyMuPDF date format: "D:20210315093000+00'00'"
                date_str = metadata['creationDate']
                if date_str.startswith('D:'):
                    year_str = date_str[2:6]
                    year = int(year_str)
                    if 1900 <= year <= datetime.now().year + 1:
                        return year
            except (ValueError, IndexError):
                pass
        
        # Look for year in text (first few pages)
        first_part = full_text[:2000]  # First 2000 characters
        year_pattern = r'\b(20[0-2]\d|19[7-9]\d)\b'
        matches = re.findall(year_pattern, first_part)
        
        if matches:
            # Return the most recent reasonable year
            years = [int(match) for match in matches]
            years = [y for y in years if 1950 <= y <= datetime.now().year + 1]
            if years:
                return max(years)
        
        return None
    
    def _extract_journal_info(self, full_text: str, metadata: Dict) -> Dict:
        """Extract journal, volume, issue, and pages information."""
        journal_info = {
            'journal': None,
            'volume': None,
            'issue': None,
            'pages': None
        }
        
        # Look for journal patterns in first page
        first_part = full_text[:1000]
        
        # Journal patterns
        journal_patterns = [
            r'Journal of ([^,\n]+)',
            r'([A-Z][a-z]+ [A-Z][a-z]+ Journal)',
            r'Proceedings of ([^,\n]+)',
            r'([A-Z][a-z]+ Review)',
        ]
        
        for pattern in journal_patterns:
            match = re.search(pattern, first_part, re.IGNORECASE)
            if match:
                journal = match.group(1).strip()
                if 3 <= len(journal) <= 100:
                    journal_info['journal'] = journal
                    break
        
        # Volume, Issue, Pages patterns
        vol_issue_patterns = [
            r'Vol\.?\s*(\d+),?\s*(?:No\.?\s*(\d+))?,?\s*(?:pp\.?\s*([\d-]+))?',
            r'Volume\s*(\d+),?\s*(?:Issue\s*(\d+))?,?\s*(?:Pages?\s*([\d-]+))?',
        ]
        
        for pattern in vol_issue_patterns:
            match = re.search(pattern, first_part, re.IGNORECASE)
            if match:
                if match.group(1):
                    journal_info['volume'] = match.group(1)
                if match.group(2):
                    journal_info['issue'] = match.group(2)
                if match.group(3):
                    journal_info['pages'] = match.group(3)
                break
        
        return journal_info
    
    def _extract_keywords(self, full_text: str) -> List[str]:
        """Extract keywords from the paper."""
        keywords = []
        
        # Look for keywords section
        keyword_patterns = [
            r'Keywords?:\s*([^\n]+)',
            r'Key words?:\s*([^\n]+)',
            r'Index terms?:\s*([^\n]+)',
        ]
        
        for pattern in keyword_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                keyword_text = match.group(1).strip()
                # Split keywords by common separators
                keywords = re.split(r',|;|\n', keyword_text)
                keywords = [k.strip().lower() for k in keywords if k.strip()]
                # Limit to reasonable number and length
                keywords = [k for k in keywords if 2 <= len(k) <= 30][:20]
                break
        
        return keywords
    
    def _extract_references(self, full_text: str) -> List[Dict]:
        """Extract references (basic implementation)."""
        references = []
        
        # Look for references section
        ref_patterns = [
            r'REFERENCES\s*\n(.*?)$',
            r'References\s*\n(.*?)$',
            r'BIBLIOGRAPHY\s*\n(.*?)$',
        ]
        
        for pattern in ref_patterns:
            match = re.search(pattern, full_text, re.DOTALL | re.IGNORECASE)
            if match:
                ref_text = match.group(1)
                # Split references by numbers or patterns
                ref_entries = re.split(r'\n\s*\[\d+\]|\n\s*\d+\.', ref_text)
                
                for ref in ref_entries[:50]:  # Limit number of references
                    ref = ref.strip()
                    if len(ref) > 20:  # Reasonable reference length
                        references.append({
                            'raw_text': ref,
                            'extracted_at': datetime.utcnow().isoformat()
                        })
                break
        
        return references
    
    def _calculate_confidence_score(self, title: Optional[str], authors: List[str], abstract: Optional[str]) -> float:
        """Calculate confidence score for extraction quality."""
        score = 0.0
        
        # Title score (40% weight)
        if title and len(title) > 10:
            score += 0.4
        
        # Authors score (30% weight)
        if authors:
            score += 0.3 * min(len(authors) / 5, 1.0)  # Up to 5 authors give full score
        
        # Abstract score (30% weight)
        if abstract and len(abstract) > 50:
            score += 0.3
        
        return round(score, 2)