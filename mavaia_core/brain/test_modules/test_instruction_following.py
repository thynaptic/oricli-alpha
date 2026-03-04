import unittest
from mavaia_core.brain.modules.instruction_following import InstructionFollowingModule

class TestInstructionFollowing(unittest.TestCase):
    def setUp(self):
        self.module = InstructionFollowingModule()

    def test_detect_intent_standard_keywords(self):
        # Test basic keywords
        queries = [
            "Please convert this to JSON",
            "Can you parse this CSV file?",
            "Reformat the data into a markdown table",
            "Extract the information without explanation",
            "Show me the raw only output"
        ]
        for query in queries:
            result = self.module.detect_intent(query)
            self.assertTrue(result["is_high_precision"], f"Failed to detect intent in: {query}")
            self.assertGreater(len(result["matched_keywords"]), 0)

    def test_detect_intent_special_chars(self):
        # Test special characters
        queries = [
            "What is in this { 'key': 'value' }?",
            "Look at this [1, 2, 3]",
            "Render this <html><body>hello</body></html>"
        ]
        for query in queries:
            result = self.module.detect_intent(query)
            self.assertTrue(result["is_high_precision"], f"Failed to detect special char in: {query}")

    def test_detect_intent_negative(self):
        # Test negative cases (no keywords)
        queries = [
            "Hello, how are you today?",
            "Tell me a story about a brave knight",
            "What is the capital of France?",
            "Why is the sky blue?"
        ]
        for query in queries:
            result = self.module.detect_intent(query)
            self.assertFalse(result["is_high_precision"], f"False positive in: {query}")

    def test_detect_intent_word_boundaries(self):
        # Test that it doesn't match keywords inside other words
        queries = [
            "The masonry is old", # matches 'json'? No
            "He lives in a cave", # matches 'csv'? No
        ]
        for query in queries:
            result = self.module.detect_intent(query)
            self.assertFalse(result["is_high_precision"], f"False positive (word boundary) in: {query}")

    def test_execute_task_parameters(self):
        # Test parameter preparation
        result = self.module.execute_task("some input", "formatting")
        self.assertEqual(result["mode"], "TASK_EXECUTION")
        self.assertTrue(result["suppress_identity"])
        self.assertTrue(result["formatting_lock"])

    def test_apply_formatting_lock(self):
        # Test formatting lock marker
        text = "some raw data"
        result = self.module.apply_formatting_lock(text)
        self.assertEqual(result["locked_text"], text)
        self.assertTrue(result["formatting_lock_active"])

if __name__ == "__main__":
    unittest.main()
