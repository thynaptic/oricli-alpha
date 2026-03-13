---
name: Module Warmup and Monitoring System
overview: Create a comprehensive module warmup and monitoring framework that ensures all brain modules are pre-loaded, initialized, tested, and kept online with automatic recovery to achieve 0% downtime.
todos:
  - id: create_warmup_service
    content: Create ModuleWarmupService in oricli_core/brain/warmup.py with warmup_all_modules(), warmup_module(), and status tracking
    status: pending
  - id: create_monitor_service
    content: Create ModuleMonitorService in oricli_core/brain/monitor.py with background monitoring thread and health checks
    status: pending
  - id: create_recovery_service
    content: Create ModuleRecoveryService in oricli_core/brain/recovery.py with automatic retry and exponential backoff
    status: pending
  - id: create_degraded_classifier
    content: Create DegradedModeClassifier in oricli_core/brain/degraded_classifier.py with degradation classification and fallback routing
    status: pending
    dependencies:
      - create_monitor_service
  - id: create_availability_manager
    content: Create ModuleAvailabilityManager in oricli_core/brain/availability.py to coordinate all services with automatic fallback routing
    status: pending
    dependencies:
      - create_warmup_service
      - create_monitor_service
      - create_recovery_service
      - create_degraded_classifier
  - id: integrate_server_startup
    content: Integrate ModuleAvailabilityManager into server startup in oricli_core/api/server.py
    status: pending
    dependencies:
      - create_availability_manager
  - id: integrate_registry
    content: Integrate availability checks into ModuleRegistry.get_module() in oricli_core/brain/registry.py
    status: pending
    dependencies:
      - create_availability_manager
  - id: integrate_orchestrator
    content: Integrate availability manager into ModuleOrchestrator in oricli_core/brain/orchestrator.py
    status: pending
    dependencies:
      - create_availability_manager
  - id: add_health_endpoints
    content: Add health and warmup status endpoints to API server in oricli_core/api/server.py
    status: pending
    dependencies:
      - create_availability_manager
---

# Module Warmup and Monitoring System

## Overview

Create a framework that proactively warms up all brain modules (load, initialize, test, pre-load resources) and continuously monitors their health with automatic recovery to ensure 0% downtime. The system includes intelligent degradation classification and automatic fallback routing, making Mavaia's cognitive system truly adaptive - automatically switching to alternative modules when primary modules are degraded, slow, or partially loaded.

### Adaptive Brain Concept

The degraded mode classifier and fallback routing system transforms Mavaia into a truly adaptive cognitive system:

- **Intelligent Degradation Detection**: Not all failures are equal - modules can be slow, missing dependencies, or half-loaded
- **Automatic Fallback Routing**: When a module is degraded, the system automatically routes requests to alternative modules that can perform similar operations
- **Zero-Downtime Operation**: Even when primary modules fail, the system continues operating using fallback modules
- **Performance Optimization**: The system learns which modules are most reliable and routes accordingly
- **Graceful Degradation**: The system maintains functionality even when optimal modules are unavailable

**Example Fallback Scenarios**:

- MCTS module is slow (exceeding performance thresholds) → automatically route to CoT module
- Symbolic solver missing dependency → automatically route to heuristic reasoning module  
- Generator module partially loaded (some operations fail) → automatically route to text generation engine
- Module timeout → automatically route to simpler, faster alternative

This creates a self-healing, adaptive cognitive architecture that maintains service quality even under adverse conditions.

## Architecture

The system will consist of:

1. **ModuleWarmupService** (`oricli_core/brain/warmup.py`) - Core warmup service
2. **ModuleMonitorService** (`oricli_core/brain/monitor.py`) - Continuous health monitoring
3. **ModuleRecoveryService** (`oricli_core/brain/recovery.py`) - Automatic recovery for failed modules
4. **DegradedModeClassifier** (`oricli_core/brain/degraded_classifier.py`) - Classifies degradation reasons and manages fallback routing
5. **ModuleAvailabilityManager** (`oricli_core/brain/availability.py`) - Unified interface coordinating all services with automatic fallback
6. Integration points in server startup and orchestrator

