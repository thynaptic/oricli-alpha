#!/usr/bin/env python3
"""
Test script for the External Skills API.
"""

import sys
from pathlib import Path
import time

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from oricli_core.client import OricliAlphaClient

def test_skills_crud():
    print("\n--- Testing External Skills API ---")
    client = OricliAlphaClient(base_url="http://localhost:8080", api_key="test_key")
    
    skill_name = "test_robot_api"
    
    # 1. Create a skill
    print(f"Creating skill: {skill_name}...")
    try:
        new_skill = client.skills.create({
            "skill_name": skill_name,
            "description": "Test robot persona created via API",
            "triggers": ["robot", "beep", "boop"],
            "requires_tools": ["shell_sandbox_service"],
            "mindset": "You are a test robot. You beep and boop.",
            "instructions": "1. Always end your sentences with beep boop."
        })
        print(f"Create success: {new_skill.get('skill_name') == skill_name}")
    except Exception as e:
        print(f"Failed to create skill: {e}")

    # 2. List skills
    print("Listing skills...")
    try:
        skills = client.skills.list()
        skill_names = [s["skill_name"] for s in skills]
        print(f"Total skills: {len(skills)}")
        print(f"Found our new skill: {skill_name in skill_names}")
    except Exception as e:
        print(f"Failed to list skills: {e}")

    # 3. Get skill
    print(f"Getting details for {skill_name}...")
    try:
        skill = client.skills.get(skill_name)
        print(f"Skill triggers: {skill.get('triggers')}")
    except Exception as e:
        print(f"Failed to get skill: {e}")

    # 4. Update skill
    print(f"Updating skill {skill_name}...")
    try:
        updated_skill = client.skills.update(skill_name, {
            "description": "Updated robot persona",
            "triggers": ["robot", "beep", "boop", "bzzz"],
            "requires_tools": ["shell_sandbox_service"],
            "mindset": "You are an updated test robot.",
            "instructions": "1. Always end with bzzz."
        })
        print(f"Update success, new triggers: {updated_skill.get('triggers')}")
    except Exception as e:
        print(f"Failed to update skill: {e}")

    # 5. Delete skill
    print(f"Deleting skill {skill_name}...")
    try:
        success = client.skills.delete(skill_name)
        print(f"Delete success: {success}")
        
        # Verify deletion
        skills = client.skills.list()
        skill_names = [s["skill_name"] for s in skills]
        print(f"Skill truly deleted: {skill_name not in skill_names}")
    except Exception as e:
        print(f"Failed to delete skill: {e}")

if __name__ == "__main__":
    test_skills_crud()
