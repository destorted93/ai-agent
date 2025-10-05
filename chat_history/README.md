# Chat History Management System

## Overview

The chat history system now uses a **wrapped format** that adds metadata to each conversation entry. This allows for better tracking, management, and selective deletion of chat history entries without breaking OpenAI API compatibility.

## New Format Structure

Each entry in `chat_history.json` is now wrapped with metadata:

```json
{
  "id": "unique-uuid-here",
  "ts": "2025-10-05T14:59:15.123456",
  "type": "user",
  "size": 1234,
  "content": {
    "role": "user",
    "content": [
      {"type": "input_text", "text": "User's message here"}
    ]
  }
}
```

### Metadata Fields

- **id**: Unique UUID for this entry (generated automatically)
- **ts**: ISO 8601 timestamp when entry was created
- **type**: Entry type (see below for list of types)
- **size**: Size of the content in bytes
- **content**: The original OpenAI message object (unchanged)

### Entry Types

The `type` field reflects the actual content type, not the role:

- **input_text**: User messages (role: user, content[0].type: input_text)
- **output_text**: Assistant text responses (role: assistant, content[0].type: output_text)
- **reasoning**: AI thinking process (type: reasoning at top level)
- **function_call**: Tool/function calls (type: function_call at top level)
- **function_call_output**: Tool/function results (type: function_call_output at top level)
- **message**: Complete assistant message objects (type: message at top level)

Note: We store types, not roles, because reasoning and function calls don't have roles.

## Why This Design?

1. **OpenAI Compatibility**: The `content` field remains exactly as OpenAI expects it
2. **Tracking**: Each entry has a unique ID for reference and management
3. **Management**: Can selectively delete or analyze entries by ID
4. **Analytics**: Track conversation size, types, and growth over time
5. **Backwards Compatible**: Automatic migration from old format

## Migration

### Automatic Migration

The `ChatHistoryManager` automatically detects and migrates old format files on first load. A message will be printed to console.

### Manual Migration

Run the migration script to explicitly migrate and see detailed statistics:

```powershell
python migrate_chat_history.py
```

This will:
- Create a timestamped backup of your current history
- Convert all entries to the new wrapped format
- Show statistics about your chat history
- Save the migrated data

## New Tools

Four new tools are available for managing chat history:

### 1. GetChatHistoryMetadataTool

Retrieve metadata about all entries without loading full content:

```python
GetChatHistoryMetadataTool()
```

Returns: List of entries with `id`, `ts`, `type`, `size` only.

**Use cases:**
- Analyze conversation flow
- Identify large entries
- Find specific messages to inspect or delete

### 2. GetChatHistoryEntryTool

Get the full wrapped entry (including content) by ID:

```python
GetChatHistoryEntryTool()
```

**Use cases:**
- Inspect specific message content
- Review entries before deletion
- Debug conversation issues

### 3. DeleteChatHistoryEntriesTool

Delete entries by their IDs, or delete ALL entries at once:

```python
# Delete all entries (efficient)
DeleteChatHistoryEntriesTool(delete_all=True)

# Delete specific entries by ID
DeleteChatHistoryEntriesTool(entry_ids=['id1', 'id2'])
```

**Two modes:**
1. **Delete All**: Set `delete_all=true` to clear entire history in 1 call (no metadata needed)
2. **Delete Specific**: Provide `entry_ids` to delete selected entries

**When to use each:**
- "Delete all", "clear history" → Use `delete_all=true` (efficient!)
- "Delete reasoning entries", "delete messages from today" → Use `entry_ids`

**⚠️ Use with EXTREME CAUTION:**
- Deleting entries can break conversation context
- Only use when user explicitly requests deletion
- Best for removing errors, redundant, or sensitive entries

### 4. GetChatHistoryStatsTool

Get statistical overview of chat history:

```python
GetChatHistoryStatsTool()
```

Returns:
- Total entries and size
- Breakdown by entry type
- Oldest and newest timestamps
- Size distribution