## Implementation Plan

### 1. Create Module Warmup Service (`oricli_core/brain/warmup.py`)

**Purpose**: Pre-load, initialize, test, and pre-warm all modules**Key Features**:

- Discovers all modules via `ModuleRegistry`
- Loads modules in dependency order using `ModuleOrchestrator`
- Initializes each module
- Performs lightweight operation tests (if module has a "health_check" or "ping" operation, otherwise uses first available operation)
- Pre-loads heavy resources (models, caches) by executing warmup operations
- Tracks warmup status per module
- Supports parallel warmup with configurable concurrency
- Handles warmup failures gracefully (retry with backoff)

**Methods**:

- `warmup_all_modules()` - Warm up all discovered modules
- `warmup_module(module_name)` - Warm up a specific module
- `get_warmup_status()` - Get status of all modules
- `is_module_warmed(module_name)` - Check if module is warmed

**Configuration**:

- `MAVAIA_WARMUP_ENABLED` (default: true)
- `MAVAIA_WARMUP_TIMEOUT` (default: 300s per module)
- `MAVAIA_WARMUP_CONCURRENCY` (default: 4 parallel warmups)
- `MAVAIA_WARMUP_TEST_OPERATIONS` (default: true)

### 2. Create Module Monitor Service (`oricli_core/brain/monitor.py`)

**Purpose**: Continuously monitor module health and detect failures**Key Features**:

- Background thread that periodically checks all modules
- Uses `HealthChecker` for health status
- Performs lightweight operation tests to verify modules are responsive
- Tracks module state (online/offline/degraded)
- Detects timeouts, import failures, and execution failures
- Measures response times and performance metrics
- Emits events when modules go offline or recover
- Configurable check interval

**Methods**:

- `start_monitoring()` - Start background monitoring thread
- `stop_monitoring()` - Stop monitoring
- `check_module(module_name)` - Manually check a module
- `get_module_status(module_name)` - Get current status with degradation details
- `get_all_statuses()` - Get status of all modules
- `register_status_callback()` - Register callback for status changes

**Configuration**:

- `MAVAIA_MONITOR_ENABLED` (default: true)
- `MAVAIA_MONITOR_INTERVAL` (default: 30s)
- `MAVAIA_MONITOR_TIMEOUT` (default: 10s per check)
- `MAVAIA_MONITOR_SLOW_THRESHOLD` (default: 5.0s) - Response time threshold for "slow" classification

### 3. Create Module Recovery Service (`oricli_core/brain/recovery.py`)

**Purpose**: Automatically recover failed or offline modules**Key Features**:

- Listens to monitor events for module failures
- Automatically attempts to reload and reinitialize failed modules
- Retries with exponential backoff
- Handles import timeouts, initialization failures, and execution failures
- Tracks recovery attempts and success rates
- Prevents infinite retry loops (max attempts configurable)

**Methods**:

- `recover_module(module_name)` - Attempt to recover a module
- `recover_all_failed()` - Recover all failed modules
- `get_recovery_status()` - Get recovery attempt history
- `register_recovery_callback()` - Register callback for recovery events

**Configuration**:

- `MAVAIA_RECOVERY_ENABLED` (default: true)
- `MAVAIA_RECOVERY_MAX_ATTEMPTS` (default: 5)
- `MAVAIA_RECOVERY_BACKOFF_BASE` (default: 2.0)
- `MAVAIA_RECOVERY_BACKOFF_MAX` (default: 300s)

### 4. Create Degraded Mode Classifier (`oricli_core/brain/degraded_classifier.py`)

**Purpose**: Classify degradation reasons and manage automatic fallback routing**Key Features**:

- Classifies degradation reasons: slow, missing_dependency, half_loaded, timeout, partial_failure
- Maintains fallback module mappings (e.g., MCTS → CoT, Symbolic → Heuristic, Generator → Completions)
- Determines appropriate fallback based on degradation type and module capabilities
- Supports configurable fallback chains (primary → secondary → tertiary)
- Tracks fallback usage and success rates
- Provides fallback recommendations based on operation type

