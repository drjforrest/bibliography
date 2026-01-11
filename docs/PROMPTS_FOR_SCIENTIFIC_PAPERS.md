### Pre-Loaded Prompts for Your Scientific Library App

Based on current best practices in research analytics and academic AI integration, here are actionable prompt templates you can embed into your scientific library application. These are organized by use case and include variations for quick analysis versus deep engagement.

#### Core Analysis Prompts

1. Comprehensive Paper Analysis (Standard Deep Dive)

```Analyze this research paper systematically:
- Research Question & Objectives: What is the study's central aim?
- Methodology & Data: What research design, sample size, and data sources were used?
- Key Findings: What are the most important results and their effect sizes/confidence intervals?
- Theoretical Framework: What theories or models underpin this work?
- Limitations & Validity: What methodological constraints or potential biases exist?
- Scholarly Context: How does this paper build upon, contradict, or extend prior research?
- Practical & Theoretical Implications: What are the real-world or policy applications?
- Relevance to [YOUR RESEARCH AREA]: How applicable is this to your work?
```

2. Quick Paper Summary (2-3 Minutes)

```Provide a concise 150-word overview capturing:
- Central research question
- Methodology type (e.g., RCT, qualitative, systematic review)
- Main finding(s) with effect size if applicable
- One key limitation
- Why this matters to [RESEARCH DOMAIN]
```

#### Critical Appraisal Prompts

3. Methodology & Risk of Bias Assessment

```Evaluate the methodological quality of this paper:
- Study Design Appropriateness: Is the design well-suited to the research question?
- Sample Adequacy: Is the sample size, selection, and composition appropriate?
- Data Collection Quality: Were measurements valid and reliable?
- Analysis Rigor: Were statistical/qualitative analysis methods appropriate?
- Potential Biases: What sources of bias might affect findings (selection, measurement, reporting)?
- Internal Validity: Can we trust these results given the study design?
- External Validity: How generalizable are these findings beyond the study population?
- Quality Rating: [Strong/Moderate/Weak] with justification
```

4. Critical Appraisal via IMRaD Structure

```Review this paper using IMRaD framework:
INTRODUCTION: Are the research gaps clearly identified? Is the relevance established?
METHODS: Are methods adequately described for reproducibility? Are ethical considerations addressed?
RESULTS: Are results clearly presented? Do tables/figures match text descriptions?
DISCUSSION: Are interpretations supported by findings? Are limitations discussed? Is speculation identified?
Overall Assessment: [Score 1-5] Key strengths and weaknesses?
```

5. Spin & Interpretive Bias Detection

```Identify potential spin (distorted interpretation) in this paper:
- Title Accuracy: Does the title reflect study limitations or overstate findings?
- Conclusion Alignment: Are conclusions supported by the actual data presented?
- Selective Reporting: Are unfavorable results downplayed or missing?
- Inappropriate Extrapolation: Are findings generalized beyond the study population?
- Potential Conflicts of Interest: Do author affiliations or funding sources suggest bias?
Spin Risk Level: [None/Minor/Moderate/Significant]
```

#### Knowledge Synthesis & Integration Prompts

6. Generate Essential Questions (Strategic Deep Understanding)

```Create 5-7 essential questions that, when answered, fully capture the core contribution of this paper:
Focus on:
- Central thesis or hypothesis examined
- Key supporting evidence and data
- Important methodological choices
- Stated limitations and assumptions
- Broader implications for the field

For each question, provide a direct quote from the paper that addresses it.
```

7. Research Gap Identification

```Based on this paper, identify the research gaps it addresses and creates:
- Gaps This Paper Addressed: What prior knowledge or methodological gaps did it fill?
- Gaps This Paper Creates: What new questions emerge from the findings?
- Why These Gaps Matter: What are the theoretical or practical implications of these gaps?
- Feasible Next Steps: What follow-up research would logically address these gaps?
- Relevance to My Work: How do these gaps relate to [YOUR RESEARCH AREA]?
```

8. Cross-Paper Synthesis (For Multiple Papers)

```Synthesize insights across these [N] papers:
- Common Themes: What consistent findings or approaches appear across papers?
- Contradictions: Where do papers disagree? How might these differences be explained?
- Methodological Patterns: Do certain designs appear more in specific findings?
- Research Evolution: How has thinking on this topic evolved (chronologically)?
- Knowledge Gaps: Where does evidence diverge or remain unclear?
- Synthesis Statement: Write a 2-3 sentence statement capturing the collective evidence
```

#### Applied Research Prompts

9. Extract for Grant/Proposal Writing

