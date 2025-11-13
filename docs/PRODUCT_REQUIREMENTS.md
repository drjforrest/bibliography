# Bibliography: The App

### Problem Statement
Researchers and avid readers often struggle to organize, search, and annotate their extensive PDF libraries efficiently. Current tools frequently lack integrated full-text search and seamless metadata management, making literature reviews and scholarly work cumbersome.

### Goals and Objectives
- Enable rapid searching and browsing of personal PDF collections.
- Allow exporting accurate, formatted citations for scholarly work.
- Enable adding notes and lightweight annotations to PDFs.
- Secure user authentication and registry for privacy and creditable actions.
- Improve productivity for academic research workflows.

### User Personas
- Academic Researchers: Need to collect, annotate, and cite research papers; want robust search and export functions.
- Graduate Students: Require organized reading lists and annotation for coursework and projects.
- Knowledge Workers: Seek simple citation export and quick notes for efficient information management.

### Use Cases
- A researcher catalogs and browses their PDF library, exporting citation for grant proposals.
- A student annotates and adds notes to important sections for study.
- A registered user logs in, searches for a report using vector similarity, and copies its citation.
- A team member creates basic text annotations to share with collaborators.

### Key Features
- PDF Browsing: Browse organized collections via tags, folders, or search queries.
- Vectorized Full-text Search: Semantic search via pgvector for fast retrieval.
- Citation Copying: Export formatted citations (APA, MLA, etc.) for any PDF.
- Basic Notes & Annotations: Inline note-adding, annotation overlays stored with metadata.
- User Registry & Authentication: Secure registration, login, permission management.
- PDF Metadata Management: Store, edit, and display extracted metadata (title, author, date).

### Success Metrics
- Time-to-find for any paper reduced by 50% compared to baseline manual folder navigation.
- At least 90% citation formatting accuracy (verified vs published examples).
- Annotation adoption: >60% users actively use annotation feature within first month.
- Session completion rate: >95% successful login and search per session.

### Assumptions
- The user has a local collection of PDFs with standard metadata formats.
- Postgresql and pgvector will run locally without high-volume concurrent usage.
- Users are credentialed and aware of basic citation standards.
- FastAPI, Streamlit, and PYMuPDF are compatible in local deployment environment.

### Timeline
- Month 1: MVP scope – PDF ingest/parsing, metadata storage, user login, basic search, citation export.
- Month 2: Add annotation features, UX improvements, and tag/folder navigation.
- Month 3+: Future enhancements – Group sharing, advanced permissions, full-text annotation sync, mobile support.

### Stakeholders
- Product Owner
- Lead Backend Engineer
- Frontend Developer (Streamlit)
- Authentication/DevOps Engineer
- End users (researchers, students)

### Known Constraints or Dependencies
- Local deployment – must support easy install across Mac/PC.
- PDF parsing – PYMuPDF compatibility with encrypted or unusual PDF formats.
- PostgreSQL/pgvector capacity – efficient for personal scale, not cloud multi-tenant.
- Streamlit UI – limits advanced customization and third-party integrations.

### Open Questions
- Which citation formats are highest priority for export?
- What annotation types (text, highlight, drawing) are most needed?
- Should folders/tags support nested hierarchy?
- Is OAuth or another SSO needed for user registry beyond basic credentials?

### Risks
- Security: Storing user credentials locally may pose risks; mitigate via strong password hashing, secure session management.
- PDF compatibility: Some PDFs may fail parsing or metadata extraction; provide fallback mechanisms.
- User adoption: If annotation flow is clunky, engagement may lag; mitigate via UX prototyping and testing.

This PRD provides clear direction for building an actionable personal PDF library app tailored for serious research workflows, with extensible architecture and targeted initial features.

Sources