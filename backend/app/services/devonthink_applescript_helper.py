"""Helper functions to interact with DEVONthink via AppleScript"""
import subprocess
import logging
import os
import tempfile

logger = logging.getLogger(__name__)


def get_pdf_binary_from_devonthink(record_uuid: str, database_name: str = "BIBLIOGRAPHY") -> bytes:
    """
    Get PDF binary data from DEVONthink using AppleScript.
    Similar to the user's export script but for a single record.
    """
    applescript = f'''
    tell application id "DNtp"
        try
            set theDatabase to database "{database_name}"
            if theDatabase is missing value then
                error "Database '{database_name}' not found"
            end if
            
            -- Find record by UUID
            set theRecord to (every record of theDatabase whose uuid is "{record_uuid}")
            if (count of theRecord) = 0 then
                error "Record with UUID {record_uuid} not found"
            end if
            
            set theRecord to item 1 of theRecord
            
            -- Get binary PDF data
            set pdfData to data of theRecord
            if pdfData is missing value then
                error "No binary data for record {record_uuid}"
            end if
            
            -- Return base64 encoded data (AppleScript can't return binary directly)
            -- We'll write to a temp file instead
            return pdfData
            
        on error errMsg
            error "AppleScript error: " & errMsg
        end try
    end tell
    '''
    
    # Create a temp file path
    temp_dir = os.path.expanduser("~/tmp/devonthink_export")
    os.makedirs(temp_dir, exist_ok=True)
    temp_file = os.path.join(temp_dir, f"{record_uuid}.pdf")
    
    # AppleScript to write PDF to temp file
    export_script = f'''
    tell application id "DNtp"
        try
            set theDatabase to database "{database_name}"
            set theRecord to (every record of theDatabase whose uuid is "{record_uuid}")
            if (count of theRecord) = 0 then
                error "Record with UUID {record_uuid} not found"
            end if
            
            set theRecord to item 1 of theRecord
            set pdfData to data of theRecord
            
            if pdfData is missing value then
                error "No binary data for record {record_uuid}"
            end if
            
            -- Write to temp file
            set pdfFilePath to POSIX file "{temp_file}"
            set pdfFile to open for access pdfFilePath with write permission
            set eof of pdfFile to 0
            write pdfData to pdfFile
            close access pdfFile
            
            return "{temp_file}"
            
        on error errMsg
            try
                close access file "{temp_file}"
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
            timeout=30
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
                logger.warning(f"File doesn't start with PDF header, but continuing")
            
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
        raise

