# UI Integration Plan for v2.0 Features (Podcasts, Summaries, Exports)

## Current v2 Status
✅ Database tables created (podcasts, summaries, infographics, slide_decks)
✅ User API keys added (openrouter, openai, elevenlabs, default_openrouter_model)
✅ Service architecture documented (BYOK + smart TTS optimization)
✅ V1 fixes merged (auth improvements, thumbnail generation, hydration fixes)

⚠️ Git push blocked by false positive Stripe secret detection - can work locally

---

## Recommended UI Locations for v2.0 Features

### 1. 🎯 Primary Location: Individual Paper Detail Page

**File**: `frontend/nextjs-app/app/papers/[paperId]/page.tsx`

**Why Here**: 
- Most natural place to "do something" with a paper
- User is already engaged with the content
- Context is clear (this specific paper)

**UI Addition**: Right sidebar "Generate Content" panel

```tsx
// New component: components/papers/GenerateContentPanel.tsx

<Card className="generate-content-panel">
  <CardHeader>
    <h3>Generate from This Paper</h3>
  </CardHeader>
  <CardContent>
    <div className="action-buttons">
      <Button 
        icon={<Mic />} 
        onClick={handlePodcast}
        variant="primary"
      >
        🎙️ Generate Podcast
        <span className="subtitle">AI discussion of this paper</span>
      </Button>
      
      <Dropdown>
        <DropdownTrigger>
          <Button icon={<FileText />}>
            📝 Generate Summary
          </Button>
        </DropdownTrigger>
        <DropdownMenu>
          <DropdownItem value="lay">For General Audience</DropdownItem>
          <DropdownItem value="technical">For Peer Researchers</DropdownItem>
          <DropdownItem value="executive">For Decision Makers</DropdownItem>
        </DropdownMenu>
      </Dropdown>
      
      <Button icon={<BarChart />} onClick={handleInfographic}>
        📊 Create Infographic
      </Button>
      
      <Button icon={<Presentation />} onClick={handleSlides}>
        📑 Generate Slides
      </Button>
    </div>
    
    {/* Show generated content */}
    {generatedPodcast && (
      <PodcastPlayer podcast={generatedPodcast} />
    )}
    
    {generatedSummary && (
      <SummaryDisplay summary={generatedSummary} />
    )}
  </CardContent>
</Card>
```

**Layout Integration**:
```
┌─────────────────────────────────────────────────────┐
│ Climate Change and Agriculture (2024)     [← Back] │
├───────────────────────────────────┬─────────────────┤
│                                   │                 │
│  [PDF Viewer]                     │ [Annotations]   │
│                                   │                 │
│  Page 1 of 24                     │ • Highlight 1   │
│                                   │ • Note 1        │
│  [Full document text...]          │                 │
│                                   ├─────────────────┤
│                                   │ [Generate]      │ ← NEW
│                                   │                 │
│                                   │ 🎙️ Podcast     │
│                                   │ 📝 Summary      │
│                                   │ 📊 Infographic  │
│                                   │ 📑 Slides       │
│                                   │                 │
└───────────────────────────────────┴─────────────────┘
```

---

### 2. 📚 Secondary Location: Multi-Paper Selection (Search Space / Library)

**File**: `frontend/nextjs-app/app/search-spaces/[spaceId]/page.tsx` or Library view

**Why Here**:
- Comparative analysis across multiple papers
- Synthesize findings from literature review
- Create comprehensive summaries

**UI Addition**: Bulk actions toolbar

