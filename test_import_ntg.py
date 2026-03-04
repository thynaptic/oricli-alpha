from mavaia_core.brain.modules.neural_text_generator import NeuralTextGeneratorModule
try:
    mod = NeuralTextGeneratorModule()
    print("Instance created:", mod)
    print("Metadata:", mod.metadata.name)
except Exception as e:
    import traceback
    traceback.print_exc()