```Extract key elements for incorporating this paper into a grant proposal:
- Strategic Relevance: Why is this study important for your proposed research?
- Preliminary Evidence: What specific findings support the need for your project?
- Methodological Lessons: What approaches or cautions should inform your design?
- Cited Limitations: What gaps does this study suggest your project should address?
- Quotable Insight: Provide a key quote (with page/section) suitable for proposal text
- Citation Format: [Provide in your preferred style - APA/Vancouver/etc.]
```

10. Practical & Theoretical Implications Assessment

```For this paper, distinguish between:
THEORETICAL IMPLICATIONS:
- What does this advance our conceptual understanding of [TOPIC]?
- How might these findings change theoretical models?

PRACTICAL IMPLICATIONS:
- What specific changes to clinical practice, policy, or intervention are suggested?
- Who are the key stakeholder groups affected?
- What are implementation barriers and enablers?

POLICY IMPLICATIONS:
- Are there health system, regulatory, or governance implications?
- What evidence would be needed before policy change?

NEXT STEPS FOR YOUR WORK:
- Which implication is most relevant to your research direction?
```

#### Quality & Validity Prompts

11. Evidence Strength & Certainty Assessment

```Rate the strength of evidence in this paper using a hierarchy:
- Evidence Hierarchy Level: [Systematic review/RCT/Cohort/Case-control/Case series/Opinion]
- Quality of Execution: How well was this level of evidence conducted?
- Certainty of Evidence: [High/Moderate/Low/Very Low] - Why?
- Applicability: How directly do results apply to [YOUR POPULATION/CONTEXT]?
- Recommendation Confidence: If recommending change based on this paper, how confident would you be?
```

12. Author & Source Credibility Check

```Assess the credibility of this paper's authors:
- Author Expertise: What is their track record in this field?
- Institutional Affiliation: What's the reputation and resources of their organization?
- Funding Sources: Are there transparent declarations and potential conflicts?
- Citation Impact: How influential are their prior works?
- Publication Venue: What's the peer-review rigor and impact factor of this journal?
- Overall Trust Assessment: [High/Moderate/Low] - Consider all factors above
```

#### Organization & Management Prompts

13. Paper Tagging & Categorization (For Library Organization)

```Suggest metadata categories for organizing this paper:
- Research Design: [RCT/Observational/Qualitative/Mixed/etc.]
- Topic/Keyword Tags: [5-7 relevant descriptors]
- Relevance to My Research: [Core/Supporting/Background/Tangential]
- Geographic Context: [Location(s) of study if applicable]
- Population/Participants: [Brief descriptor of study population]
- Evidence Level: [High/Moderate/Low quality evidence]
- Status: [Must-read/Important/Reference/Skim]
```

14. Visual/Tabular Summary (For Comparison Tables)

```Create a comparison table row for this paper including:
Authors | Year | Design | Sample | Key Finding(s) | Strength | Limitations | Relevance

Format for easy comparison when reviewing multiple papers on the same topic.
```

#### Workflow-Ready Prompt Chains

For your app, consider enabling chained prompts that build on each other:
Chain A: Literature → Grant Development

1. Run Prompt #2 (Quick Summary)
2. Run Prompt #7 (Gap Identification)
3. Run Prompt #9 (Grant Elements)
4. Run Prompt #11 (Evidence Strength)
   Chain B: Critical Evaluation
5. Run Prompt #3 (Methodology Assessment)
6. Run Prompt #5 (Spin Detection)
7. Run Prompt #12 (Author Credibility)
8. Run Prompt #11 (Overall Quality Rating)
   Chain C: Comparative Synthesis (Multiple papers)
9. Run Prompt #1 (Comprehensive Analysis) on each paper
10. Run Prompt #8 (Cross-Paper Synthesis)
11. Run Prompt #7 (Gap Identification)
12. Run Prompt #14 (Tabular Summary)

#### Implementation Recommendations

For your scientific library app, I'd suggest:
Quick Access Tier (Single click, <1 minute output):