**Use cases:**
- Monitor conversation growth
- Identify optimization opportunities
- Understand conversation composition

## Enabling History Tools

By default, history management tools are commented out in `app.py`. To enable them:

```python
# In app.py, in initialize_agent() function:
selected_tools = [
    # ... other tools ...
    
    # Uncomment these lines:
    GetChatHistoryMetadataTool(),
    GetChatHistoryEntryTool(),
    DeleteChatHistoryEntriesTool(),
    GetChatHistoryStatsTool(),
    
    # ... more tools ...
]
```

## API Changes

### ChatHistoryManager Methods

**New methods:**
- `get_wrapped_history()` - Returns full wrapped entries with metadata
- `delete_entries_by_ids(entry_ids)` - Delete entries by ID
- `get_entry_by_id(entry_id)` - Get single entry by ID

**Modified methods:**
- `get_history()` - Still returns OpenAI-compatible message list (unwrapped)
- `add_entry(entry)` - Now wraps entry and returns its ID
- `append_entries(entries)` - Now wraps entries and returns list of IDs

**No changes needed** in most code - `get_history()` still returns the same format OpenAI expects!

## Example Usage

### Get conversation statistics

```python
from tools import GetChatHistoryStatsTool

tool = GetChatHistoryStatsTool()
stats = tool.run()

print(f"Total entries: {stats['total_entries']}")
print(f"Total size: {stats['total_size_kb']} KB")
print(f"By type: {stats['stats_by_type']}")
```

### List all entries

```python
from tools import GetChatHistoryMetadataTool

tool = GetChatHistoryMetadataTool()
result = tool.run()

for entry in result['entries']:
    print(f"{entry['ts']} - {entry['type']} - {entry['size']} bytes - ID: {entry['id']}")
```

### Delete all entries (efficient)

```python
from tools import DeleteChatHistoryEntriesTool

tool = DeleteChatHistoryEntriesTool()
result = tool.run(delete_all=True)

print(f"Deleted {result['deleted_count']} entries")
print(f"Remaining: {result['remaining_count']} entries")
print(f"Message: {result['message']}")
```

### Delete specific entries

```python
from tools import DeleteChatHistoryEntriesTool, GetChatHistoryMetadataTool

# First, get metadata to find entries
metadata_tool = GetChatHistoryMetadataTool()
metadata = metadata_tool.run()

# Filter for entries you want to delete (e.g., reasoning entries)
ids_to_delete = [e['id'] for e in metadata['entries'] if e['type'] == 'reasoning']

# Delete them
delete_tool = DeleteChatHistoryEntriesTool()
result = delete_tool.run(entry_ids=ids_to_delete)

print(f"Deleted {result['deleted_count']} entries")
print(f"Remaining: {result['remaining_count']} entries")
```

## Best Practices

1. **Enable tools only when needed** - History management tools are powerful; enable only for administrative tasks
2. **Back up before bulk deletions** - The migration script creates backups; consider doing the same before manual deletions
3. **Use stats tool first** - Understand your conversation before making changes
4. **Review before deleting** - Use `GetChatHistoryEntryTool` to inspect entries before deletion
5. **Monitor size growth** - Use stats tool periodically to track conversation size

## Backwards Compatibility

- ✅ Existing code using `chat_history_manager.get_history()` works unchanged
- ✅ OpenAI API receives the same message format as before
- ✅ Old format files are automatically migrated on load
- ✅ All existing functionality preserved

## Technical Details

### Wrapping Process

When an entry is added:
1. Calculate JSON size in bytes
2. Generate unique UUID
3. Create ISO 8601 timestamp
4. Determine entry type from content
5. Wrap in metadata envelope
6. Save to file

### Unwrapping Process

When history is requested for OpenAI:
1. Load wrapped entries from file
2. Extract `content` field from each entry
3. Return list of unwrapped content objects
4. OpenAI receives standard message format

This design ensures **zero impact** on OpenAI API interactions while enabling powerful management capabilities.
