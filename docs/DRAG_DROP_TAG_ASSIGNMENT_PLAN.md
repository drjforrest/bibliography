# Drag-and-Drop Tag Assignment Feature - Implementation Plan

## Overview
Implement drag-and-drop functionality allowing users to drag BookCards from the main grid to sidebar topic tags, automatically assigning the tag to the paper. Tags will be color-coded based on the paper's `literature_type`.

## Feature Requirements

### Core Functionality
1. **Drag Source**: BookCard components in the main grid/list view
2. **Drop Target**: Topic/Tag items in the left sidebar
3. **Action**: When a BookCard is dropped on a tag, assign that tag to the paper
4. **Visual Feedback**: 
   - Show drag preview while dragging
   - Highlight drop zones when dragging over them
   - Color-code tags based on literature_type of papers they contain

### Color Coding
Tags in the sidebar should be color-coded based on the `literature_type` of papers they contain:
- **PEER_REVIEWED**: `bg-[#4e989e]/20 text-[#4e989e] dark:bg-[#4e989e]/30 dark:text-[#94d2bd]`
- **GREY_LITERATURE**: `bg-[#e86530]/20 text-[#e86530] dark:bg-[#e86530]/30 dark:text-[#e86530]`
- **NEWS**: `bg-[#cc9900]/20 text-[#cc9900] dark:bg-[#cc9900]/30 dark:text-[#cc9900]`

**Note**: If a tag contains papers of multiple literature types, we need to decide on a display strategy (e.g., show dominant type, or use a neutral color).

## Technical Implementation Plan

### Phase 1: Dependencies & Setup

#### 1.1 Install Drag-and-Drop Library
- **Library**: `@dnd-kit/core`, `@dnd-kit/utilities`, `@dnd-kit/sortable`
- **Rationale**: Modern, accessible, performant drag-and-drop library for React
- **Command**: `pnpm add @dnd-kit/core @dnd-kit/utilities @dnd-kit/sortable`

#### 1.2 Type Definitions
- Add TypeScript types for drag-and-drop if needed (usually included with @dnd-kit)

### Phase 2: Backend Enhancements (if needed)

#### 2.1 Tag Assignment API
- **Status**: ✅ Already exists
- **Endpoint**: `POST /api/v1/tags/papers/{paper_id}/tags/{tag_id}`
- **Location**: `backend/app/routes/tags_routes.py:233-259`
- **Action**: Verify endpoint handles duplicate tag assignment gracefully (returns success message if tag already applied)

#### 2.2 Tag Color Calculation (Optional Enhancement)
- **Enhancement**: Add endpoint or modify existing to return dominant `literature_type` per tag
- **Purpose**: Determine which color to use for tags containing mixed literature types
- **Alternative**: Calculate on frontend based on papers in each tag

### Phase 3: Frontend Component Updates

#### 3.1 BookCard Component (`frontend/nextjs-app/components/library/BookCard.tsx`)

**Changes Required**:
1. Make BookCard draggable
   - Add `draggable` attribute or use `@dnd-kit` `useDraggable` hook
   - Store paper data in drag data transfer
   - Add visual feedback (opacity change, cursor change) when dragging

2. Prevent navigation during drag
   - Disable Link click during drag operation
   - Ensure drag doesn't trigger navigation

3. Add drag handle indicator (optional)
   - Small icon or visual cue that card is draggable
   - Could use Material Symbols icon: `drag_indicator`

**Implementation Details**:
```typescript
// Use @dnd-kit's useDraggable hook
import { useDraggable } from '@dnd-kit/core';

// In BookCard component:
const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
  id: `paper-${paper.id}`,
  data: {
    type: 'paper',
    paper: paper,
  },
});

// Apply transform and opacity when dragging
const style = {
  transform: CSS.Transform.toString(transform),
  opacity: isDragging ? 0.5 : 1,
};
```

#### 3.2 Sidebar Component (`frontend/nextjs-app/components/layout/Sidebar.tsx`)

**Changes Required**:
1. Make tag items droppable
   - Use `@dnd-kit` `useDroppable` hook for each tag
   - Handle drop events to assign tag to paper

2. Add visual feedback for drop zones
   - Highlight tag when dragging over it
   - Show visual indicator (border, background change)
   - Use appropriate color based on literature_type

