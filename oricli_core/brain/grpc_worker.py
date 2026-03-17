"""
Python gRPC Worker for Oricli-Alpha

This acts as the execution backend for the Go sidecar mesh. It loads
all the brain modules via ModuleRegistry and exposes them over gRPC
so the high-speed Go backbone can orchestrate them.
"""

import sys
import time
import json
import logging
import grpc
from concurrent import futures

from oricli_core.brain.registry import ModuleRegistry
import oricli_core.brain.protos.oricli_rpc_pb2 as pb2
import oricli_core.brain.protos.oricli_rpc_pb2_grpc as pb2_grpc

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

class ModuleWorkerService(pb2_grpc.ModuleServiceServicer):
    def __init__(self):
        self._discovered = False

    def GetManifest(self, request, context):
        """Returns the list of all available modules and their operations"""
        if not self._discovered:
            logger.info("Performing one-time module discovery...")
            ModuleRegistry.discover_modules(background=False)
            self._discovered = True
            logger.info(f"Discovered {len(ModuleRegistry.list_modules())} modules.")
            
        manifest_modules = []
        for name in ModuleRegistry.list_modules():
            meta = ModuleRegistry.get_metadata(name)
            if meta:
                try:
                    m = pb2.ModuleMetadata(
                        name=meta.name,
                        description=meta.description,
                        version=meta.version,
                        operations=meta.operations
                    )
                    manifest_modules.append(m)
                except AttributeError as e:
                    logger.error(f"AttributeError for module {name}: {e}. Meta: {meta}")
                    raise
        return pb2.ManifestResponse(modules=manifest_modules)

    def ExecuteOperation(self, request, context):
        """Executes a specific operation on a brain module"""
        module_name = request.module_name
        operation = request.operation
        task_id = request.task_id
        
        try:
            params = json.loads(request.params_json) if request.params_json else {}
        except json.JSONDecodeError as e:
            return pb2.ExecuteResponse(
                success=False,
                error_message=f"Invalid JSON parameters: {e}"
            )

        logger.info(f"[Task {task_id}] Executing {module_name}.{operation}")
        
        try:
            # get_module will lazily initialize the instance if it isn't already warmed up
            module = ModuleRegistry.get_module(module_name)
            if not module:
                return pb2.ExecuteResponse(
                    success=False,
                    error_message=f"Module '{module_name}' not found or failed to load."
                )
                
            if operation == "health_check":
                # Use the default health_check method if not overridden in execute
                if hasattr(module, "health_check"):
                    result = module.health_check()
                else:
                    result = {"success": True, "status": "online"}
            elif operation not in module.metadata.operations:
                return pb2.ExecuteResponse(
                    success=False,
                    error_message=f"Operation '{operation}' not supported by '{module_name}'."
                )
            else:
                # Normal Execution
                result = module.execute(operation, params)
            
            return pb2.ExecuteResponse(
                success=True,
                result_json=json.dumps(result)
            )

        except Exception as e:
            logger.error(f"[Task {task_id}] Execution failed: {e}", exc_info=True)
            return pb2.ExecuteResponse(
                success=False,
                error_message=str(e)
            )

    def HealthCheck(self, request, context):
        """Lightweight ping to ensure the worker is responsive"""
        return pb2.HealthCheckResponse(
            ready=True,
            status_message=f"Python Worker running with {len(ModuleRegistry.list_modules())} modules."
        )


def serve(port=50051):
    # Use a large thread pool to handle concurrent executions from the Go bus
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=50))
    pb2_grpc.add_ModuleServiceServicer_to_server(ModuleWorkerService(), server)
    
    # We can eventually switch this to a Unix socket for near-zero latency
    address = f'[::]:{port}'
    server.add_insecure_port(address)
    server.start()
    logger.info(f"Python gRPC Worker started on {address}")
    
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down worker...")
        server.stop(0)

if __name__ == '__main__':
    import os
    port = int(os.environ.get("ORICLI_WORKER_PORT", 50051))
    serve(port)
