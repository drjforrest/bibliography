def chunk_text(text, size=500, overlap=100):
    """Split text into overlapping chunks."""
    if not text or not text.strip():
        return []

    chunks = []
    text_length = len(text)

    # If text is shorter than chunk size, return as single chunk
    if text_length <= size:
        return [text.strip()]

    for i in range(0, text_length, size - overlap):
        chunk = text[i : i + size]

        # Skip empty chunks
        if chunk.strip():
            chunks.append(chunk.strip())

        # Break if we've reached the end
        if i + size >= text_length:
            break

    return chunks
