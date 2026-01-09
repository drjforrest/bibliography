# Paper Actions UX Design - Scalable Action System

**Date:** 2026-01-08  
**Goal:** Design a scalable UX pattern for paper actions that can accommodate 10+ actions without clutter

---

## Current State Analysis

### Current Implementation
1. **BookCard (Library Grid/List)**: Right-click context menu with:
   - Chat with PDF
   - Manage Tags
   - Add/Remove Favorites
   - Delete

2. **Paper Detail Page**: 
   - Recommendations button (top-right corner)
   - Annotation sidebar (right side)

### Problems
- ❌ Actions scattered across different interaction patterns
- ❌ Context menu doesn't scale well (will be cluttered with 10+ actions)
- ❌ Recommendations only on detail page, not accessible from library
- ❌ No visual hierarchy for action importance
- ❌ No grouping/organization of related actions
- ❌ No preview/description for complex actions

---

## Proposed Solution: Action Panel System

### Design Pattern: NotebookLM-Style Action Panel

**Core Concept**: A dedicated, slide-out action panel that contains all paper actions organized by category. Accessible from both library cards and detail pages.

### Key Principles

1. **Consistent Access Point**: Same action panel everywhere
2. **Category Organization**: Group related actions logically
3. **Visual Hierarchy**: Most common actions prominent, others discoverable
4. **Progressive Disclosure**: Expandable sections for less common actions
5. **Action Cards**: Visual cards with icons, titles, and descriptions
6. **Status Indicators**: Show which actions have been used/are available

---

## UI Structure

### Layout Options

#### Option A: Slide-Out Panel (Recommended)
```
┌─────────────────────────────────────────────────────────┐
│  Library / Paper Detail                                  │
│                                                           │
│  ┌─────┐                           ┌──────────────────┐ │
│  │Card │    [Click Action Button]  │  Action Panel → │ │
│  │     │                           │                  │ │
│  └─────┘                           │  ┌────────────┐ │ │
│                                    │  │ AI Actions │ │ │
│                                    │  │ ────────── │ │ │
│                                    │  │ [Card]     │ │ │
│                                    │  │ [Card]     │ │ │
│                                    │  └────────────┘ │ │
│                                    │                  │ │
│                                    │  ┌────────────┐ │ │
│                                    │  │ Organize   │ │ │
│                                    │  │ [Card]     │ │ │
│                                    │  │ [Card]     │ │ │
│                                    │  └────────────┘ │ │
│                                    └──────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

**Advantages:**
- ✅ Doesn't block main content
- ✅ Can be persistent or toggleable
- ✅ Familiar pattern (like Notion, Obsidian)
- ✅ Works well on all screen sizes

#### Option B: Modal/Dialog (Alternative)
- Full-screen overlay with action grid
- Better for mobile
- More prominent, but blocks content

---

## Action Organization

### Proposed Categories

#### 1. **AI-Powered Actions** (Primary Category)
- Find Related Papers (Recommendations)
- Generate Summary
- Create Podcast
- Generate Infographic
- Explain Concepts
- Extract Key Points
- Compare with Other Papers
- Suggest Research Questions

#### 2. **Organization** (Secondary)
- Manage Tags
- Add to Favorites
- Add to Collection/Folder
- Set Reading Status
- Add Notes

#### 3. **Sharing & Export** (Tertiary)
- Share Paper
- Export Citations
- Download PDF
- Copy Link
- Print

#### 4. **Content Actions** (Tertiary)
- Chat with PDF
- View Annotations
- View Similar Papers
- View Citation Network

#### 5. **Management** (Danger Zone)
- Delete Paper
- Archive Paper
- Report Issue

---

## Component Structure

### New Components Needed

```
components/
├── library/
│   ├── PaperActionPanel.tsx          # Main action panel component
│   ├── ActionCategory.tsx             # Category section with expand/collapse
│   ├── ActionCard.tsx                 # Individual action card
│   ├── ActionButton.tsx               # Trigger button (replaces context menu)
│   └── ActionStatusBadge.tsx          # Shows action status (completed, processing, etc.)
```

### Component Specifications

#### PaperActionPanel
- **Props**: `paper: Paper`, `isOpen: boolean`, `onClose: () => void`
- **Layout**: Fixed/sliding panel from right side
- **Sections**: Collapsible category sections
- **Scrollable**: For many actions
- **Animation**: Smooth slide-in/out

#### ActionCard
- **Props**: 
  - `action: Action`
  - `onClick: () => void`
  - `disabled?: boolean`
  - `status?: 'available' | 'processing' | 'completed'`
- **Layout**: Card with:
  - Icon (large, prominent)
  - Title
  - Description (1-2 lines)
  - Status indicator
  - Badge (e.g., "New", "Pro", "Beta")

#### ActionButton
- **Replaces**: Context menu trigger
- **Locations**: 
  - BookCard: Floating action button (hover overlay)
  - Paper Detail: Action button in header
- **Visual**: Icon button with tooltip

---

## Implementation Plan

### Phase 1: Foundation (Week 1)
1. Create `PaperActionPanel` component with basic layout
2. Create `ActionCard` component
3. Create `ActionButton` component
4. Implement panel toggle logic

### Phase 2: Migration (Week 1-2)
1. Move existing actions to panel:
   - Find Related Papers
   - Manage Tags
   - Add/Remove Favorites
   - Delete
   - Chat with PDF
2. Replace context menu with action button
3. Add action panel to both BookCard and PaperDetail

### Phase 3: Enhancements (Week 2+)
1. Add action categories
2. Implement expand/collapse
3. Add action status tracking
4. Add keyboard shortcuts
5. Add action search/filter

### Phase 4: Future Actions (As needed)
1. Generate Summary
2. Create Podcast
3. Generate Infographic
4. etc.

---

## Detailed Component Design

### ActionCard Example

```tsx
interface Action {
  id: string;
  title: string;
  description: string;
  icon: string;
  category: 'ai' | 'organize' | 'share' | 'content' | 'manage';
  onClick: () => void;
  status?: 'available' | 'processing' | 'completed' | 'disabled';
  badge?: 'new' | 'pro' | 'beta';
  keyboardShortcut?: string;
}

