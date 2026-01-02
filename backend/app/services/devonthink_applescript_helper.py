"""Helper functions to interact with DEVONthink via AppleScript"""

import logging
import os
import re
import subprocess

logger = logging.getLogger(__name__)

# UUID pattern: 8-4-4-4-12 hexadecimal characters with hyphens
# Example: 550e8400-e29b-41d4-a716-446655440000
UUID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

# Dangerous characters for AppleScript injection
DANGEROUS_CHARS = set("\"'();&`|<>\\${}[]*?~!@#$%^=+")


def validate_record_uuid(record_uuid: str) -> str:
    """
    Validate and sanitize record UUID.

    Args:
        record_uuid: UUID string to validate

    Returns:
        Validated UUID string

    Raises:
        ValueError: If UUID is invalid or contains dangerous characters
    """
    if not isinstance(record_uuid, str):
        raise ValueError(f"record_uuid must be a string, got {type(record_uuid)}")

    # Check for dangerous characters
    if any(char in DANGEROUS_CHARS for char in record_uuid):
        raise ValueError(
            "record_uuid contains dangerous characters. "
            "Only alphanumeric characters and hyphens are allowed."
        )

    # Validate UUID format
    if not UUID_PATTERN.match(record_uuid):
        raise ValueError(
            f"record_uuid must be a valid UUID format "
            f"(8-4-4-4-12 hexadecimal characters with hyphens), got: {record_uuid[:50]}"
        )

    return record_uuid


def validate_database_name(database_name: str) -> str:
    """
    Validate and sanitize database name.

    Args:
        database_name: Database name to validate

    Returns:
        Validated database name

    Raises:
        ValueError: If database name contains dangerous characters
    """
    if not isinstance(database_name, str):
        raise ValueError(f"database_name must be a string, got {type(database_name)}")

    # Reject inputs containing quotes entirely (as recommended)
    if '"' in database_name or "'" in database_name:
        raise ValueError(
            "database_name cannot contain quotes. "
            "Only alphanumeric characters, spaces, hyphens, and underscores are allowed."
        )

    # Check for other dangerous characters
    dangerous_found = [char for char in database_name if char in DANGEROUS_CHARS]
    if dangerous_found:
        raise ValueError(
            f"database_name contains dangerous characters: {set(dangerous_found)}. "
            f"Only alphanumeric characters, spaces, hyphens, and underscores are allowed."
        )

    if not database_name.strip():
        raise ValueError("database_name cannot be empty")

    return database_name.strip()


def escape_applescript_string(value: str) -> str:
    """
    Escape double quotes in a string for safe use in AppleScript.
    This should only be called after validation has already ensured
    the string doesn't contain other dangerous characters.

    Args:
        value: String to escape

    Returns:
        Escaped string
    """
    # Replace double quotes with escaped versions
    # Note: We validate that quotes aren't present before this,
    # but this provides defense in depth
    return value.replace('"', '\\"')


def get_pdf_binary_from_devonthink(record_uuid: str, database_name: str) -> bytes:
    """
    Export PDF binary data from DEVONthink using AppleScript.

    Args:
        record_uuid: UUID of the DEVONthink record
        database_name: Name of the DEVONthink database

    Returns:
        PDF binary data as bytes

    Raises:
        ValueError: If validation fails or export fails
    """
    # Validate inputs
    validated_uuid = validate_record_uuid(record_uuid)
    validated_db_name = validate_database_name(database_name)

    # Escape for AppleScript
    escaped_uuid = escape_applescript_string(validated_uuid)
    escaped_db_name = escape_applescript_string(validated_db_name)

    # Create temporary file
    try:
        from tempfile import mkstemp

        fd, temp_file = mkstemp(suffix=".pdf", prefix="devonthink_")
        os.close(fd)  # Close the file descriptor, we'll open it later for reading
    except Exception as e:
        logger.error(f"Failed to create temp file: {e}")
        raise ValueError(f"Failed to create temp file: {e}")

    escaped_temp_file = escape_applescript_string(temp_file)

    # AppleScript using validated variables to avoid injection
    # We set variables at the start to avoid string interpolation issues
    export_script = f'''
    tell application id "DNtp"
        try
            set dbName to "{escaped_db_name}"
            set recordUUID to "{escaped_uuid}"
            set outputPath to "{escaped_temp_file}"
            
            set theDatabase to database dbName
            set theRecord to (every record of theDatabase whose uuid is recordUUID)
            if (count of theRecord) = 0 then
                error "Record with UUID " & recordUUID & " not found"
            end if
            
            set theRecord to item 1 of theRecord
            set pdfData to data of theRecord
            
            if pdfData is missing value then
                error "No binary data for record " & recordUUID
            end if
            
            -- Write to temp file
            set pdfFilePath to POSIX file outputPath
            set pdfFile to open for access pdfFilePath with write permission
            set eof of pdfFile to 0
            write pdfData to pdfFile
            close access pdfFile
        on error errMsg
            try
                close access file outputPath
            end try
            error "AppleScript error: " & errMsg
        end try
    end tell
    '''

    try:
        # Run AppleScript
        result = subprocess.run(
            ["osascript", "-e", export_script],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            error_msg = result.stderr.strip() or result.stdout.strip()
            logger.error(f"AppleScript failed: {error_msg}")
            raise ValueError(f"Failed to export PDF via AppleScript: {error_msg}")

        # Read the PDF file that was created
        if os.path.exists(temp_file):
            with open(temp_file, "rb") as f:
                pdf_data = f.read()

            # Clean up temp file
            try:
                os.remove(temp_file)
            except:
                pass

            if len(pdf_data) == 0:
                raise ValueError("Exported PDF file is empty")

            # Verify it's a PDF
            if not pdf_data.startswith(b"%PDF"):
                logger.warning("File doesn't start with PDF header, but continuing")

            return pdf_data
        else:
            raise ValueError(f"AppleScript did not create PDF file: {temp_file}")

    except subprocess.TimeoutExpired:
        raise ValueError("AppleScript timeout while exporting PDF")
    except Exception as e:
        # Clean up on error
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass
        raise ValueError(f"Failed to export PDF via AppleScript: {e}")
