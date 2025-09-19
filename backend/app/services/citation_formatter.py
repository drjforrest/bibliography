from datetime import datetime
from typing import Dict, List, Optional
import re

from app.db import ScientificPaper


class CitationFormatter:
    """Service for formatting citations in different academic styles."""
    
    @staticmethod
    def format_citation(paper: ScientificPaper, style: str = "apa") -> str:
        """
        Format a citation for a scientific paper in the specified style.
        
        Args:
            paper: ScientificPaper object
            style: Citation style ('apa', 'mla', 'chicago', 'ieee', 'harvard')
            
        Returns:
            Formatted citation string
        """
        style = style.lower()
        
        if style == "apa":
            return CitationFormatter._format_apa(paper)
        elif style == "mla":
            return CitationFormatter._format_mla(paper)
        elif style == "chicago":
            return CitationFormatter._format_chicago(paper)
        elif style == "ieee":
            return CitationFormatter._format_ieee(paper)
        elif style == "harvard":
            return CitationFormatter._format_harvard(paper)
        else:
            raise ValueError(f"Unsupported citation style: {style}")
    
    @staticmethod
    def _format_apa(paper: ScientificPaper) -> str:
        """Format citation in APA style."""
        citation_parts = []
        
        # Authors
        if paper.authors:
            if len(paper.authors) == 1:
                # Single author: Last, F. M.
                author = CitationFormatter._format_author_apa(paper.authors[0])
                citation_parts.append(f"{author}.")
            elif len(paper.authors) <= 20:
                # Multiple authors (up to 20): Last, F. M., & Last, F. M.
                formatted_authors = []
                for i, author in enumerate(paper.authors):
                    formatted_author = CitationFormatter._format_author_apa(author)
                    if i == len(paper.authors) - 1 and len(paper.authors) > 1:
                        formatted_authors.append(f"& {formatted_author}")
                    else:
                        formatted_authors.append(formatted_author)
                citation_parts.append(f"{', '.join(formatted_authors)}.")
            else:
                # More than 20 authors: First 19, ..., Last
                formatted_authors = []
                for i in range(19):
                    formatted_authors.append(CitationFormatter._format_author_apa(paper.authors[i]))
                formatted_authors.append("...")
                formatted_authors.append(CitationFormatter._format_author_apa(paper.authors[-1]))
                citation_parts.append(f"{', '.join(formatted_authors)}.")
        
        # Year
        if paper.publication_year:
            citation_parts.append(f"({paper.publication_year}).")
        
        # Title
        if paper.title:
            citation_parts.append(f"{paper.title}.")
        
        # Journal information
        if paper.journal:
            journal_part = f"*{paper.journal}*"
            if paper.volume:
                journal_part += f", *{paper.volume}*"
                if paper.issue:
                    journal_part += f"({paper.issue})"
            if paper.pages:
                journal_part += f", {paper.pages}"
            citation_parts.append(f"{journal_part}.")
        
        # DOI
        if paper.doi:
            citation_parts.append(f"https://doi.org/{paper.doi}")
        
        return " ".join(citation_parts)
    
    @staticmethod
    def _format_mla(paper: ScientificPaper) -> str:
        """Format citation in MLA style."""
        citation_parts = []
        
        # Authors
        if paper.authors:
            if len(paper.authors) == 1:
                # Single author: Last, First
                author_parts = paper.authors[0].split()
                if len(author_parts) >= 2:
                    citation_parts.append(f"{author_parts[-1]}, {' '.join(author_parts[:-1])}.")
                else:
                    citation_parts.append(f"{paper.authors[0]}.")
            else:
                # Multiple authors: Last, First, and First Last
                first_author_parts = paper.authors[0].split()
                if len(first_author_parts) >= 2:
                    first_author = f"{first_author_parts[-1]}, {' '.join(first_author_parts[:-1])}"
                else:
                    first_author = paper.authors[0]
                
                if len(paper.authors) == 2:
                    citation_parts.append(f"{first_author}, and {paper.authors[1]}.")
                else:
                    citation_parts.append(f"{first_author}, et al.")
        
        # Title
        if paper.title:
            citation_parts.append(f'"{paper.title}."')
        
        # Journal information
        if paper.journal:
            journal_part = f"*{paper.journal}*"
            if paper.volume:
                journal_part += f", vol. {paper.volume}"
                if paper.issue:
                    journal_part += f", no. {paper.issue}"
            if paper.publication_year:
                journal_part += f", {paper.publication_year}"
            if paper.pages:
                journal_part += f", pp. {paper.pages}"
            citation_parts.append(f"{journal_part}.")
        
        return " ".join(citation_parts)
    
    @staticmethod
    def _format_chicago(paper: ScientificPaper) -> str:
        """Format citation in Chicago style (Notes-Bibliography)."""
        citation_parts = []
        
        # Authors
        if paper.authors:
            if len(paper.authors) == 1:
                citation_parts.append(f"{paper.authors[0]}.")
            elif len(paper.authors) <= 3:
                authors_str = ", ".join(paper.authors[:-1]) + f", and {paper.authors[-1]}"
                citation_parts.append(f"{authors_str}.")
            else:
                citation_parts.append(f"{paper.authors[0]} et al.")
        
        # Title
        if paper.title:
            citation_parts.append(f'"{paper.title}."')
        
        # Journal information
        if paper.journal:
            journal_part = f"*{paper.journal}*"
            if paper.volume:
                journal_part += f" {paper.volume}"
                if paper.issue:
                    journal_part += f", no. {paper.issue}"
            if paper.publication_year:
                journal_part += f" ({paper.publication_year})"
            if paper.pages:
                journal_part += f": {paper.pages}"
            citation_parts.append(f"{journal_part}.")
        
        # DOI
        if paper.doi:
            citation_parts.append(f"https://doi.org/{paper.doi}.")
        
        return " ".join(citation_parts)
    
    @staticmethod
    def _format_ieee(paper: ScientificPaper) -> str:
        """Format citation in IEEE style."""
        citation_parts = []
        
        # Authors
        if paper.authors:
            if len(paper.authors) <= 6:
                formatted_authors = []
                for author in paper.authors:
                    # IEEE format: F. M. Last
                    parts = author.split()
                    if len(parts) >= 2:
                        initials = ". ".join([part[0] for part in parts[:-1]]) + "."
                        last_name = parts[-1]
                        formatted_authors.append(f"{initials} {last_name}")
                    else:
                        formatted_authors.append(author)
                citation_parts.append(f"{', '.join(formatted_authors)},")
            else:
                # More than 6 authors: First author et al.
                first_author_parts = paper.authors[0].split()
                if len(first_author_parts) >= 2:
                    initials = ". ".join([part[0] for part in first_author_parts[:-1]]) + "."
                    last_name = first_author_parts[-1]
                    citation_parts.append(f"{initials} {last_name} et al.,")
                else:
                    citation_parts.append(f"{paper.authors[0]} et al.,")
        
        # Title
        if paper.title:
            citation_parts.append(f'"{paper.title},"')
        
        # Journal information
        if paper.journal:
            journal_part = f"*{paper.journal}*"
            if paper.volume:
                journal_part += f", vol. {paper.volume}"
                if paper.issue:
                    journal_part += f", no. {paper.issue}"
            if paper.pages:
                journal_part += f", pp. {paper.pages}"
            if paper.publication_year:
                journal_part += f", {paper.publication_year}"
            citation_parts.append(f"{journal_part}.")
        
        return " ".join(citation_parts)
    
    @staticmethod
    def _format_harvard(paper: ScientificPaper) -> str:
        """Format citation in Harvard style."""
        citation_parts = []
        
        # Authors
        if paper.authors:
            if len(paper.authors) == 1:
                citation_parts.append(f"{paper.authors[0]}")
            elif len(paper.authors) <= 3:
                authors_str = ", ".join(paper.authors[:-1]) + f" and {paper.authors[-1]}"
                citation_parts.append(authors_str)
            else:
                citation_parts.append(f"{paper.authors[0]} et al.")
        
        # Year
        if paper.publication_year:
            citation_parts.append(f"({paper.publication_year})")
        
        # Title
        if paper.title:
            citation_parts.append(f"'{paper.title}',")
        
        # Journal information
        if paper.journal:
            journal_part = f"*{paper.journal}*"
            if paper.volume:
                journal_part += f", vol. {paper.volume}"
                if paper.issue:
                    journal_part += f"({paper.issue})"
            if paper.pages:
                journal_part += f", pp. {paper.pages}"
            citation_parts.append(f"{journal_part}.")
        
        return " ".join(citation_parts)
    
    @staticmethod
    def _format_author_apa(author_name: str) -> str:
        """Format author name for APA style: Last, F. M."""
        parts = author_name.strip().split()
        if len(parts) < 2:
            return author_name
        
        last_name = parts[-1]
        first_names = parts[:-1]
        
        # Create initials
        initials = ". ".join([name[0].upper() for name in first_names if name]) + "."
        
        return f"{last_name}, {initials}"
    
    @staticmethod
    def format_bibtex(paper: ScientificPaper) -> str:
        """Format citation as BibTeX entry."""
        # Generate a citation key
        key_parts = []
        if paper.authors:
            # Use first author's last name
            first_author_parts = paper.authors[0].split()
            if first_author_parts:
                key_parts.append(first_author_parts[-1].lower().replace(" ", ""))
        
        if paper.publication_year:
            key_parts.append(str(paper.publication_year))
        
        # Add first significant word from title
        if paper.title:
            title_words = re.findall(r'\b[A-Za-z]{3,}\b', paper.title.lower())
            if title_words:
                key_parts.append(title_words[0])
        
        citation_key = "".join(key_parts) if key_parts else "unknown"
        
        bibtex_parts = [f"@article{{{citation_key},"]
        
        if paper.title:
            bibtex_parts.append(f'  title={{{paper.title}}},')
        
        if paper.authors:
            authors_str = " and ".join(paper.authors)
            bibtex_parts.append(f'  author={{{authors_str}}},')
        
        if paper.journal:
            bibtex_parts.append(f'  journal={{{paper.journal}}},')
        
        if paper.volume:
            bibtex_parts.append(f'  volume={{{paper.volume}}},')
        
        if paper.issue:
            bibtex_parts.append(f'  number={{{paper.issue}}},')
        
        if paper.pages:
            bibtex_parts.append(f'  pages={{{paper.pages}}},')
        
        if paper.publication_year:
            bibtex_parts.append(f'  year={{{paper.publication_year}}},')
        
        if paper.doi:
            bibtex_parts.append(f'  doi={{{paper.doi}}},')
        
        bibtex_parts.append("}")
        
        return "\n".join(bibtex_parts)
    
    @staticmethod
    def get_available_styles() -> List[Dict[str, str]]:
        """Get list of available citation styles."""
        return [
            {"code": "apa", "name": "APA (American Psychological Association)"},
            {"code": "mla", "name": "MLA (Modern Language Association)"},
            {"code": "chicago", "name": "Chicago (Notes-Bibliography)"},
            {"code": "ieee", "name": "IEEE (Institute of Electrical and Electronics Engineers)"},
            {"code": "harvard", "name": "Harvard"},
            {"code": "bibtex", "name": "BibTeX"},
        ]