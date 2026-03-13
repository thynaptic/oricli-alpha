from oricli_core.brain.registry import ModuleRegistry
import logging
logging.basicConfig(level=logging.DEBUG)
try:
    mod = ModuleRegistry.get_module("neural_text_generator", auto_discover=True)
    print(f"Loaded: {mod}")
except Exception as e:
    import traceback
    traceback.print_exc()
