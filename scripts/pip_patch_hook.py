#!/usr/bin/env python3
"""
Pip install hook to patch pybind11 for CMake 4.x compatibility
This is called during pip's build process to patch pybind11's CMakeLists.txt
"""

import os
import sys
import re
from pathlib import Path

def patch_pybind11_cmake(build_dir):
    """Patch pybind11 CMakeLists.txt files for CMake 4.x compatibility"""
    build_path = Path(build_dir)
    
    # Find all pybind11 CMakeLists.txt files
    for cmake_file in build_path.rglob("**/pybind11*/CMakeLists.txt"):
        try:
            content = cmake_file.read_text(encoding='utf-8')
            original_content = content
            
            # Fix 1: Replace cmake_minimum_required with version range
            # CMake 4.x requires the new syntax: VERSION min...max
            content = re.sub(
                r'cmake_minimum_required\s*\(\s*VERSION\s+3\.5\s*\)',
                'cmake_minimum_required(VERSION 3.5...4.0)',
                content
            )
            
            # Fix 2: Add policy settings at the top if not present
            if 'cmake_policy' not in content[:1000]:
                # Find the first cmake_minimum_required line
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if 'cmake_minimum_required' in line:
                        # Insert policy settings before it
                        policy_lines = [
                            '# Policy fixes for CMake 4.x compatibility',
                            'if(POLICY CMP0144)',
                            '    cmake_policy(SET CMP0144 NEW)',
                            'endif()',
                            'cmake_policy(SET CMP0003 NEW)',
                            'cmake_policy(SET CMP0011 NEW)',
                            'cmake_policy(SET CMP0074 NEW)',
                            ''
                        ]
                        lines.insert(i, '\n'.join(policy_lines))
                        content = '\n'.join(lines)
                        break
            
            # Only write if we made changes
            if content != original_content:
                print(f"Patching: {cmake_file}", file=sys.stderr)
                cmake_file.write_text(content, encoding='utf-8')
                
        except Exception as e:
            print(f"Warning: Could not patch {cmake_file}: {e}", file=sys.stderr)

if __name__ == "__main__":
    # Get build directory from environment or argument
    build_dir = os.environ.get('PIP_BUILD_DIR', sys.argv[1] if len(sys.argv) > 1 else '.')
    patch_pybind11_cmake(build_dir)
