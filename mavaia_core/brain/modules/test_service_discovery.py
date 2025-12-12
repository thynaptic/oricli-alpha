"""
Test Service Discovery
Verifies all converted services are discoverable and accessible
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from module_registry import ModuleRegistry


def test_service_discovery():
    """Test that all converted services are discoverable"""
    print("=" * 80)
    print("Testing Service Discovery")
    print("=" * 80)
    
    # Discover all modules
    ModuleRegistry.discover_modules(verbose=True)
    
    # List all discovered modules
    all_modules = ModuleRegistry.list_modules()
    print(f"\nTotal modules discovered: {len(all_modules)}")
    
    # Expected new services from conversion
    expected_new_services = [
        # Core Reasoning Services
        "supervised_self_consistency_service",
        "cognitive_reasoning_orchestrator",
        "self_chaining_discovery_service",
        "self_chaining_executor",
        
        # Personality & Style Services
        "personality_builder_service",
        "personality_builder_storage_service",
        "personality_configuration_loader",
        "hybrid_phrasing_service",
        
        # Safety Services
        "safety_service_registration",
        "step_safety_filter",
        "reasoning_verification_loop",
        
        # COGS Services
        "cogs_engine",
        "cogs_relationship_extractor",
        
        # Agent Services
        "agent_coordinator",
        
        # Document & Analysis Services
        "vision_pipeline_service",
        "document_ranker",
        
        # Memory Services
        "conversation_archive",
        "reaction_memory_service",
        
        # Model & Performance Services
        "model_routing_engine",
        "model_cascade_service",
        
        # Utility Services
        "mavaia_system_prompt_builder",
        
        # Tool Services
        "shell_sandbox_service",
    ]
    
    print("\n" + "=" * 80)
    print("Checking Expected New Services")
    print("=" * 80)
    
    found_services = []
    missing_services = []
    
    for service_name in expected_new_services:
        if ModuleRegistry.is_module_available(service_name):
            found_services.append(service_name)
            metadata = ModuleRegistry.get_metadata(service_name)
            if metadata:
                print(f"✓ {service_name} v{metadata.version} - {metadata.description[:60]}...")
            else:
                print(f"✓ {service_name} (metadata not available)")
        else:
            missing_services.append(service_name)
            print(f"✗ {service_name} - NOT FOUND")
    
    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"Found: {len(found_services)}/{len(expected_new_services)}")
    print(f"Missing: {len(missing_services)}")
    
    if missing_services:
        print("\nMissing services:")
        for service in missing_services:
            print(f"  - {service}")
    
    # Test module initialization
    print("\n" + "=" * 80)
    print("Testing Module Initialization")
    print("=" * 80)
    
    initialized_count = 0
    failed_count = 0
    
    for service_name in found_services[:10]:  # Test first 10 to avoid too much output
        try:
            module = ModuleRegistry.get_module(service_name, auto_discover=False)
            if module:
                initialized_count += 1
                print(f"✓ {service_name} - Initialized successfully")
            else:
                failed_count += 1
                print(f"✗ {service_name} - Initialization failed")
        except Exception as e:
            failed_count += 1
            print(f"✗ {service_name} - Error: {str(e)[:60]}")
    
    print(f"\nInitialized: {initialized_count}, Failed: {failed_count}")
    
    return len(found_services) == len(expected_new_services)


if __name__ == "__main__":
    success = test_service_discovery()
    sys.exit(0 if success else 1)