3. Display all tags (not just first 3)
   - Remove `.slice(0, 3)` limitation
   - Add scrollable container if needed
   - Consider pagination or "show more" if tag list is very long

4. Color-code tags based on literature_type
   - Calculate dominant literature_type for each tag
   - Apply appropriate color classes from `LITERATURE_TYPE_COLORS`
   - Handle mixed types (show dominant or neutral color)

**Implementation Details**:
```typescript
// Use @dnd-kit's useDroppable hook
import { useDroppable } from '@dnd-kit/core';

// For each tag:
const { setNodeRef, isOver } = useDroppable({
  id: `tag-${tag.id}`,
});

// Apply highlight when dragging over
const dropZoneStyle = {
  backgroundColor: isOver ? 'rgba(78, 152, 158, 0.2)' : 'transparent',
  border: isOver ? '2px dashed #4e989e' : 'none',
};
```

#### 3.3 DnD Context Provider

**New Component**: Wrap pages with DnD context
- Create `DndContext` provider in page components (or layout)
- Handle `onDragEnd` event to process tag assignment
- Call API to assign tag to paper
- Show success/error feedback

**Location**: Add to pages that use BookGrid + Sidebar:
- `frontend/nextjs-app/app/page.tsx` (HomePage)
- `frontend/nextjs-app/app/topics/page.tsx`
- `frontend/nextjs-app/app/favorites/page.tsx`
- `frontend/nextjs-app/app/recent/page.tsx`

**Implementation**:
```typescript
import { DndContext, DragEndEvent } from '@dnd-kit/core';

// In page component:
const handleDragEnd = async (event: DragEndEvent) => {
  const { active, over } = event;
  
  if (!over) return; // Dropped outside any drop zone
  
  const paperId = parseInt(active.id.toString().replace('paper-', ''));
  const tagId = parseInt(over.id.toString().replace('tag-', ''));
  
  try {
    await api.addTagToPaper(paperId, tagId);
    // Show success feedback
    // Optionally refresh papers/tags to show updated state
  } catch (error) {
    // Show error feedback
    console.error('Failed to assign tag:', error);
  }
};

// Wrap content:
<DndContext onDragEnd={handleDragEnd}>
  <Sidebar topics={topics} />
  <BookGrid papers={papers} />
</DndContext>
```

#### 3.4 Tag Color Calculation Logic

**New Utility Function**: Calculate tag colors based on papers
- Fetch papers for each tag (or use existing paper_count data)
- Determine dominant `literature_type` among papers in tag
- Return appropriate color class

**Options**:
1. **Backend Enhancement**: Add `dominant_literature_type` to tag hierarchy response
2. **Frontend Calculation**: Fetch papers per tag and calculate on frontend
3. **Hybrid**: Use cached data if available, otherwise calculate

**Recommendation**: Start with frontend calculation, optimize later if needed.

**Implementation Location**: 
- New file: `frontend/nextjs-app/lib/tagColors.ts`
- Or utility function in Sidebar component

### Phase 4: User Experience Enhancements

#### 4.1 Visual Feedback
- **Drag Preview**: Show paper thumbnail/title while dragging
- **Drop Zone Highlighting**: Clear visual indication of valid drop targets
- **Success Feedback**: Toast notification or inline message when tag assigned
- **Error Handling**: Clear error messages if assignment fails

#### 4.2 Accessibility
- **Keyboard Support**: Ensure drag-and-drop works with keyboard navigation
- **Screen Reader**: Add ARIA labels for drag/drop operations
- **Focus Management**: Maintain focus after drag operation

#### 4.3 Performance Considerations
- **Lazy Loading**: Only load tag colors when needed
- **Debouncing**: Debounce API calls if multiple rapid drags occur
- **Optimistic Updates**: Update UI immediately, rollback on error

### Phase 5: Testing & Refinement

#### 5.1 Testing Checklist
- [ ] Drag BookCard from grid view
- [ ] Drag BookCard from list view
- [ ] Drop on parent tag
- [ ] Drop on child tag
- [ ] Drop outside valid zone (should cancel)
- [ ] Assign tag to paper that already has tag (should handle gracefully)
- [ ] Color coding displays correctly for each literature_type
- [ ] Mixed literature_type tags display appropriately
- [ ] Works on mobile/touch devices
- [ ] Keyboard navigation works
- [ ] Screen reader announces operations

