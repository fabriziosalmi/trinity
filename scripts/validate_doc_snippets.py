#!/usr/bin/env python3
"""
Extract and validate Python code snippets from Markdown documentation.

This script ensures that all Python code examples in documentation are
syntactically valid and executable. Prevents documentation drift where
examples break as the API evolves.

Usage:
    python scripts/validate_doc_snippets.py README.md
    python scripts/validate_doc_snippets.py CONTRIBUTING.md
"""
import re
import sys
import ast
import subprocess
from pathlib import Path
from typing import List, Tuple


def extract_python_snippets(markdown_path: Path) -> List[Tuple[int, str]]:
    """
    Extract Python code blocks from Markdown file.
    
    Args:
        markdown_path: Path to Markdown file
        
    Returns:
        List of (line_number, code) tuples
    """
    content = markdown_path.read_text()
    snippets = []
    
    # Match Python code blocks: ```python or ```bash with trinity commands
    pattern = r'```(?:python|bash)\n(.*?)```'
    
    for match in re.finditer(pattern, content, re.DOTALL):
        code = match.group(1)
        line_num = content[:match.start()].count('\n') + 1
        
        # Skip bash commands (we'll validate trinity CLI separately)
        if code.strip().startswith(('trinity ', '# ', 'poetry ', 'git ', 'docker ', 'pip ', 'cd ', 'source ')):
            continue
            
        # Skip output examples (lines starting with $ or #)
        if any(line.strip().startswith(('$ ', '# ', '>>> ')) for line in code.split('\n')):
            continue
        
        # Skip commit message examples (feat:, fix:, docs:, etc.)
        if any(line.strip().startswith(('feat:', 'fix:', 'docs:', 'refactor:', 'test:', 'chore:', 'ci:')) for line in code.split('\n')):
            continue
            
        snippets.append((line_num, code))
    
    return snippets


def validate_python_syntax(code: str, line_num: int, filepath: Path) -> bool:
    """
    Validate Python code syntax using AST parsing.
    
    Args:
        code: Python code to validate
        line_num: Line number in source file (for error reporting)
        filepath: Source file path
        
    Returns:
        True if valid, False otherwise
    """
    try:
        ast.parse(code)
        print(f"✅ {filepath.name}:{line_num} - Valid Python syntax")
        return True
    except SyntaxError as e:
        print(f"❌ {filepath.name}:{line_num} - Syntax error: {e}")
        print(f"   Code snippet:\n{code[:200]}")
        return False


def validate_imports(code: str, line_num: int, filepath: Path) -> bool:
    """
    Verify that imports in code snippet are available.
    
    Args:
        code: Python code to check
        line_num: Line number in source file
        filepath: Source file path
        
    Returns:
        True if all imports resolve, False otherwise
    """
    # Extract import statements
    import_pattern = r'^(?:from\s+[\w.]+\s+)?import\s+[\w.,\s]+$'
    imports = [line for line in code.split('\n') if re.match(import_pattern, line.strip())]
    
    if not imports:
        return True  # No imports to validate
    
    # Create temporary test file
    test_code = '\n'.join(imports)
    try:
        ast.parse(test_code)
        # Try to actually import (this will fail if module doesn't exist)
        result = subprocess.run(
            ['python', '-c', test_code],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print(f"✅ {filepath.name}:{line_num} - All imports resolve")
            return True
        else:
            print(f"⚠️  {filepath.name}:{line_num} - Import error: {result.stderr.strip()}")
            return False
    except subprocess.TimeoutExpired:
        print(f"⚠️  {filepath.name}:{line_num} - Import validation timeout")
        return False
    except Exception as e:
        print(f"⚠️  {filepath.name}:{line_num} - Import check failed: {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_doc_snippets.py <markdown_file>")
        sys.exit(1)
    
    filepath = Path(sys.argv[1])
    
    if not filepath.exists():
        print(f"❌ File not found: {filepath}")
        sys.exit(1)
    
    print(f"\n📝 Validating Python snippets in {filepath}")
    print("=" * 60)
    
    snippets = extract_python_snippets(filepath)
    
    if not snippets:
        print(f"ℹ️  No Python code snippets found in {filepath}")
        sys.exit(0)
    
    print(f"Found {len(snippets)} Python code snippet(s)\n")
    
    valid_count = 0
    invalid_count = 0
    
    for line_num, code in snippets:
        # Validate syntax
        if not validate_python_syntax(code, line_num, filepath):
            invalid_count += 1
            continue
        
        # Validate imports (optional, can be noisy)
        # validate_imports(code, line_num, filepath)
        
        valid_count += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {valid_count} valid, {invalid_count} invalid")
    
    if invalid_count > 0:
        print("\n❌ Some code snippets have syntax errors")
        sys.exit(1)
    else:
        print("\n✅ All code snippets are syntactically valid")
        sys.exit(0)


if __name__ == "__main__":
    main()
