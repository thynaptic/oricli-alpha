from oricli_core.brain.modules.memory_tool import MemoryToolModule
from oricli_core.exceptions import InvalidParameterError
import unittest


class TestMemoryToolSmoke(unittest.TestCase):
    def test_memory_tool_unknown_operation_does_not_require_storage(self) -> None:
        module = MemoryToolModule()
        with self.assertRaises(InvalidParameterError):
            module.execute("no_such_operation", {})


if __name__ == "__main__":
    unittest.main()