#### 5.2 Edge Cases
- **Empty Tags**: Tags with no papers (use neutral color)
- **Mixed Types**: Tags containing multiple literature types
- **Very Long Tag Lists**: Performance with 100+ tags
- **Concurrent Drags**: Multiple users dragging simultaneously (if applicable)

## File Changes Summary

### New Files
1. `frontend/nextjs-app/lib/tagColors.ts` - Utility for calculating tag colors
2. `frontend/nextjs-app/components/dnd/DndProvider.tsx` - Optional wrapper component

### Modified Files
1. `frontend/nextjs-app/components/library/BookCard.tsx`
   - Add drag functionality
   - Add drag visual feedback
   - Prevent navigation during drag

2. `frontend/nextjs-app/components/layout/Sidebar.tsx`
   - Add drop functionality to tags
   - Add color coding based on literature_type
   - Remove `.slice(0, 3)` limitation
   - Add drop zone visual feedback

3. `frontend/nextjs-app/app/page.tsx`
   - Add DndContext provider
   - Add drag end handler
   - Add tag color calculation logic

4. `frontend/nextjs-app/app/topics/page.tsx`
   - Add DndContext provider
   - Add drag end handler

5. `frontend/nextjs-app/app/favorites/page.tsx`
   - Add DndContext provider
   - Add drag end handler

6. `frontend/nextjs-app/app/recent/page.tsx`
   - Add DndContext provider
   - Add drag end handler

7. `frontend/nextjs-app/package.json`
   - Add @dnd-kit dependencies

### Backend Files (No changes needed)
- Tag assignment API already exists and works correctly

## Implementation Order

1. **Phase 1**: Install dependencies and set up basic DnD context
2. **Phase 2**: Make BookCard draggable with visual feedback
3. **Phase 3**: Make Sidebar tags droppable with visual feedback
4. **Phase 4**: Implement tag assignment API call on drop
5. **Phase 5**: Add color coding based on literature_type
6. **Phase 6**: Enhance UX with better feedback and error handling
7. **Phase 7**: Testing and refinement

## Success Criteria

✅ Users can drag BookCards from main view to sidebar tags
✅ Dropping a card assigns the tag to the paper
✅ Tags are color-coded based on literature_type
✅ Visual feedback is clear and intuitive
✅ Works across all pages with BookGrid + Sidebar
✅ Handles errors gracefully
✅ Accessible via keyboard and screen readers
✅ Performance is acceptable with large tag lists

## Open Questions / Decisions Needed

1. **Mixed Literature Types**: How should tags with mixed types be displayed?
   - Option A: Show dominant type color
   - Option B: Show neutral/default color
   - Option C: Show striped/multi-color indicator
   - **Recommendation**: Option A (dominant type)

2. **Tag List Display**: Should all tags be shown or keep pagination?
   - **Recommendation**: Show all tags with scrollable container

3. **Tag Color Calculation**: Backend vs Frontend?
   - **Recommendation**: Start with frontend, optimize to backend if needed

4. **Success Feedback**: Toast notification vs inline message?
   - **Recommendation**: Subtle toast notification (non-intrusive)

5. **Mobile Support**: Should drag-and-drop work on touch devices?
   - **Recommendation**: Yes, @dnd-kit supports touch events

## Estimated Effort

- **Phase 1-2**: 2-3 hours (Dependencies + BookCard drag)
- **Phase 3**: 2-3 hours (Sidebar drop zones)
- **Phase 4**: 1-2 hours (API integration)
- **Phase 5**: 2-3 hours (Color coding logic)
- **Phase 6**: 2-3 hours (UX polish)
- **Phase 7**: 2-3 hours (Testing & fixes)

**Total**: ~12-18 hours

## Notes

- The existing tag assignment API (`POST /api/v1/tags/papers/{paper_id}/tags/{tag_id}`) already handles duplicate assignments gracefully (returns success message if tag already applied)
- Literature type colors are already defined in `types/index.ts` - reuse these constants
- Tag hierarchy is already fetched and displayed in Sidebar - just need to enhance with drop functionality
- Consider adding a "recently assigned tags" indicator or animation for better UX
