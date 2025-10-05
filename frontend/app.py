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

    def get_devonthink_stats(self) -> Dict:
        """Get DEVONthink sync statistics."""
        response = requests.get(
            "http://localhost:8000/devonthink/stats",
            headers=self.headers
        )
        return response.json() if response.status_code == 200 else {"error": response.text}

    def get_devonthink_folders(self) -> Dict:
        """Get DEVONthink folder hierarchy."""
        response = requests.get(
            "http://localhost:8000/devonthink/folders",
            headers=self.headers
        )
        return response.json() if response.status_code == 200 else {"error": response.text}

    def get_devonthink_sync_status(self) -> Dict:
        """Get DEVONthink sync status."""
        response = requests.get(
            "http://localhost:8000/devonthink/sync/status",
            headers=self.headers
        )
        return response.json() if response.status_code == 200 else {"error": response.text}

    def trigger_devonthink_sync(self, database_name: str = "Reference") -> Dict:
        """Trigger DEVONthink sync."""
        response = requests.post(
            "http://localhost:8000/devonthink/sync",
            json={"database_name": database_name},
            headers=self.headers
        )
        return response.json() if response.status_code == 200 else {"error": response.text}

    def get_users(self) -> Dict:
        """Get all users (admin only)."""
        response = requests.get(
            f"{self.base_url}/admin/users",
            headers=self.headers
        )
        return response.json() if response.status_code == 200 else {"error": response.text}

    def get_user_stats(self) -> Dict:
        """Get user statistics (admin only)."""
        response = requests.get(
            f"{self.base_url}/admin/users/stats",
            headers=self.headers
        )
        return response.json() if response.status_code == 200 else {"error": response.text}

    def get_folder_hierarchy(self) -> Dict:
        """Get DEVONthink folder hierarchy."""
        response = requests.get(
            "http://localhost:8000/devonthink/folders",
            headers=self.headers
        )
        return response.json() if response.status_code == 200 else {"error": response.text}

    def get_papers_by_folder(self, folder_path: str) -> Dict:
        """Get papers in a specific folder path."""
        response = requests.get(
            f"{self.base_url}/papers/by-folder",
            params={"folder_path": folder_path},
            headers=self.headers
        )
        return response.json() if response.status_code == 200 else {"error": response.text}

    def get_paper_pdf(self, paper_id: int) -> bytes:
        """Get PDF file for a paper."""
        response = requests.get(
            f"{self.base_url}/papers/{paper_id}/pdf",
            headers=self.headers
        )
        return response.content if response.status_code == 200 else None

    def get_annotations(self, paper_id: int) -> Dict:
        """Get annotations for a paper."""
        response = requests.get(
            f"{self.base_url}/annotations/paper/{paper_id}",
            headers=self.headers
        )
        return response.json() if response.status_code == 200 else {"error": response.text}

    def add_annotation(self, paper_id: int, content: str, page_number: int = None,
                       annotation_type: str = "note", is_private: bool = True) -> Dict:
        """Add annotation to a paper."""
        data = {
            "paper_id": paper_id,
            "content": content,
            "annotation_type": annotation_type,
            "is_private": is_private
        }
        if page_number is not None:
            data["page_number"] = page_number

        response = requests.post(
            f"{self.base_url}/annotations/",
            json=data,
            headers=self.headers
        )
        return response.json() if response.status_code == 200 else {"error": response.text}

    def rag_ask_question(self, question: str, search_space_id: int = None) -> Dict:
        """Ask a question using RAG."""
        data = {"question": question}
        if search_space_id:
            data["search_space_id"] = search_space_id

        response = requests.post(
            f"{self.base_url}/enhanced-rag/ask",
            json=data,
            headers=self.headers
        )
        return response.json() if response.status_code == 200 else {"error": response.text}

    def rag_search(self, query: str, search_space_id: int = None, limit: int = 10) -> Dict:
        """Enhanced RAG search."""
        data = {"query": query, "limit": limit}
        if search_space_id:
            data["search_space_id"] = search_space_id

        response = requests.post(
            f"{self.base_url}/enhanced-rag/search",
            json=data,
            headers=self.headers
        )
        return response.json() if response.status_code == 200 else {"error": response.text}

    def create_chat(self, name: str, search_space_id: int) -> Dict:
        """Create a new chat session."""
        response = requests.post(
            f"{self.base_url}/chats/",
            json={"name": name, "search_space_id": search_space_id},
            headers=self.headers
        )
        return response.json() if response.status_code == 200 else {"error": response.text}

    def get_chats(self) -> Dict:
        """Get all chat sessions."""
        response = requests.get(
            f"{self.base_url}/chats/",
            headers=self.headers
        )
        return response.json() if response.status_code == 200 else {"error": response.text}

    def send_chat_message(self, message: str, search_space_id: int = None) -> Dict:
        """Send a chat message."""
        data = {"message": message}
        if search_space_id:
            data["search_space_id"] = search_space_id

        response = requests.post(
            "http://localhost:8000/api/v1/chats/chat",
            json=data,
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
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📚 Library", "🔍 Search", "💬 Chat", "📊 Dashboard", "🔧 Admin"])

    with tab1:
        library_browser_tab(api)

    with tab2:
        search_tab(api, search_spaces)

    with tab3:
        chat_tab(api, search_spaces)

    with tab4:
        dashboard_tab(api)

    with tab5:
        admin_tab(api)

def chat_tab(api: BibliographyAPI, search_spaces: List[Dict]):
    """AI Chat interface with RAG."""
    st.header("💬 Research Assistant")
    st.markdown("*Ask questions about your research papers and get AI-powered answers with citations*")

    # Initialize chat history
    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = []

    # Search space selector
    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown("### Ask your research assistant")

    with col2:
        search_space_options = {ss["name"]: ss["id"] for ss in search_spaces}
        search_space_options["All Papers"] = None
        selected_space = st.selectbox(
            "Search in",
            options=list(search_space_options.keys()),
            index=0,
            key="chat_search_space"
        )

    search_space_id = search_space_options[selected_space]

    # Display chat history
    chat_container = st.container()

    with chat_container:
        for message in st.session_state.chat_messages:
            if message["role"] == "user":
                with st.chat_message("user"):
                    st.write(message["content"])
            else:
                with st.chat_message("assistant"):
                    st.write(message["content"])

                    # Show sources if available
                    if "sources" in message and message["sources"]:
                        with st.expander("📚 View Sources"):
                            for i, source in enumerate(message["sources"], 1):
                                st.markdown(f"**{i}. {source.get('title', 'Untitled')}**")
                                if source.get('authors'):
                                    st.caption(f"Authors: {', '.join(source['authors'])}")
                                if source.get('score'):
                                    st.caption(f"Relevance: {source['score']:.2%}")
                                st.markdown("---")

    # Chat input
    user_question = st.chat_input("Ask a question about your research papers...")

    if user_question:
        # Add user message to chat
        st.session_state.chat_messages.append({
            "role": "user",
            "content": user_question
        })

        # Get AI response
        with st.spinner("🤔 Thinking..."):
            response = api.rag_ask_question(user_question, search_space_id)

        if "error" in response:
            st.error(f"Error: {response.get('error')}")
        else:
            # Add assistant response
            assistant_message = {
                "role": "assistant",
                "content": response.get("answer", "I couldn't generate an answer."),
                "sources": response.get("sources", [])
            }

            st.session_state.chat_messages.append(assistant_message)
            st.rerun()

    # Clear chat button
    if st.session_state.chat_messages:
        if st.button("🗑️ Clear Chat History"):
            st.session_state.chat_messages = []
            st.rerun()


def library_browser_tab(api: BibliographyAPI):
    """Library browser with file tree, PDF viewer, and annotations."""
    st.header("📚 Research Library")

    # Initialize session state
    if 'selected_paper' not in st.session_state:
        st.session_state.selected_paper = None
    if 'expanded_folders' not in st.session_state:
        st.session_state.expanded_folders = set()

    # Create two columns: file tree on left, content on right
    col_tree, col_content = st.columns([1, 3])

    with col_tree:
        st.subheader("📁 Folders")

        # Get folder hierarchy
        with st.spinner("Loading folders..."):
            folders_result = api.get_folder_hierarchy()

        if "error" in folders_result:
            st.error("Could not load folder hierarchy")
        elif isinstance(folders_result, list) and folders_result:
            # Display folder tree
            for folder in folders_result:
                render_folder_tree(folder, api, level=0)
        else:
            st.info("No folders synced yet. Go to Admin → DEVONthink Sync to sync your library.")

    with col_content:
        if st.session_state.selected_paper:
            display_paper_with_pdf_and_annotations(st.session_state.selected_paper, api)
        else:
            st.info("👈 Select a paper from the folder tree to view it")


def render_folder_tree(folder: Dict, api: BibliographyAPI, level: int = 0):
    """Recursively render folder tree with papers."""
    folder_name = folder.get("name", "Unnamed")
    folder_path = folder.get("path", "")
    subfolders = folder.get("subfolders", [])

    # Create indent
    indent = "  " * level

    # Folder expander
    folder_key = f"folder_{folder_path}_{level}"

    with st.expander(f"{indent}📁 {folder_name}", expanded=(folder_key in st.session_state.expanded_folders)):
        # Get papers in this folder
        papers_result = api.get_papers_by_folder(folder_path)

        if "error" not in papers_result:
            papers = papers_result.get("papers", [])

            # Display papers in this folder
            if papers:
                for paper in papers:
                    paper_title = paper.get("title", "Untitled")[:50]
                    if st.button(f"📄 {paper_title}", key=f"paper_{paper['id']}", use_container_width=True):
                        st.session_state.selected_paper = paper
                        st.rerun()

        # Render subfolders
        for subfolder in subfolders:
            render_folder_tree(subfolder, api, level + 1)


def display_paper_with_pdf_and_annotations(paper: Dict, api: BibliographyAPI):
    """Display paper with PDF viewer and annotations."""
    paper_id = paper.get("id")

    # Paper header
    st.markdown(f"### 📄 {paper.get('title', 'Untitled')}")

    if paper.get("authors"):
        st.markdown(f"**Authors:** {', '.join(paper['authors'])}")

    if paper.get("journal"):
        journal_info = paper["journal"]
        if paper.get("publication_year"):
            journal_info += f" ({paper['publication_year']})"
        st.markdown(f"**Journal:** {journal_info}")

    # Create tabs for PDF and annotations
    pdf_tab, annotations_tab, metadata_tab = st.tabs(["📖 PDF", "📝 Annotations", "ℹ️ Metadata"])

    with pdf_tab:
        # PDF Viewer
        pdf_content = api.get_paper_pdf(paper_id)

        if pdf_content:
            # Encode PDF for display
            import base64
            base64_pdf = base64.b64encode(pdf_content).decode('utf-8')
            pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"></iframe>'
            st.markdown(pdf_display, unsafe_allow_html=True)
        else:
            st.warning("PDF file not available")

    with annotations_tab:
        display_annotations_panel(paper_id, api)

    with metadata_tab:
        display_paper_metadata(paper)


def display_annotations_panel(paper_id: int, api: BibliographyAPI):
    """Display and manage annotations for a paper."""
    st.subheader("📝 Annotations")

    # Add new annotation form
    with st.form(key=f"new_annotation_{paper_id}"):
        st.write("**Add New Annotation**")

        col1, col2 = st.columns([3, 1])
        with col1:
            annotation_content = st.text_area("Note", placeholder="Enter your annotation...", height=100)
        with col2:
            page_number = st.number_input("Page", min_value=1, value=1, step=1)
            is_private = st.checkbox("Private", value=True, help="Only you can see private annotations")

        submit = st.form_submit_button("💾 Save Annotation", type="primary")

        if submit and annotation_content:
            result = api.add_annotation(
                paper_id=paper_id,
                content=annotation_content,
                page_number=page_number,
                is_private=is_private
            )

            if "error" in result:
                st.error(f"Failed to save annotation: {result.get('error')}")
            else:
                st.success("✅ Annotation saved!")
                st.rerun()

    # Display existing annotations
    st.markdown("---")
    st.write("**Your Annotations**")

    annotations_result = api.get_annotations(paper_id)

    if "error" in annotations_result:
        st.info("No annotations yet")
    else:
        annotations = annotations_result.get("annotations", [])

        if annotations:
            for ann in annotations:
                with st.container():
                    col1, col2 = st.columns([4, 1])

                    with col1:
                        privacy_icon = "🔒" if ann.get("is_private") else "🌐"
                        st.markdown(f"{privacy_icon} **Page {ann.get('page_number', 'N/A')}**")
                        st.write(ann.get("content", ""))

                    with col2:
                        if ann.get("created_at"):
                            st.caption(ann["created_at"][:10])

                    st.markdown("---")
        else:
            st.info("No annotations yet. Add one above!")


def display_paper_metadata(paper: Dict):
    """Display full paper metadata."""
    st.subheader("ℹ️ Paper Metadata")

    metadata_items = [
        ("Title", paper.get("title")),
        ("Authors", ", ".join(paper.get("authors", []))),
        ("Journal", paper.get("journal")),
        ("Volume", paper.get("volume")),
        ("Issue", paper.get("issue")),
        ("Pages", paper.get("pages")),
        ("Publication Year", paper.get("publication_year")),
        ("DOI", paper.get("doi")),
        ("PMID", paper.get("pmid")),
        ("Keywords", ", ".join(paper.get("keywords", []))),
    ]

    for label, value in metadata_items:
        if value:
            st.write(f"**{label}:** {value}")

    if paper.get("abstract"):
        st.markdown("**Abstract:**")
        st.write(paper["abstract"])

    if paper.get("dt_source_path"):
        st.markdown("**DEVONthink Path:**")
        st.code(paper["dt_source_path"])


def search_tab(api: BibliographyAPI, search_spaces: List[Dict]):
    """Combined search tab with keyword and semantic search."""
    st.header("🔍 Search")

    search_type = st.radio(
        "Search Type",
        ["Keyword Search", "Semantic Search"],
        horizontal=True
    )

    if search_type == "Keyword Search":
        keyword_search_panel(api, search_spaces)
    else:
        semantic_search_panel(api, search_spaces)


def keyword_search_panel(api: BibliographyAPI, search_spaces: List[Dict]):
    """Keyword search interface."""
    col1, col2 = st.columns([3, 1])

    with col1:
        query = st.text_input("Search query", placeholder="Enter keywords, title, author, etc.")

    with col2:
        search_space_options = {ss["name"]: ss["id"] for ss in search_spaces}
        search_space_options["All Spaces"] = None
        selected_space = st.selectbox(
            "Search in",
            options=list(search_space_options.keys()),
            index=0
        )

    if st.button("🔍 Search", type="primary") and query:
        search_space_id = search_space_options[selected_space]
        search_result = api.search_papers(query, search_space_id)

        if "error" in search_result:
            st.error(f"Search error: {search_result['error']}")
        else:
            papers = search_result.get("papers", [])

            if papers:
                st.success(f"Found {len(papers)} papers")
                for paper in papers:
                    with st.expander(f"📄 {paper.get('title', 'Untitled')}"):
                        if st.button("View Paper", key=f"view_{paper['id']}"):
                            st.session_state.selected_paper = paper
                            st.rerun()
                        display_paper(paper, api)
            else:
                st.info("No papers found")


def semantic_search_panel(api: BibliographyAPI, search_spaces: List[Dict]):
    """Semantic search interface."""
    # Keep the existing semantic search implementation
    semantic_search_tab(api, search_spaces)


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

    # Create sub-tabs for different admin functions
    admin_tab1, admin_tab2, admin_tab3 = st.tabs(["📚 DEVONthink Sync", "👥 User Management", "📊 System Stats"])

    with admin_tab1:
        devonthink_sync_panel(api)

    with admin_tab2:
        user_management_panel(api)

    with admin_tab3:
        system_stats_panel(api)

def devonthink_sync_panel(api: BibliographyAPI):
    """DEVONthink sync status and controls."""
    st.subheader("📚 DEVONthink Synchronization")

    # Sync status
    col1, col2 = st.columns([2, 1])

    with col1:
        if st.button("🔄 Refresh Status", key="refresh_dt_status"):
            st.rerun()

    with col2:
        database_name = st.text_input("Database Name", value="Reference", key="dt_db_name")

    # Get current sync stats
    with st.spinner("Loading DEVONthink status..."):
        stats_result = api.get_devonthink_stats()
        folders_result = api.get_devonthink_folders()
        sync_status_result = api.get_devonthink_sync_status()

    # Display stats
    if "error" not in stats_result:
        st.markdown("### 📊 Sync Statistics")
        stats = stats_result

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Synced", stats.get("total_synced", 0))
        with col2:
            st.metric("Successful", stats.get("successful_syncs", 0))
        with col3:
            st.metric("Failed", stats.get("failed_syncs", 0))
        with col4:
            success_rate = stats.get("success_rate", 0)
            st.metric("Success Rate", f"{success_rate:.1%}")

        if stats.get("last_sync_time"):
            st.info(f"Last sync: {stats['last_sync_time']}")

    # Display folder hierarchy
    if "error" not in folders_result and isinstance(folders_result, list):
        st.markdown("### 📁 DEVONthink Folder Hierarchy")

        if folders_result:
            for folder in folders_result:
                display_folder_tree(folder, level=0)
        else:
            st.info("No folders synced yet")

    # Display recent sync status
    if "error" not in sync_status_result and isinstance(sync_status_result, list):
        st.markdown("### 📝 Recent Sync Records")

        if sync_status_result:
            # Convert to DataFrame for better display
            sync_df = pd.DataFrame([
                {
                    "DEVONthink UUID": s.get("dt_uuid", "")[:16] + "...",
                    "Local UUID": s.get("local_uuid", "")[:16] + "...",
                    "Status": s.get("sync_status", ""),
                    "Path": s.get("dt_path", "")[:50] + "..." if len(s.get("dt_path", "")) > 50 else s.get("dt_path", ""),
                    "Last Sync": s.get("last_synced_at", "")[:19] if s.get("last_synced_at") else "Never"
                }
                for s in sync_status_result[:20]  # Show last 20
            ])
            st.dataframe(sync_df, use_container_width=True)
        else:
            st.info("No sync records found")

    # Sync controls
    st.markdown("### 🎛️ Sync Controls")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🚀 Start Full Sync", type="primary", key="start_full_sync"):
            with st.spinner(f"Starting full sync of '{database_name}' database..."):
                sync_result = api.trigger_devonthink_sync(database_name)

            if "error" in sync_result:
                st.error(f"Sync failed: {sync_result['error']}")
            else:
                st.success(f"✅ Sync completed!")
                st.json(sync_result)

    with col2:
        st.info("💡 Full sync will process all records in your DEVONthink database")

def display_folder_tree(folder: Dict, level: int = 0):
    """Recursively display folder tree."""
    indent = "  " * level
    icon = "📁" if folder.get("subfolders") else "📄"

    folder_name = folder.get("name", "Unnamed")
    record_count = folder.get("record_count", 0)

    st.write(f"{indent}{icon} **{folder_name}** ({record_count} records)")

    # Display subfolders
    subfolders = folder.get("subfolders", [])
    if subfolders:
        for subfolder in subfolders:
            display_folder_tree(subfolder, level + 1)

def user_management_panel(api: BibliographyAPI):
    """User management panel for admins."""
    st.subheader("👥 User Management")

    if st.button("🔄 Refresh Users", key="refresh_users"):
        st.rerun()

    # Get user stats
    stats_result = api.get_user_stats()

    if "error" not in stats_result:
        st.markdown("### 📊 User Statistics")
        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.metric("Total Users", stats_result.get("total_users", 0))
        with col2:
            st.metric("Active", stats_result.get("active_users", 0))
        with col3:
            st.metric("Verified", stats_result.get("verified_users", 0))
        with col4:
            st.metric("Superusers", stats_result.get("superusers", 0))
        with col5:
            st.metric("Inactive", stats_result.get("inactive_users", 0))

    # Get users list
    users_result = api.get_users()

    if "error" in users_result:
        st.error(f"Error loading users: {users_result.get('error', 'Unknown error')}")
        st.info("Make sure you are logged in as a superuser")
    elif isinstance(users_result, list):
        users = users_result

        if users:
            st.markdown(f"### 👥 All Users ({len(users)})")

            # Create user table
            user_df = pd.DataFrame([
                {
                    "Email": u.get("email", ""),
                    "Status": "✅ Active" if u.get("is_active") else "❌ Inactive",
                    "Verified": "✅" if u.get("is_verified") else "❌",
                    "Superuser": "🔑" if u.get("is_superuser") else "-",
                    "ID": str(u.get("id", ""))[:8] + "..."
                }
                for u in users
            ])

            st.dataframe(user_df, use_container_width=True)
        else:
            st.info("No users found")

def system_stats_panel(api: BibliographyAPI):
    """System statistics panel."""
    st.subheader("📊 System Statistics")

    if st.button("🌐 Load Global Dashboard", key="load_global_dash"):
        with st.spinner("Loading global statistics..."):
            global_result = api.get_global_dashboard()

        if "error" in global_result:
            st.error(f"Global dashboard error: {global_result['error']}")
            return

        # System Stats
        st.markdown("### 📊 System Overview")
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
        st.markdown("### 💾 Storage Metrics")
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
        st.markdown("### 📊 Popular Journals")
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