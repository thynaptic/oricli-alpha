from __future__ import annotations
"""
Test Service Discovery
Verifies all converted services are discoverable and accessible
"""

import sys
import logging

from oricli_core.brain.registry import ModuleRegistry

logger = logging.getLogger(__name__)


def test_service_discovery():
    """Test that all converted services are discoverable"""
    logger.info("=" * 80)
    logger.info("Testing Service Discovery")
    logger.info("=" * 80)
    
    # Discover all modules
    ModuleRegistry.discover_modules(verbose=True)
    
    # List all discovered modules
    all_modules = ModuleRegistry.list_modules()
    logger.info("Total modules discovered: %s", len(all_modules))
    
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
        "oricli_system_prompt_builder",
        
        # Tool Services
        "shell_sandbox_service",
    ]
    
    logger.info("=" * 80)
    logger.info("Checking Expected New Services")
    logger.info("=" * 80)
    
    found_services = []
    missing_services = []
    
    for service_name in expected_new_services:
        if ModuleRegistry.is_module_available(service_name):
            found_services.append(service_name)
            metadata = ModuleRegistry.get_metadata(service_name)
            if metadata:
                logger.info(
                    "✓ %s v%s - %s...",
                    service_name,
                    metadata.version,
                    (metadata.description or "")[:60],
                )
            else:
                logger.info("✓ %s (metadata not available)", service_name)
        else:
            missing_services.append(service_name)
            logger.warning("✗ %s - NOT FOUND", service_name)
    
    logger.info("=" * 80)
    logger.info("Summary")
    logger.info("=" * 80)
    logger.info("Found: %s/%s", len(found_services), len(expected_new_services))
    logger.info("Missing: %s", len(missing_services))
    
    if missing_services:
        logger.info("Missing services:")
        for service in missing_services:
            logger.info("  - %s", service)
    
    # Test module initialization
    logger.info("=" * 80)
    logger.info("Testing Module Initialization")
    logger.info("=" * 80)
    
    initialized_count = 0
    failed_count = 0
    
    for service_name in found_services[:10]:  # Test first 10 to avoid too much output
        try:
            module = ModuleRegistry.get_module(service_name, auto_discover=False)
            if module:
                initialized_count += 1
                logger.info("✓ %s - Initialized successfully", service_name)
            else:
                failed_count += 1
                logger.warning("✗ %s - Initialization failed", service_name)
        except Exception as e:
            failed_count += 1
            logger.debug(
                "✗ %s - Error during initialization",
                service_name,
                exc_info=True,
                extra={"service_name": service_name, "error_type": type(e).__name__},
            )
    
    logger.info("Initialized: %s, Failed: %s", initialized_count, failed_count)
    
    return len(found_services) == len(expected_new_services)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    success = test_service_discovery()
    sys.exit(0 if success else 1)

