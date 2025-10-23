# Tags System Guide

The Bibliography system now includes a comprehensive, user-specific tagging system for organizing papers. This replaces the previous mock topics with a real database-backed hierarchical tag structure.

## Overview

- **User-Specific**: Each user has their own set of tags
- **Hierarchical**: Tags support parent-child relationships for nested organization
- **Customizable**: Tags can have custom colors and icons
- **Many-to-Many**: Papers can have multiple tags, tags can apply to multiple papers

## Database Schema

### Tag Model

```python
class Tag:
    id: int
    name: str (max 100 characters)
    description: Optional[str]
    color: str (hex color code, default: #3B82F6)
    icon: Optional[str] (Material icon name)
    parent_id: Optional[int] (for hierarchical structure)
    user_id: UUID (owner of the tag)
    created_at: datetime

    # Relationships
    parent: Tag (parent tag)
    children: List[Tag] (child tags)
    papers: List[ScientificPaper] (papers with this tag)
```

### Many-to-Many Relationship

Tags and papers are linked via the `paper_tags` junction table:
- `paper_id`: Foreign key to scientific_papers
- `tag_id`: Foreign key to tags
- `created_at`: Timestamp when tag was added to paper

## Backend API Endpoints

### Tag CRUD Operations

#### Create Tag
```http
POST /api/v1/tags/
Content-Type: application/json
Authorization: Bearer <token>

{
  "name": "Machine Learning",
  "description": "Papers about ML and AI",
  "color": "#3B82F6",
  "icon": "psychology",
  "parent_id": null
}
```

#### Get All Tags
```http
GET /api/v1/tags/
GET /api/v1/tags/?parent_id=1  # Get children of a specific tag
GET /api/v1/tags/?flat=true     # Get all tags in flat list
```

#### Get Tag Hierarchy
```http
GET /api/v1/tags/hierarchy
# Returns nested tree structure with all children loaded
```

#### Get Single Tag
```http
GET /api/v1/tags/{tag_id}
```

#### Update Tag
```http
PUT /api/v1/tags/{tag_id}
Content-Type: application/json

{
  "name": "Updated Name",
  "color": "#EF4444"
}
```

#### Delete Tag
```http
DELETE /api/v1/tags/{tag_id}
# Note: Child tags will also be deleted (CASCADE)
```

#### Search Tags
```http
GET /api/v1/tags/search/query?q=machine&limit=20
```

### Paper-Tag Operations

#### Add Tag to Paper
```http
POST /api/v1/tags/papers/{paper_id}/tags/{tag_id}
```

#### Remove Tag from Paper
```http
DELETE /api/v1/tags/papers/{paper_id}/tags/{tag_id}
```

#### Get Tags for a Paper
```http
GET /api/v1/tags/papers/{paper_id}/tags
```

#### Set Paper Tags (Replace All)
```http
PUT /api/v1/tags/papers/{paper_id}/tags
Content-Type: application/json

{
  "tag_ids": [1, 3, 5]
}
```

#### Get Papers by Tag
```http
GET /api/v1/tags/{tag_id}/papers?limit=50&offset=0
```

## Frontend Integration

### TypeScript Types

```typescript
interface Tag {
  id: number;
  name: string;
  description?: string;
  color?: string;
  icon?: string;
  parent_id?: number;
  user_id: string;
  created_at: string;
  paper_count: number;
  children?: Tag[];
}

interface TagCreate {
  name: string;
  description?: string;
  color?: string;
  icon?: string;
  parent_id?: number;
}

interface TagUpdate {
  name?: string;
  description?: string;
  color?: string;
  icon?: string;
  parent_id?: number;
}
```

### API Client Methods

```typescript
// Tag management
await api.getTags({ parent_id: 1, flat: false });
await api.getTagHierarchy();
await api.getTag(tagId);
await api.createTag({ name: 'New Tag', color: '#3B82F6' });
await api.updateTag(tagId, { name: 'Updated' });
await api.deleteTag(tagId);
await api.searchTags('query', 20);

// Paper-tag operations
await api.getPaperTags(paperId);
await api.addTagToPaper(paperId, tagId);
await api.removeTagFromPaper(paperId, tagId);
await api.setPaperTags(paperId, [1, 2, 3]);
await api.getPapersByTag(tagId, 50, 0);
```

## Example Usage

### Creating a Hierarchical Tag Structure

