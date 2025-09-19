import streamlit as st
import requests
import pandas as pd
from typing import Dict, List, Optional
import io
import base64

# Configuration
API_BASE_URL = "http://localhost:8000/api/v1"

# Session state initialization
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'token' not in st.session_state:
    st.session_state.token = None
if 'user' not in st.session_state:
    st.session_state.user = None

class BibliographyAPI:
    """API client for the bibliography backend."""
    
    def __init__(self, base_url: str, token: Optional[str] = None):
        self.base_url = base_url
        self.token = token
    
    @property
    def headers(self):
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    def login(self, email: str, password: str) -> Dict:
        """Login and get authentication token."""
        response = requests.post(
            f"{self.base_url}/auth/jwt/login",
            data={"username": email, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        return response.json() if response.status_code == 200 else {"error": response.text}
    
    def get_papers(self, search_space_id: Optional[int] = None, limit: int = 50) -> Dict:
        """Get list of papers."""
        params = {"limit": limit}
        if search_space_id:
            params["search_space_id"] = search_space_id
        
        response = requests.get(
            f"{self.base_url}/papers/",
            params=params,
            headers=self.headers
        )
        return response.json() if response.status_code == 200 else {"error": response.text}
    
    def search_papers(self, query: str, search_space_id: Optional[int] = None) -> Dict:
        """Search papers."""
        data = {"query": query, "limit": 20}
        if search_space_id:
            data["search_space_id"] = search_space_id
        
        response = requests.post(
            f"{self.base_url}/papers/search",
            json=data,
            headers=self.headers
        )
        return response.json() if response.status_code == 200 else {"error": response.text}
    
    def upload_paper(self, file, search_space_id: int) -> Dict:
        """Upload a PDF paper."""
        files = {"file": (file.name, file, "application/pdf")}
        data = {"search_space_id": search_space_id, "move_file": True}
        
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        
        response = requests.post(
            f"{self.base_url}/papers/upload",
            files=files,
            data=data,
            headers=headers
        )
        return response.json() if response.status_code == 200 else {"error": response.text}
    
    def get_citation(self, paper_id: int, style: str = "apa") -> Dict:
        """Get formatted citation for a paper."""
        response = requests.post(
            f"{self.base_url}/papers/{paper_id}/citation",
            json={"style": style},
            headers=self.headers
        )
        return response.json() if response.status_code == 200 else {"error": response.text}
    
    def get_search_spaces(self) -> Dict:
        """Get user's search spaces."""
        response = requests.get(
            f"{self.base_url}/search-spaces/",
            headers=self.headers
        )
        return response.json() if response.status_code == 200 else {"error": response.text}
    
    def semantic_search(self, query: str, search_type: str = "hybrid", 
                       search_space_id: Optional[int] = None, limit: int = 10) -> Dict:
        """Perform semantic search on papers."""
        data = {
            "query": query,
            "search_type": search_type,
            "limit": limit,
            "min_confidence": 0.0,
            "include_abstracts": True
        }
        if search_space_id:
            data["search_space_id"] = search_space_id
        
        response = requests.post(
            f"{self.base_url}/semantic-search/",
            json=data,
            headers=self.headers
        )
        return response.json() if response.status_code == 200 else {"error": response.text}
    
    def get_similar_papers(self, paper_id: int, limit: int = 5) -> Dict:
        """Get papers similar to a given paper."""
        response = requests.get(
            f"{self.base_url}/semantic-search/similar/{paper_id}",
            params={"limit": limit},
            headers=self.headers
        )
        return response.json() if response.status_code == 200 else {"error": response.text}
    
    def get_user_dashboard(self) -> Dict:
        """Get user dashboard data."""
        response = requests.get(
            f"{self.base_url}/dashboard/user",
            headers=self.headers
        )
        return response.json() if response.status_code == 200 else {"error": response.text}
    
    def get_global_dashboard(self) -> Dict:
        """Get global dashboard data."""
        response = requests.get(
            f"{self.base_url}/dashboard/global",
            headers=self.headers
        )
        return response.json() if response.status_code == 200 else {"error": response.text}
    
    def get_dashboard_overview(self) -> Dict:
        """Get dashboard overview."""
        response = requests.get(
            f"{self.base_url}/dashboard/overview",
            headers=self.headers
        )
        return response.json() if response.status_code == 200 else {"error": response.text}

def login_page():
    """Display login page."""
    st.title("📚 Bibliography Manager")
    st.markdown("### Please log in to continue")
    
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit and email and password:
            api = BibliographyAPI(API_BASE_URL)
            result = api.login(email, password)
            
            if "access_token" in result:
                st.session_state.authenticated = True
                st.session_state.token = result["access_token"]
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Login failed. Please check your credentials.")

def main_app():
    """Main application interface."""
    api = BibliographyAPI(API_BASE_URL, st.session_state.token)
    
    # Sidebar
    st.sidebar.title("📚 Bibliography")
    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.session_state.token = None
        st.rerun()
    
    # Get search spaces
    search_spaces_result = api.get_search_spaces()
    search_spaces = search_spaces_result.get("search_spaces", []) if "error" not in search_spaces_result else []
    
    # Main content
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📖 Browse Papers", "🔍 Search", "🧠 Semantic Search", "📤 Upload", "📊 Dashboard", "🔧 Admin"])
    
    with tab1:
        browse_papers_tab(api, search_spaces)
    
    with tab2:
        search_papers_tab(api, search_spaces)
    
    with tab3:
        semantic_search_tab(api, search_spaces)
    
    with tab4:
        upload_papers_tab(api, search_spaces)
    
    with tab5:
        dashboard_tab(api)
    
    with tab6:
        admin_tab(api)

def browse_papers_tab(api: BibliographyAPI, search_spaces: List[Dict]):
    """Browse papers tab."""
    st.header("📖 Browse Papers")
    
    # Filter options
    col1, col2 = st.columns([2, 1])
    
    with col1:
        search_space_options = {ss["name"]: ss["id"] for ss in search_spaces}
        search_space_options["All Spaces"] = None
        selected_space = st.selectbox(
            "Search Space",
            options=list(search_space_options.keys()),
            index=0
        )
    
    with col2:
        limit = st.number_input("Papers to show", min_value=10, max_value=100, value=20)
    
    search_space_id = search_space_options[selected_space]
    
    # Get papers
    papers_result = api.get_papers(search_space_id=search_space_id, limit=limit)
    
    if "error" in papers_result:
        st.error(f"Error loading papers: {papers_result['error']}")
        return
    
    papers = papers_result.get("papers", [])
    
    if not papers:
        st.info("No papers found. Try uploading some PDFs!")
        return
    
    st.write(f"Found {len(papers)} papers")
    
    # Display papers
    for paper in papers:
        with st.expander(f"📄 {paper.get('title', 'Untitled')}"):
            display_paper(paper, api)

def search_papers_tab(api: BibliographyAPI, search_spaces: List[Dict]):
    """Search papers tab."""
    st.header("🔍 Search Papers")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        query = st.text_input("Search query", placeholder="Enter keywords, title, author, etc.")
    
    with col2:
        search_space_options = {ss["name"]: ss["id"] for ss in search_spaces}
        search_space_options["All Spaces"] = None
        selected_space = st.selectbox(
            "Search in",
            options=list(search_space_options.keys()),
            index=0,
            key="search_space"
        )
    
    if st.button("🔍 Search") and query:
        search_space_id = search_space_options[selected_space]
        search_result = api.search_papers(query, search_space_id)
        
        if "error" in search_result:
            st.error(f"Search error: {search_result['error']}")
            return
        
        papers = search_result.get("papers", [])
        
        if not papers:
            st.info("No papers found matching your query.")
            return
        
        st.success(f"Found {len(papers)} papers")
        
        for paper in papers:
            with st.expander(f"📄 {paper.get('title', 'Untitled')}"):
                display_paper(paper, api)

def upload_papers_tab(api: BibliographyAPI, search_spaces: List[Dict]):
    """Upload papers tab."""
    st.header("📤 Upload Papers")
    
    if not search_spaces:
        st.warning("You need to create a search space first.")
        return
    
    search_space_options = {ss["name"]: ss["id"] for ss in search_spaces}
    
    with st.form("upload_form"):
        selected_space = st.selectbox(
            "Upload to Search Space",
            options=list(search_space_options.keys())
        )
        
        uploaded_file = st.file_uploader(
            "Choose PDF file",
            type="pdf",
            accept_multiple_files=False
        )
        
        submit = st.form_submit_button("📤 Upload Paper")
        
        if submit and uploaded_file:
            search_space_id = search_space_options[selected_space]
            
            with st.spinner("Processing PDF... This may take a few moments."):
                result = api.upload_paper(uploaded_file, search_space_id)
            
            if "error" in result:
                st.error(f"Upload failed: {result['error']}")
            elif result.get("status") == "success":
                st.success("✅ Paper uploaded and processed successfully!")
                
                # Display extracted information
                st.subheader("Extracted Information:")
                col1, col2 = st.columns(2)
                
                with col1:
                    if result.get("title"):
                        st.write(f"**Title:** {result['title']}")
                    if result.get("authors"):
                        st.write(f"**Authors:** {', '.join(result['authors'])}")
                
                with col2:
                    if result.get("extraction_confidence"):
                        confidence = result['extraction_confidence']
                        st.metric("Extraction Confidence", f"{confidence:.2%}")
            else:
                st.warning(f"Upload completed with status: {result.get('status', 'unknown')}")
                if result.get("message"):
                    st.info(result["message"])


def display_paper(paper: Dict, api: BibliographyAPI):
    """Display paper information in an expander."""
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Basic information
        if paper.get("authors"):
            st.write(f"**Authors:** {', '.join(paper['authors'])}")
        
        if paper.get("journal"):
            journal_info = paper["journal"]
            if paper.get("volume"):
                journal_info += f", Vol. {paper['volume']}"
            if paper.get("issue"):
                journal_info += f", No. {paper['issue']}"
            if paper.get("publication_year"):
                journal_info += f" ({paper['publication_year']})"
            st.write(f"**Journal:** {journal_info}")
        
        if paper.get("doi"):
            st.write(f"**DOI:** {paper['doi']}")
        
        if paper.get("abstract"):
            with st.expander("Abstract"):
                st.write(paper["abstract"])
        
        if paper.get("keywords"):
            st.write(f"**Keywords:** {', '.join(paper['keywords'])}")
    
    with col2:
        # Actions
        if st.button("📋 Get Citation", key=f"cite_{paper['id']}"):
            citation_styles = ["apa", "mla", "chicago", "ieee", "harvard", "bibtex"]
            selected_style = st.selectbox(
                "Citation Style",
                options=citation_styles,
                key=f"style_{paper['id']}"
            )
            
            citation_result = api.get_citation(paper["id"], selected_style)
            
            if "error" not in citation_result:
                st.text_area(
                    "Citation",
                    value=citation_result.get("citation", ""),
                    height=150,
                    key=f"citation_{paper['id']}"
                )
            else:
                st.error("Failed to generate citation")
        
        if paper.get("confidence_score"):
            st.metric("Confidence", f"{paper['confidence_score']:.2%}")

def semantic_search_tab(api: BibliographyAPI, search_spaces: List[Dict]):
    """Semantic search tab with advanced search capabilities."""
    st.header("🧠 Semantic Search")
    st.markdown("*Advanced semantic search using AI embeddings for better results*")
    
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        query = st.text_input(
            "Search query", 
            placeholder="Enter your search query (e.g., 'machine learning in healthcare')..."
        )
    
    with col2:
        search_type = st.selectbox(
            "Search Type",
            options=["hybrid", "semantic", "keyword"],
            help="Hybrid: combines semantic + keyword, Semantic: AI embeddings only, Keyword: traditional text search"
        )
    
    with col3:
        search_space_options = {ss["name"]: ss["id"] for ss in search_spaces}
        search_space_options["All Spaces"] = None
        selected_space = st.selectbox(
            "Search in",
            options=list(search_space_options.keys()),
            key="semantic_search_space"
        )
    
    # Advanced options
    with st.expander("⚙️ Advanced Options"):
        col_a, col_b = st.columns(2)
        with col_a:
            limit = st.slider("Max Results", 5, 50, 15)
            min_confidence = st.slider("Min Confidence", 0.0, 1.0, 0.0, 0.1)
        with col_b:
            include_abstracts = st.checkbox("Include Abstracts", True)
    
    if st.button("🧠 Semantic Search") and query:
        search_space_id = search_space_options[selected_space]
        
        with st.spinner("Performing semantic search..."):
            search_result = api.semantic_search(
                query=query,
                search_type=search_type,
                search_space_id=search_space_id,
                limit=limit
            )
        
        if "error" in search_result:
            st.error(f"Search error: {search_result['error']}")
            return
        
        results = search_result.get("results", [])
        insights = search_result.get("insights", {})
        
        if not results:
            st.info("No papers found matching your query.")
            return
        
        # Display insights
        st.subheader("📈 Search Insights")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Results Found", insights.get("total_papers", 0))
        with col2:
            st.metric("Avg Confidence", f"{insights.get('avg_confidence', 0):.1%}")
        with col3:
            st.metric("Avg Score", f"{insights.get('avg_search_score', 0):.2f}")
        with col4:
            if insights.get("top_journals"):
                top_journal = insights["top_journals"][0]
                st.metric("Top Journal", f"{top_journal['journal'][:20]}..." if len(top_journal['journal']) > 20 else top_journal['journal'])
        
        # Display results
        st.subheader("📝 Search Results")
        
        for i, result in enumerate(results):
            paper_info = result.get("paper_info", {})
            if not paper_info:
                continue
                
            with st.expander(f"📄 {paper_info.get('title', 'Untitled')} (Score: {result.get('score', 0):.3f})"):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    if paper_info.get("authors"):
                        st.write(f"**Authors:** {', '.join(paper_info['authors'])}")
                    
                    if paper_info.get("journal"):
                        journal_info = paper_info["journal"]
                        if paper_info.get("publication_year"):
                            journal_info += f" ({paper_info['publication_year']})"
                        st.write(f"**Journal:** {journal_info}")
                    
                    if paper_info.get("doi"):
                        st.write(f"**DOI:** {paper_info['doi']}")
                    
                    if paper_info.get("abstract") and include_abstracts:
                        with st.expander("Abstract"):
                            st.write(paper_info["abstract"])
                    
                    if paper_info.get("keywords"):
                        st.write(f"**Keywords:** {', '.join(paper_info['keywords'])}")
                
                with col2:
                    st.metric("Similarity Score", f"{result.get('score', 0):.3f}")
                    if paper_info.get("confidence_score"):
                        st.metric("Extraction Confidence", f"{paper_info['confidence_score']:.1%}")
                    
                    # Similar papers button
                    if st.button("🔍 Find Similar", key=f"similar_{paper_info['id']}"):
                        similar_result = api.get_similar_papers(paper_info['id'], 3)
                        if "error" not in similar_result:
                            st.subheader("Similar Papers:")
                            for sim_paper in similar_result.get("similar_papers", []):
                                sim_info = sim_paper.get("paper_info", {})
                                if sim_info:
                                    st.write(f"- **{sim_info.get('title', 'Untitled')}** (Score: {sim_paper.get('score', 0):.3f})")

def dashboard_tab(api: BibliographyAPI):
    """Dashboard tab with analytics and overview."""
    st.header("📊 Dashboard")
    
    # Quick overview
    with st.spinner("Loading dashboard..."):
        overview_result = api.get_dashboard_overview()
    
    if "error" in overview_result:
        st.error(f"Dashboard error: {overview_result['error']}")
        return
    
    overview = overview_result.get("overview", {})
    
    # Key metrics
    st.subheader("📈 Key Metrics")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Papers", overview.get("total_papers", 0))
    with col2:
        st.metric("Search Spaces", overview.get("total_search_spaces", 0))
    with col3:
        st.metric("Annotations", overview.get("total_annotations", 0))
    with col4:
        st.metric("Avg Confidence", f"{overview.get('avg_confidence', 0):.1%}")
    with col5:
        st.metric("DOI Coverage", f"{overview.get('doi_coverage', 0):.1%}")
    
    # Get full dashboard data
    if st.button("🔄 Load Full Dashboard"):
        with st.spinner("Loading detailed analytics..."):
            dashboard_result = api.get_user_dashboard()
        
        if "error" in dashboard_result:
            st.error(f"Dashboard error: {dashboard_result['error']}")
            return
        
        # Recent Activity
        st.subheader("🕰️ Recent Activity")
        recent_activity = dashboard_result.get("recent_activity", [])
        
        if recent_activity:
            for activity in recent_activity[:5]:  # Show last 5 activities
                activity_time = datetime.fromisoformat(activity["timestamp"].replace('Z', '+00:00'))
                time_ago = datetime.now().replace(tzinfo=activity_time.tzinfo) - activity_time
                st.write(f"- **{activity['title']}** ({time_ago.days} days ago)")
        else:
            st.info("No recent activity")
        
        # Paper Analytics
        st.subheader("📉 Paper Analytics")
        paper_analytics = dashboard_result.get("paper_analytics", {})
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Publication years
            year_dist = paper_analytics.get("year_distribution", [])
            if year_dist:
                st.write("**Papers by Publication Year:**")
                year_df = pd.DataFrame(year_dist)
                st.bar_chart(year_df.set_index("year")["count"])
        
        with col2:
            # Top journals
            journals = paper_analytics.get("top_journals", [])
            if journals:
                st.write("**Top Journals:**")
                for journal in journals[:5]:
                    st.write(f"- {journal['journal']}: {journal['count']} papers")
        
        # Search Spaces
        st.subheader("📁 Search Spaces")
        search_spaces = dashboard_result.get("search_spaces", [])
        
        if search_spaces:
            for space in search_spaces:
                with st.expander(f"{space['name']} ({space['paper_count']} papers)"):
                    if space.get("description"):
                        st.write(space["description"])
                    st.write(f"Created: {space['created_at'][:10]}")
        else:
            st.info("No search spaces found")

def admin_tab(api: BibliographyAPI):
    """Admin tab for system overview."""
    st.header("🔧 System Administration")
    st.warning("Admin features - use with caution")
    
    if st.button("🌐 Load Global Dashboard"):
        with st.spinner("Loading global statistics..."):
            global_result = api.get_global_dashboard()
        
        if "error" in global_result:
            st.error(f"Global dashboard error: {global_result['error']}")
            return
        
        # System Stats
        st.subheader("📊 System Statistics")
        system_stats = global_result.get("system_stats", {})
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Users", system_stats.get("total_users", 0))
        with col2:
            st.metric("Total Papers", system_stats.get("total_papers", 0))
        with col3:
            st.metric("Search Spaces", system_stats.get("total_search_spaces", 0))
        with col4:
            st.metric("Annotations", system_stats.get("total_annotations", 0))
        
        # Storage Metrics
        st.subheader("💾 Storage Metrics")
        storage_metrics = global_result.get("storage_metrics", {})
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Storage", f"{storage_metrics.get('total_size_gb', 0):.2f} GB")
        with col2:
            st.metric("Average File Size", f"{storage_metrics.get('avg_file_size_mb', 0):.2f} MB")
        with col3:
            processing_stats = global_result.get("processing_stats", {})
            st.metric("Global Confidence", f"{processing_stats.get('global_avg_confidence', 0):.1%}")
        
        # Popular Journals
        st.subheader("📊 Popular Journals")
        content_analytics = global_result.get("content_analytics", {})
        popular_journals = content_analytics.get("popular_journals", [])
        
        if popular_journals:
            for journal in popular_journals[:10]:
                st.write(f"- **{journal['journal']}**: {journal['count']} papers")
        else:
            st.info("No journal data available")

def main():
    """Main application entry point."""
    st.set_page_config(
        page_title="Bibliography Manager",
        page_icon="📚",
        layout="wide"
    )
    
    if not st.session_state.authenticated:
        login_page()
    else:
        main_app()

if __name__ == "__main__":
    main()