```tsx
// Update: components/library/BulkActions.tsx

<div className="bulk-actions-toolbar">
  {selectedPapers.length > 0 && (
    <>
      <span className="selection-count">
        {selectedPapers.length} papers selected
      </span>
      
      {/* Existing actions */}
      <ButtonGroup>
        <Button icon={<Tag />}>Tag</Button>
        <Button icon={<Trash />}>Delete</Button>
        <Button icon={<Download />}>Export</Button>
      </ButtonGroup>
      
      {/* NEW: v2.0 Generate actions */}
      <Separator />
      
      <Dropdown>
        <DropdownTrigger>
          <Button variant="primary">
            ✨ Generate from Selection
          </Button>
        </DropdownTrigger>
        <DropdownMenu>
          <DropdownItem 
            icon={<Mic />} 
            onClick={() => handleBulkPodcast(selectedPapers)}
          >
            🎙️ Podcast Discussion
            <span className="item-desc">
              AI hosts discuss and compare papers
            </span>
          </DropdownItem>
          
          <DropdownItem 
            icon={<FileText />}
            onClick={() => handleBulkSummary(selectedPapers)}
          >
            📝 Comparative Summary
            <span className="item-desc">
              Synthesize key findings across papers
            </span>
          </DropdownItem>
          
          <DropdownItem 
            icon={<Presentation />}
            onClick={() => handleBulkSlides(selectedPapers)}
          >
            📑 Literature Review Deck
            <span className="item-desc">
              Present findings as slides
            </span>
          </DropdownItem>
        </DropdownMenu>
      </Dropdown>
    </>
  )}
</div>
```

**Visual Layout**:
```
┌─────────────────────────────────────────────────────┐
│ Search Space: Climate Research                      │
├─────────────────────────────────────────────────────┤
│ ☑ 5 papers selected                                │
│ [Tag] [Delete] [Export] │ [✨ Generate from Selection ▼] │ ← NEW
│                                                     │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│ │ Paper 1  │ │ Paper 2  │ │ Paper 3  │           │
│ │ Smith    │ │ Jones    │ │ Lee      │           │
│ │ 2024  ✓  │ │ 2023  ✓  │ │ 2024  ✓  │           │
│ └──────────┘ └──────────┘ └──────────┘           │
└─────────────────────────────────────────────────────┘
```

---

### 3. 📂 Tertiary Location: Generated Content Library/History

**New Page**: `frontend/nextjs-app/app/generated/page.tsx`

**Why**:
- Central place to view all generated content
- Re-access podcasts, summaries, slides
- Track generation history
- Manage generated assets

**UI Structure**:
```tsx
// app/generated/page.tsx

<DashboardLayout>
  <PageHeader>
    <h1>Generated Content</h1>
    <p>Podcasts, summaries, and exports from your library</p>
  </PageHeader>
  
  <Tabs>
    <TabsList>
      <Tab value="podcasts">🎙️ Podcasts</Tab>
      <Tab value="summaries">📝 Summaries</Tab>
      <Tab value="infographics">📊 Infographics</Tab>
      <Tab value="slides">📑 Slide Decks</Tab>
    </TabsList>
    
    <TabContent value="podcasts">
      <PodcastGrid podcasts={userPodcasts}>
        {podcasts.map(podcast => (
          <PodcastCard 
            key={podcast.id}
            title={podcast.title}
            duration={podcast.duration_seconds}
            sourcePapers={podcast.source_paper_ids}
            createdAt={podcast.created_at}
            audioSrc={podcast.file_location}
            transcript={podcast.podcast_transcript}
          />
        ))}
      </PodcastGrid>
    </TabContent>
    
    {/* Similar for other tabs */}
  </Tabs>
</DashboardLayout>
```

**Visual Layout**:
```
┌─────────────────────────────────────────────────────┐
│ Generated Content                                    │
├─────────────────────────────────────────────────────┤
│ [🎙️ Podcasts] [📝 Summaries] [📊 Infographics] [📑 Slides] │
├─────────────────────────────────────────────────────┤
│                                                     │
│ ┌─────────────────────────────────────────────┐   │
│ │ 🎙️ Climate Policy Discussion               │   │
│ │ Duration: 12:34 • 3 papers • 2 days ago    │   │
│ │ [▶️ Play] [📄 Transcript] [⬇️ Download]    │   │
│ └─────────────────────────────────────────────┘   │
│                                                     │
│ ┌─────────────────────────────────────────────┐   │
│ │ 🎙️ Machine Learning Ethics                 │   │
│ │ Duration: 8:15 • 5 papers • 1 week ago     │   │
│ │ [▶️ Play] [📄 Transcript] [⬇️ Download]    │   │
│ └─────────────────────────────────────────────┘   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

### 4. ⚙️ Settings Integration: API Keys & Model Selection

**File**: `frontend/nextjs-app/app/profile/page.tsx` (already exists)

**Current**: Has OpenRouter API key field

**Enhancement Needed**: Add new TTS keys and model preferences

```tsx
// Update: components/layout/APIKeySettings.tsx