<ActionCard
  action={{
    id: 'find-related',
    title: 'Find Related Papers',
    description: 'Discover similar papers using Semantic Scholar',
    icon: 'auto_awesome',
    category: 'ai',
    onClick: () => openRecommendations(),
    status: 'available',
    badge: 'new',
    keyboardShortcut: 'R'
  }}
/>
```

### Visual Design

```
┌─────────────────────────────────────┐
│  ✨  Find Related Papers          [N]│
│  Discover similar papers using      │
│  Semantic Scholar                    │
│                                      │
│  [Available] ─────────────────────  │
└─────────────────────────────────────┘
```

### Category Section Example

```
┌─────────────────────────────────────┐
│  🎯 AI-Powered Actions  [Expand ▼]  │
│  ─────────────────────────────────  │
│  ┌─────────┐  ┌─────────┐          │
│  │ Action  │  │ Action  │          │
│  │  Card   │  │  Card   │          │
│  └─────────┘  └─────────┘          │
│  ┌─────────┐  ┌─────────┐          │
│  │ Action  │  │ Action  │          │
│  │  Card   │  │  Card   │          │
│  └─────────┘  └─────────┘          │
└─────────────────────────────────────┘
```

---

## Interaction Patterns

### Library View (BookCard)

**Before (Current)**:
- Right-click → Context menu

**After (Proposed)**:
- Hover over card → Action button appears (top-right)
- Click action button → Panel slides in from right
- Alternative: Keyboard shortcut (e.g., `A` for actions)

### Detail View

**Before (Current)**:
- Recommendations button in top-right
- Other actions scattered

**After (Proposed)**:
- Action button in header/toolbar
- All actions in consistent panel
- Panel can be persistent or toggleable

---

## Accessibility

- **Keyboard Navigation**: 
  - Tab through actions
  - Enter to activate
  - Escape to close panel
  - Keyboard shortcuts for common actions
- **Screen Readers**: 
  - Proper ARIA labels
  - Announce action status
  - Describe action cards
- **Focus Management**:
  - Focus trap in panel
  - Return focus on close

---

## Responsive Behavior

### Desktop (>1024px)
- Panel: 400px wide, slides from right
- Action cards: 2-column grid
- Can be persistent (not blocking)

### Tablet (768px-1024px)
- Panel: 350px wide
- Action cards: 2-column grid
- Slightly smaller cards

### Mobile (<768px)
- Panel: Full-width overlay
- Action cards: 1-column grid
- Bottom sheet style (slides from bottom)

---

## Benefits of This Approach

1. **Scalable**: Easy to add 10+ actions without clutter
2. **Discoverable**: Users see all available actions
3. **Organized**: Logical grouping makes actions easy to find
4. **Consistent**: Same experience everywhere
5. **Flexible**: Can show/hide categories, add filters
6. **Future-proof**: Ready for AI actions, badges, status tracking

---

## Migration Strategy

### Step 1: Create Components (No Breaking Changes)
- Build new components alongside existing ones
- Add action button as optional overlay

### Step 2: Dual Support
- Keep context menu, add action panel
- Allow users to choose or use both

### Step 3: Make Primary
- Make action panel primary interaction
- Keep context menu as alternative
- Add user preference toggle

### Step 4: Deprecate (Future)
- Remove context menu (if desired)
- Action panel becomes sole method

---

## Next Steps

1. **Review & Approve Design** ✅
2. **Create Component Scaffolding** 
   - PaperActionPanel.tsx
   - ActionCard.tsx
   - ActionButton.tsx
3. **Migrate Existing Actions**
   - Recommendations
   - Tags
   - Favorites
   - Delete
   - Chat
4. **Add Action Categories**
5. **Test & Iterate**

---

## Questions to Consider

1. **Panel Position**: Right side (recommended) vs left side?
2. **Default State**: Closed (toggle) vs open (persistent)?
3. **Animation**: Slide, fade, or instant?
4. **Categories**: Pre-defined or user-customizable?
5. **Search**: Add search/filter for many actions?

---

This design provides a solid foundation that can scale from 4 actions to 40+ without UX degradation.