- Quick Summary (Prompt #2)
- Paper Tagging (Prompt #13)
- Key Questions (Generate 3 essential questions)
  Deep Dive Tier (User-initiated, 5-10 minute workflows):
- Comprehensive Analysis (Prompt #1)
- Critical Appraisal (Prompt #4)
- Gap Identification (Prompt #7)
  Advanced Research Tier (Comparative/Synthesis):
- Cross-Paper Synthesis (Prompt #8)
- Grant Element Extraction (Prompt #9)
- Evidence Strength Rating (Prompt #11)
  Customization Features:
- Allow users to specify their research domain/context for contextually-relevant outputs
- Support chaining of prompts with results feeding into subsequent analyses
- Enable role-based templates (clinician, policy maker, researcher, educator)
- Build in citation export functionality to preserve provenance
- Create comparison views showing multiple papers side-by-side with standard prompts applied
  This approach balances comprehensiveness with usability, letting users engage papers at their preferred depth while maintaining academic rigor suitable for your health research context at Purpose Africa.
  Sources
  [1] 40+ AI Research Prompts To Help You Write Better Papers https://columncontent.com/ai-research-prompts/
  [2] Top AI Prompts for Literature Review https://clickup.com/p/ai-prompts/literature-review
  [3] Examples of Prompts https://www.promptingguide.ai/introduction/examples
  [4] Two useful prompts for research/academic papers. https://www.reddit.com/r/ChatGPTPromptGenius/comments/1j76mfo/two_useful_prompts_for_researchacademic_papers/
  [5] literature review prompts i use this prompt to make the AI lists the literature for me, it will give you only for but you can simply ask him to continue https://www.reddit.com/r/ChatGPTPromptGenius/comments/11orvrq/literature_review_prompts_i_use_this_prompt_to/
  [6] Getting started with prompts for text-based Generative AI ... https://www.huit.harvard.edu/news/ai-prompts
  [7] 15 ChatGPT Prompts for Academic Writing https://www.godofprompt.ai/blog/chatgpt-prompts-for-academic-writing
  [8] How to Craft Prompts - AI-Based Literature Review Tools https://tamu.libguides.com/c.php?g=1289555&p=9642751
  [9] Effective Prompts for AI: The Essentials https://mitsloanedtech.mit.edu/ai/basics/effective-prompts/
  [10] 15 Essential Prompts, Research analysis tool, Literature ... https://researchcollab.ai/resources/prompting-guides-part-1-15-prompts/
  [11] Best AI Prompts for Scientific Literature Review https://clickup.com/p/ai-prompts/scientific-literature-review
  [12] 50+ Tested System Prompts That Work Across AI Models in ... https://chatlyai.app/blog/best-system-prompts-for-everyone
  [13] 10 Powerful Gemini Prompts for Academic Research https://chuahkeeman.substack.com/p/10-powerful-gemini-prompts-for-academic
  [14] 20+ Best ChatGPT Prompts for Research & Writing — Otio Blog https://otio.ai/blog/chatgpt-prompts-for-research
  [15] dontriskit/awesome-ai-system-prompts: 🧠 Curated ... https://github.com/dontriskit/awesome-ai-system-prompts
  [16] Dissecting the literature: the importance of critical appraisal https://www.rcseng.ac.uk/library-and-publications/library/blog/dissecting-the-literature/
  [17] AI-Assisted Annotation: scaling human-led prompt ... https://centific.com/blog/ai-assisted-annotation-scaling-human-led-prompt-generation-across-13-languages-using-llm-as-a-judge
  [18] Writing a Systematic Review and Meta-analysis: A Step-by ... https://pmc.ncbi.nlm.nih.gov/articles/PMC12402582/
  [19] Critical Appraisal Questionnaires for Scientific Evidence https://cebma.org/resources/tools/critical-appraisal-questionnaires/
  [20] Easily read, annotate, understand research papers with AI. ... https://www.reddit.com/r/MLQuestions/comments/1k69dx1/easily_read_annotate_understand_research_papers/
  [21] Types of Reviews - Systematic Reviews - Guides https://guides.mclibrary.duke.edu/sysreview/types
  [22] Critical Appraisal for Research Papers https://www.nuhs.edu/media/25485/studyguide-criticalappraisalforresearchpapers.pdf
  [23] Leveraging Prompt-Based Annotation https://keylabs.ai/blog/leveraging-prompt-based-annotation-with-large-language-models/
  [24] How to critically appraise a systematic review - Oxford Academic https://academic.oup.com/ced/article/48/8/854/7147030
  [25] How to Critically Appraise a Research Paper - CASP https://casp-uk.net/news/how-to-critically-appraise-a-research-paper/
  [26] Prodigy · An annotation tool for AI, Machine Learning & NLP https://prodi.gy
  [27] Step 1: Understanding Systematic Reviews https://yorkvilleu.libguides.com/systematic-reviews
  [28] Critical appraisal of a journal article https://cinj.org/sites/cinj/files/documents/CriticalAppraisalOfAJournalArticle.pdf
  [29] Prompt Selection Matters: Enhancing Text Annotations for … https://arxiv.org/html/2407.10645v1
  [30] Writing a Systematic Review and Meta-analysis: A Step-by- … https://macupperextremity.ca/publications/writing-a-systematic-review-and-meta-analysis-a-step-by-step-guide/