**Degradation Classifications**:

- `SLOW` - Module responds but exceeds performance thresholds
- `MISSING_DEPENDENCY` - Module missing required dependencies (models, services, etc.)
- `HALF_LOADED` - Module partially initialized (some operations work, others don't)
- `TIMEOUT` - Module operations consistently timeout
- `PARTIAL_FAILURE` - Module has high error rate but still functional
- `OFFLINE` - Module completely unavailable

**Fallback Mappings** (configurable via `MAVAIA_FALLBACK_MAPPINGS` or config file):

```python
{
    "mcts_search_engine": ["chain_of_thought", "reasoning"],
    "mcts_reasoning": ["chain_of_thought", "reasoning"],
    "mcts_service": ["chain_of_thought", "reasoning"],
    "symbolic_solver": ["reasoning", "fallback_heuristics"],
    "symbolic_solver_service": ["reasoning", "fallback_heuristics"],
    "cognitive_generator": ["text_generation_engine", "neural_text_generator"],
    "neural_text_generator": ["text_generation_engine"],
    # ... more mappings
}
```

**Methods**:

- `classify_degradation(module_name, health_check)` - Classify why a module is degraded
- `get_fallback_module(module_name, operation=None)` - Get recommended fallback module
- `register_fallback_mapping(primary, fallbacks)` - Register custom fallback chain
- `should_use_fallback(module_name, operation)` - Determine if fallback should be used
- `get_fallback_stats()` - Get statistics on fallback usage

**Configuration**:

- `MAVAIA_FALLBACK_ENABLED` (default: true)
- `MAVAIA_FALLBACK_MAPPINGS_FILE` (optional JSON file with custom mappings)
- `MAVAIA_FALLBACK_AUTO_ROUTE` (default: true) - Automatically route to fallback when degraded

### 5. Create Unified Module Availability Manager (`oricli_core/brain/availability.py`)

**Purpose**: Unified interface coordinating warmup, monitoring, recovery, and fallback routing**Key Features**:

- Coordinates all four services (warmup, monitor, recovery, classifier)
- Provides unified API for module availability with automatic fallback
- Ensures modules are available before use, or routes to fallback
- Blocks requests to offline modules (with timeout) unless fallback available
- Automatically routes requests to fallback modules when primary is degraded
- Provides status dashboard with fallback information
- Tracks fallback usage and performance

**Methods**:

- `initialize()` - Start all services
- `shutdown()` - Stop all services
- `ensure_module_available(module_name, timeout, use_fallback=True)` - Get module or fallback
- `get_module_or_fallback(module_name, operation=None)` - Get primary module or automatic fallback
- `get_availability_status()` - Get overall system status with fallback info
- `force_warmup(module_name)` - Force warmup of a module
- `register_fallback_mapping(primary, fallbacks)` - Register custom fallback
- `get_fallback_usage_stats()` - Get statistics on fallback routing

### 6. Integrate with Server Startup (`oricli_core/api/server.py`)

**Changes**:

- After module discovery in `create_app()`, initialize `ModuleAvailabilityManager`
- Start warmup process in background (non-blocking server startup)
- Add `/health/modules` endpoint for module availability status
- Add `/warmup/status` endpoint for warmup status

### 7. Integrate with Module Registry (`oricli_core/brain/registry.py`)

**Changes**:

- Wrap `get_module()` to check availability before returning
- If module is not warmed/available, trigger warmup (with timeout)
- If module is degraded and fallback enabled, return fallback module instead
- Log warnings when modules are requested but not available
- Add `get_module_or_fallback(module_name, operation=None)` method that automatically routes to fallback

### 8. Integrate with Module Orchestrator (`oricli_core/brain/orchestrator.py`)

**Changes**:

- Use `ModuleAvailabilityManager` to ensure modules are available before loading
- Coordinate with warmup service for dependency-aware warmup

### 9. Add Health Check Endpoints (`oricli_core/api/server.py`)

**New Endpoints**:

- `GET /health/modules` - Overall module health status with fallback info
- `GET /health/modules/{module_name}` - Specific module health with degradation classification
- `GET /warmup/status` - Warmup status for all modules
- `POST /warmup/{module_name}` - Force warmup of a module
- `POST /recovery/{module_name}` - Force recovery of a module
- `GET /fallback/mappings` - Get all fallback mappings
- `POST /fallback/mappings` - Register custom fallback mapping
- `GET /fallback/stats` - Get fallback usage statistics

## Implementation Details

### Warmup Process Flow

```javascript
1. Discover all modules (ModuleRegistry.discover_modules())
2. Get dependency order (ModuleOrchestrator.get_load_order())
3. For each module (in dependency order):
   a. Load module instance (ModuleRegistry.get_module())
   b. Initialize module (module.initialize())
   c. Test with lightweight operation (if available)
   d. Pre-load resources (execute warmup operations)
   e. Mark as warmed
4. Track warmup status and failures
```



### Monitoring Process Flow

```javascript
1. Start background thread
2. Every N seconds:
   a. For each registered module:
                - Check if module instance exists
                - Check health via HealthChecker
                - Test with lightweight operation (with timeout)
                - Measure response time and performance
                - Classify degradation reason (if degraded)
                - Update status (online/offline/degraded) with classification
   b. Emit events for status changes (including degradation classification)
3. On module failure or degradation:
        - Classify degradation reason
        - Trigger recovery service
        - Notify availability manager for fallback routing
```



### Recovery Process Flow

```javascript
1. On module failure event:
   a. Attempt to unregister module
   b. Wait for backoff period
   c. Attempt to reload module
   d. Attempt to reinitialize
   e. Test with lightweight operation
   f. If successful, mark as recovered
   g. If failed, retry with increased backoff (up to max attempts)
2. Track recovery attempts and success
```



### Fallback Routing Process Flow

```javascript
1. Request comes in for module X
2. Check module availability:
   a. If ONLINE → use module X
   b. If DEGRADED:
            - Classify degradation reason
            - Check if fallback should be used (based on degradation type)
            - Get fallback module from mappings
            - Verify fallback is available
            - Route request to fallback (with metadata indicating fallback used)
            - Log fallback usage
   c. If OFFLINE:
            - Get fallback module
            - If fallback available → route to fallback
            - If no fallback → return error or wait for recovery
3. Track fallback usage and performance
4. Periodically retry primary module to check if recovered
```



## Files to Create

1. `oricli_core/brain/warmup.py` - Module warmup service
2. `oricli_core/brain/monitor.py` - Module monitoring service
3. `oricli_core/brain/recovery.py` - Module recovery service
4. `oricli_core/brain/degraded_classifier.py` - Degraded mode classifier and fallback routing
5. `oricli_core/brain/availability.py` - Unified availability manager with fallback support

## Files to Modify

1. `oricli_core/api/server.py` - Add warmup initialization and health endpoints
2. `oricli_core/brain/registry.py` - Integrate availability checks in `get_module()`
3. `oricli_core/brain/orchestrator.py` - Integrate with availability manager

## Testing Strategy

- Unit tests for each service
- Integration tests for warmup → monitor → recovery flow
- Test timeout scenarios
- Test recovery scenarios
- Test concurrent warmup
- Test dependency ordering

## Configuration

All services will be configurable via environment variables with sensible defaults to ensure they work out of the box while allowing fine-tuning for different environments.

## Error Handling

- All warmup/monitoring/recovery operations will be wrapped in try/except
- Failures will be logged but won't crash the system
- Modules that fail to warm up will be marked as "failed" but system continues
- Recovery will attempt to fix failed modules automatically

## Observability

- Log all warmup, monitoring, and recovery events
- Track metrics for warmup times, recovery attempts, module availability
- Provide status endpoints for monitoring dashboards
- Track fallback usage: which modules triggered fallbacks, success rates, performance comparison