```typescript
// Create parent tag
const csTag = await api.createTag({
  name: 'Computer Science',
  color: '#3B82F6',
  icon: 'computer'
});

// Create child tags
const mlTag = await api.createTag({
  name: 'Machine Learning',
  parent_id: csTag.id,
  color: '#10B981',
  icon: 'psychology'
});

const nlpTag = await api.createTag({
  name: 'Natural Language Processing',
  parent_id: mlTag.id,
  color: '#8B5CF6',
  icon: 'chat'
});
```

### Tagging a Paper

```typescript
// Tag a paper with multiple tags
await api.setPaperTags(paperId, [csTag.id, mlTag.id, nlpTag.id]);

// Or add individual tags
await api.addTagToPaper(paperId, mlTag.id);

// Remove a tag
await api.removeTagFromPaper(paperId, nlpTag.id);
```

### Displaying Tags

```typescript
// Get hierarchical structure for sidebar
const { tags } = await api.getTagHierarchy();

// Recursively render tags
function TagTree({ tag }: { tag: Tag }) {
  return (
    <div>
      <div style={{ color: tag.color }}>
        {tag.icon && <span className="material-symbols-outlined">{tag.icon}</span>}
        {tag.name} ({tag.paper_count})
      </div>
      {tag.children?.map(child => (
        <div key={child.id} style={{ paddingLeft: '20px' }}>
          <TagTree tag={child} />
        </div>
      ))}
    </div>
  );
}
```

## Features

### 1. Hierarchical Organization
- Create nested tag structures (e.g., CS → ML → NLP)
- Cycle prevention: Tags cannot be their own ancestors
- Cascade deletion: Deleting a parent deletes all children

### 2. Visual Customization
- Hex color codes for visual distinction
- Material Icons support
- Default blue color (#3B82F6)

### 3. Paper Counting
- Each tag includes a `paper_count` field
- Automatically calculated based on paper-tag relationships

### 4. Search and Filter
- Search tags by name
- Filter by parent to browse hierarchy
- Get flat list of all tags

### 5. Bulk Operations
- Set all tags for a paper in one operation
- Replace existing tags atomically

## Migration from Mock Topics

The old mock topics used:
```typescript
interface Topic {
  id: string;  // String ID
  name: string;
  children?: Topic[];
  paperCount?: number;
}
```

The new Tag system uses:
```typescript
interface Tag {
  id: number;  // Numeric ID
  name: string;
  parent_id?: number;  // Parent reference instead of children array
  paper_count: number;  // From database
  // + color, icon, description, etc.
}
```

### Component Updates Needed

Replace `mockTopics` with API calls:

```typescript
// Before
const [topics, setTopics] = useState(mockTopics);

// After
const [tags, setTags] = useState<Tag[]>([]);

useEffect(() => {
  async function loadTags() {
    const { tags } = await api.getTagHierarchy();
    setTags(tags);
  }
  loadTags();
}, []);
```

## Best Practices

1. **Color Coding**: Use consistent colors for related tag groups
2. **Icons**: Use descriptive Material Icons for quick visual reference
3. **Hierarchy Depth**: Keep hierarchy to 3-4 levels maximum for usability
4. **Naming**: Use clear, concise names (avoid abbreviations)
5. **Deletion**: Warn users when deleting tags with children or many papers

## Error Handling

Common errors and solutions:

- **404 Tag not found**: Tag doesn't exist or doesn't belong to user
- **400 Parent tag not found**: Invalid parent_id in create/update
- **400 Tag cannot be its own parent**: Circular reference attempt
- **400 Cannot set descendant as parent**: Would create cycle

## Performance Considerations

- Tag hierarchy loading uses `selectinload` for efficient queries
- Paper counts are calculated via SQL count queries
- Junction table has indexes on both foreign keys
- Cascade deletes handled at database level

## Testing

Example test cases:

```bash
# Create a tag
curl -X POST http://localhost:8000/api/v1/tags/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Tag","color":"#3B82F6"}'

# Get hierarchy
curl http://localhost:8000/api/v1/tags/hierarchy \
  -H "Authorization: Bearer $TOKEN"

# Tag a paper
curl -X POST http://localhost:8000/api/v1/tags/papers/1/tags/1 \
  -H "Authorization: Bearer $TOKEN"
```

## Next Steps

1. Update Sidebar component to use `api.getTagHierarchy()`
2. Create TagManager component for CRUD operations
3. Add tag filtering to paper list
4. Implement tag color picker in UI
5. Add icon selector with Material Icons
6. Create bulk tagging UI for multiple papers
