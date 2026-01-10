#!/usr/bin/env python3
"""
Helper script to fix common .env file issues:
1. Change EMBEDDING_MODEL to OpenAI-style if using sentence-transformers
2. Check for syntax errors
"""

import os
import sys
from pathlib import Path

def fix_env_file(env_path: Path):
    """Fix common issues in .env file."""
    if not env_path.exists():
        print(f"❌ .env file not found at {env_path}")
        return False
    
    with open(env_path, 'r') as f:
        lines = f.readlines()
    
    modified = False
    new_lines = []
    
    for i, line in enumerate(lines, start=1):
        original_line = line
        
        # Fix EMBEDDING_MODEL
        if line.strip().startswith('EMBEDDING_MODEL=') and 'sentence-transformers' in line:
            print(f"🔧 Line {i}: Changing EMBEDDING_MODEL to OpenAI-style")
            # Comment out the old line and add new one
            new_lines.append(f"# {line.strip()}\n")
            new_lines.append('EMBEDDING_MODEL="openai://nomic-embed-text"\n')
            modified = True
            continue
        
        # Uncomment the OpenAI-style EMBEDDING_MODEL if it's commented
        if line.strip().startswith('#') and 'EMBEDDING_MODEL="openai://' in line:
            print(f"🔧 Line {i}: Uncommenting OpenAI-style EMBEDDING_MODEL")
            new_lines.append(line[1:].lstrip())  # Remove # and leading whitespace
            modified = True
            continue
        
        # Check for common syntax errors
        stripped = line.strip()
        if stripped and not stripped.startswith('#') and '=' in stripped:
            # Check for unquoted values with special characters
            parts = stripped.split('=', 1)
            if len(parts) == 2:
                key, value = parts
                # Check for problematic characters in value
                if value and not (value.startswith('"') or value.startswith("'")):
                    if any(c in value for c in [' ', ';', '#', '$']):
                        print(f"⚠️  Line {i}: Possible syntax issue - value may need quotes: {stripped[:50]}...")
        
        new_lines.append(line)
    
    if modified:
        # Backup original
        backup_path = env_path.with_suffix('.env.bak')
        with open(backup_path, 'w') as f:
            f.writelines(lines)
        print(f"📦 Backup created at {backup_path}")
        
        # Write fixed version
        with open(env_path, 'w') as f:
            f.writelines(new_lines)
        print(f"✅ Fixed .env file saved")
        return True
    else:
        print("✅ No changes needed")
        return False


if __name__ == "__main__":
    # Find .env file in backend directory
    script_dir = Path(__file__).parent
    backend_dir = script_dir.parent
    env_path = backend_dir / ".env"
    
    print(f"Looking for .env file at: {env_path}")
    print()
    
    if fix_env_file(env_path):
        print()
        print("Next steps:")
        print("1. Review the changes in your .env file")
        print("2. If line 49 has a syntax error, check it manually")
        print("3. Run your script again")
    else:
        print()
        print("If you're still getting dotenv parsing errors, check line 49 manually.")
        print("Common issues:")
        print("- Unquoted values with spaces: use quotes like KEY=\"value with spaces\"")
        print("- Trailing backslashes: remove or escape them")
        print("- Special characters: escape them or use quotes")