<Card title="AI Service Configuration">
  <Form>
    {/* Existing */}
    <FormField
      label="OpenRouter API Key"
      name="openrouter_api_key"
      type="password"
      help="One key for 100+ LLMs (GPT-4, Claude, Gemini, etc.)"
      value={user.openrouter_api_key}
    />
    
    {/* NEW: Model selection */}
    <FormField
      label="Default LLM Model"
      name="default_openrouter_model"
      type="select"
      help="Used for podcast transcripts and summaries"
      options={[
        { value: 'anthropic/claude-sonnet-4-20250514', label: 'Claude Sonnet 4 (Recommended)' },
        { value: 'openai/gpt-4o-mini', label: 'GPT-4o Mini (Budget)' },
        { value: 'openai/gpt-4o', label: 'GPT-4o (Premium)' },
        { value: 'anthropic/claude-opus-4.1-20250514', label: 'Claude Opus 4.1 (Best Quality)' },
        { value: 'google/gemini-2.0-flash-exp:free', label: 'Gemini Flash (Free)' }
      ]}
      value={user.default_openrouter_model}
    />
    
    <Separator />
    
    {/* NEW: TTS Configuration */}
    <SectionHeader>
      <h3>Voice Synthesis (Optional)</h3>
      <p>For podcast audio generation</p>
    </SectionHeader>
    
    <FormField
      label="Voice Provider"
      name="tts_optimization_mode"
      type="select"
      options={[
        { value: 'auto', label: 'Auto (Cheapest option)' },
        { value: 'kokoro_only', label: 'Free (Kokoro - Local)' },
        { value: 'prefer_openai', label: 'OpenAI TTS' },
        { value: 'prefer_elevenlabs', label: 'ElevenLabs (Premium)' }
      ]}
      value={user.tts_optimization_mode}
    />
    
    {user.tts_optimization_mode !== 'kokoro_only' && (
      <>
        <FormField
          label="OpenAI API Key (Optional)"
          name="openai_api_key"
          type="password"
          help="For OpenAI TTS ($15/1M chars, pay-per-use)"
          value={user.openai_api_key}
        />
        
        <FormField
          label="ElevenLabs API Key (Optional)"
          name="elevenlabs_api_key"
          type="password"
          help="For premium voices ($5-99/month subscription)"
          value={user.elevenlabs_api_key}
        />
      </>
    )}
    
    {/* Cost estimate */}
    {user.openrouter_api_key && (
      <CostEstimate>
        <p>Estimated cost per podcast:</p>
        <ul>
          <li>Transcript: ~$0.06-0.14 (varies by model)</li>
          <li>Audio: {getTTSCost(user.tts_optimization_mode)}</li>
        </ul>
      </CostEstimate>
    )}
    
    <Button type="submit">Save Settings</Button>
  </Form>
</Card>
```

---

### 5. 🔔 Navigation Updates

**File**: `frontend/nextjs-app/components/layout/Sidebar.tsx`

**Add New Menu Item**:
```tsx
const menuItems = [
  { icon: <Home />, label: 'Dashboard', href: '/dashboard' },
  { icon: <Library />, label: 'Library', href: '/library' },
  { icon: <Search />, label: 'Search Spaces', href: '/search-spaces' },
  { icon: <Star />, label: 'Favorites', href: '/favorites' },
  
  // NEW: Generated content section
  { 
    icon: <Sparkles />, 
    label: 'Generated', 
    href: '/generated',
    badge: newGeneratedCount > 0 ? newGeneratedCount : null
  },
  
  { icon: <Settings />, label: 'Settings', href: '/profile' }
];
```

---

## Component Architecture

### New Components Needed

```
frontend/nextjs-app/components/
├── generated/
│   ├── PodcastCard.tsx              # Display podcast with player
│   ├── PodcastPlayer.tsx            # Audio player + transcript
│   ├── PodcastGenerationModal.tsx   # Configuration modal
│   ├── SummaryCard.tsx              # Display summary
│   ├── SummaryDisplay.tsx           # Formatted summary view
│   ├── InfographicCard.tsx          # Display infographic
│   └── SlideDeckCard.tsx            # Display slide deck
│
├── papers/
│   ├── GenerateContentPanel.tsx     # Right sidebar panel (NEW)
│   └── GenerationStatus.tsx         # Progress indicator (NEW)
│
└── library/
    └── BulkGenerateActions.tsx      # Bulk generation UI (UPDATE)
