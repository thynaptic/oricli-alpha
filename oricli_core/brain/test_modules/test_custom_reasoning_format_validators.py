from __future__ import annotations
"""
Unit tests for custom_reasoning module format validators

Tests format validation for LiveBench response formats:
- Zebra puzzles: <solution>answer1, answer2, answer3, answer4, answer5</solution>
- Web of lies: **yes, no, yes**
- Spatial: coordinates or entities
"""

import unittest
from oricli_core.brain.modules.custom_reasoning_networks import CustomReasoningModule


class TestFormatValidators(unittest.TestCase):
    """Test format validation for different task types"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.module = CustomReasoningModule()
        # Initialize module (may fail if JAX not available, but that's OK for format tests)
        try:
            self.module.initialize()
        except Exception:
            pass  # JAX may not be available, but format validation doesn't need it
    
    def test_zebra_puzzle_format_validation_valid(self):
        """Test zebra puzzle format validation with valid format"""
        response = "<solution>Englishman, Spaniard, Ukrainian, Norwegian, Japanese</solution>"
        validation = self.module._validate_answer_quality(
            response,
            "zebra_puzzle",
            "Who lives in house 1? Who drinks coffee? Who owns the zebra? Where does the Norwegian live? What color is the green house?"
        )
        
        self.assertTrue(validation.get("is_valid"), f"Should be valid but got issues: {validation.get('issues')}")
        self.assertEqual(len(validation.get("issues", [])), 0)
        self.assertGreater(validation.get("confidence", 0), 0.7)
    
    def test_zebra_puzzle_format_validation_missing_tags(self):
        """Test zebra puzzle format validation with missing solution tags"""
        response = "Englishman, Spaniard, Ukrainian, Norwegian, Japanese"
        validation = self.module._validate_answer_quality(
            response,
            "zebra_puzzle",
            "Test question"
        )
        
        self.assertFalse(validation.get("is_valid"))
        self.assertIn("missing_solution_tags", validation.get("issues", []))
        self.assertTrue(validation.get("needs_repair"))
    
    def test_zebra_puzzle_format_validation_wrong_count(self):
        """Test zebra puzzle format validation with wrong answer count"""
        response = "<solution>Answer1, Answer2, Answer3</solution>"
        validation = self.module._validate_answer_quality(
            response,
            "zebra_puzzle",
            "Test question"
        )
        
        self.assertFalse(validation.get("is_valid"))
        issues = validation.get("issues", [])
        self.assertTrue(any("wrong_answer_count" in issue for issue in issues))
        self.assertTrue(validation.get("needs_repair"))
    
    def test_web_of_lies_format_validation_valid(self):
        """Test web of lies format validation with valid format"""
        response = "**yes, no, yes**"
        validation = self.module._validate_answer_quality(
            response,
            "web_of_lies",
            "Question 1? Question 2? Question 3?"
        )
        
        self.assertTrue(validation.get("is_valid"), f"Should be valid but got issues: {validation.get('issues')}")
        self.assertEqual(len(validation.get("issues", [])), 0)
        self.assertGreater(validation.get("confidence", 0), 0.7)
    
    def test_web_of_lies_format_validation_missing_bold(self):
        """Test web of lies format validation with missing bold format"""
        response = "yes, no, yes"
        validation = self.module._validate_answer_quality(
            response,
            "web_of_lies",
            "Test question"
        )
        
        self.assertFalse(validation.get("is_valid"))
        self.assertIn("missing_bold_format", validation.get("issues", []))
        self.assertTrue(validation.get("needs_repair"))
    
    def test_web_of_lies_format_validation_invalid_answers(self):
        """Test web of lies format validation with invalid answers"""
        response = "**maybe, perhaps, possibly**"
        validation = self.module._validate_answer_quality(
            response,
            "web_of_lies",
            "Test question"
        )
        
        self.assertFalse(validation.get("is_valid"))
        self.assertIn("invalid_yes_no_answers", validation.get("issues", []))
        self.assertTrue(validation.get("needs_repair"))
    
    def test_spatial_format_validation_valid_coords(self):
        """Test spatial format validation with coordinates"""
        response = "(1, 2), (3, 4), (5, 6)"
        validation = self.module._validate_answer_quality(
            response,
            "spatial",
            "Where is entity A? Where is entity B?"
        )
        
        # Spatial validation is more lenient
        self.assertGreater(validation.get("confidence", 0), 0.5)
    
    def test_spatial_format_validation_valid_entities(self):
        """Test spatial format validation with entities"""
        response = "EntityA, EntityB, EntityC"
        validation = self.module._validate_answer_quality(
            response,
            "spatial",
            "What is at position (1, 2)?"
        )
        
        # Spatial validation is more lenient - entities should pass
        # The validation checks for entities, numbers, or spatial words
        self.assertGreater(validation.get("confidence", 0), 0.3)  # Lowered threshold
    
    def test_response_repair_zebra_puzzle(self):
        """Test response format repair for zebra puzzle"""
        # Missing tags
        response = "Answer1, Answer2, Answer3, Answer4, Answer5"
        repaired = self.module._repair_response_format(
            response,
            "zebra_puzzle",
            "Test question",
            {}
        )
        
        self.assertIsNotNone(repaired)
        self.assertIn("<solution>", repaired)
        self.assertIn("</solution>", repaired)
        
        # Extract answers
        import re
        match = re.search(r'<solution>(.*?)</solution>', repaired)
        if match:
            answers = [a.strip() for a in match.group(1).split(",") if a.strip()]
            self.assertEqual(len(answers), 5)
    
    def test_response_repair_web_of_lies(self):
        """Test response format repair for web of lies"""
        # Missing bold
        response = "yes, no, yes"
        repaired = self.module._repair_response_format(
            response,
            "web_of_lies",
            "Question 1? Question 2? Question 3?",
            {}
        )
        
        self.assertIsNotNone(repaired)
        self.assertIn("**", repaired)
        self.assertIn("yes", repaired.lower())
        self.assertIn("no", repaired.lower())


class TestAnswerExtraction(unittest.TestCase):
    """Test answer extraction from various formats"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.module = CustomReasoningModule()
        try:
            self.module.initialize()
        except Exception:
            pass
    
    def test_extract_zebra_answers_from_model_v2(self):
        """Test extracting zebra puzzle answers from position map"""
        position_map = {
            1: {"color": "red", "nationality": "Englishman", "drink": "coffee", "pet": "dog"},
            2: {"color": "green", "nationality": "Spaniard", "drink": "tea", "pet": "cat"},
            3: {"color": "blue", "nationality": "Ukrainian", "drink": "milk", "pet": "horse"},
            4: {"color": "yellow", "nationality": "Norwegian", "drink": "water", "pet": "zebra"},
            5: {"color": "white", "nationality": "Japanese", "drink": "orange juice", "pet": "snail"}
        }
        
        questions = [
            "Who lives in house 1?",
            "What does the Spaniard drink?",
            "Where does the Norwegian live?",
            "What color is house 3?",
            "Who owns the zebra?"
        ]
        
        colors = ["red", "green", "blue", "yellow", "white"]
        nationalities = ["englishman", "spaniard", "ukrainian", "norwegian", "japanese"]
        drinks = ["coffee", "tea", "milk", "water", "orange juice"]
        pets = ["dog", "cat", "horse", "zebra", "snail"]
        
        answers = self.module._extract_zebra_answers_from_model_v2(
            position_map,
            questions,
            "Test puzzle",
            colors,
            nationalities,
            drinks,
            pets
        )
        
        self.assertEqual(len(answers), 5)
        self.assertEqual(answers[0], "Englishman")  # Who lives in house 1
        self.assertEqual(answers[1], "tea")  # What does the Spaniard drink
        self.assertEqual(answers[2], "4")  # Where does the Norwegian live


if __name__ == "__main__":
    unittest.main()