```

### API Routes Needed

```
frontend/nextjs-app/app/api/
├── podcasts/
│   ├── route.ts                     # GET /api/podcasts (list user's podcasts)
│   ├── generate/
│   │   └── route.ts                 # POST /api/podcasts/generate
│   └── [podcastId]/
│       ├── route.ts                 # GET/DELETE /api/podcasts/:id
│       └── download/
│           └── route.ts             # GET /api/podcasts/:id/download
│
├── summaries/
│   ├── route.ts                     # GET /api/summaries
│   ├── generate/
│   │   └── route.ts                 # POST /api/summaries/generate
│   └── [summaryId]/
│       └── route.ts                 # GET/DELETE /api/summaries/:id
│
└── generated/
    └── route.ts                     # GET /api/generated (all types combined)
```

---

## User Flow Examples

### Flow 1: Single Paper Podcast

```
1. User clicks on paper → Paper detail page
2. Sees "Generate Content" panel in right sidebar
3. Clicks "🎙️ Generate Podcast"
4. Modal appears:
   ┌─────────────────────────────┐
   │ Generate Podcast            │
   ├─────────────────────────────┤
   │ Model: [Claude Sonnet 4 ▼] │
   │ (Using your settings)       │
   │                             │
   │ Voices: [Kokoro (Free) ▼]  │
   │                             │
   │ Est. cost: ~$0.14          │
   │ Est. time: 2-3 minutes     │
   │                             │
   │ [Cancel] [Generate]         │
   └─────────────────────────────┘
5. Shows progress: "Generating transcript..." → "Creating audio..." → "Done!"
6. Auto-plays podcast in panel
7. Can download, view transcript, share
```

### Flow 2: Multi-Paper Comparative Summary

```
1. User in Search Space "Climate Research"
2. Selects 5 papers using checkboxes
3. Clicks "✨ Generate from Selection" → "📝 Comparative Summary"
4. Modal shows paper list + summary type selector
5. Generates summary comparing all 5 papers
6. Shows in-page, with export options (PDF, DOCX, MD)
```

### Flow 3: Browse Generated Content History

```
1. User clicks "Generated" in sidebar
2. Sees tabs: Podcasts | Summaries | Infographics | Slides
3. Grid of cards showing all generated content
4. Can search, filter by date, source papers
5. Click podcast card → Plays inline with transcript
6. Click summary card → Opens full text view
7. All items have [Download] [Delete] [Share] options
```

---

## Mobile Considerations

### Paper Detail Page (Mobile)
- "Generate Content" becomes bottom sheet/drawer
- Swipe up to reveal options
- Full-screen podcast player on tap

### Bulk Actions (Mobile)
- Selection mode with floating action button (FAB)
- FAB expands to show generation options
- Simplified modal for mobile form factors

---

## Accessibility

- All buttons have proper ARIA labels
- Podcast player keyboard navigable
- Transcript synchronized with audio (click to seek)
- Generated content cards have semantic HTML
- Loading states clearly communicated
- Error states actionable (e.g., "Add API key in settings")

---

## Next Steps

### Phase 1: Backend Services (In Progress)
✅ Database tables
✅ API key management
⬜ TTS service implementation
⬜ Podcast generation workflow
⬜ Summary generation workflow

### Phase 2: Frontend Components (Next)
⬜ GenerateContentPanel component
⬜ PodcastPlayer component
⬜ Generation status indicators
⬜ API integration

### Phase 3: Full Integration
⬜ Settings page updates
⬜ Generated content library page
⬜ Bulk actions UI
⬜ Mobile optimization

---

**Created**: 2025-01-04  
**Status**: Ready for frontend implementation  
**Recommended Start**: GenerateContentPanel in paper detail page
