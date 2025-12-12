"""
Tool Schema Generator - Auto-generates tool schemas from services and Python brain modules
Mirrors Swift ToolSchemaGenerator.swift functionality
"""

from typing import Any, Dict, List, Optional
from tool_calling_models import Tool, ToolFunction, ToolParameters, ToolProperty


class ToolSchemaGenerator:
    """Auto-generates tool schemas from services and Python brain modules"""
    
    _instance: Optional["ToolSchemaGenerator"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
    
    # MARK: - Schema Generation
    
    def generate_schema_for_python_module(
        self,
        module_name: str,
        operation: str,
        description: str,
        parameters: Dict[str, Any] = None,
    ) -> Tool:
        """Generate tool schema for a Python brain module operation"""
        if parameters is None:
            parameters = {}
        
        properties: Dict[str, ToolProperty] = {}
        required: List[str] = []
        
        # Common parameters for Python modules
        properties["query"] = ToolProperty(
            type="string",
            description="The query or input for the operation"
        )
        required.append("query")
        
        properties["context"] = ToolProperty(
            type="string",
            description="Additional context for the operation"
        )
        
        # Add module-specific parameters
        for key, value in parameters.items():
            if isinstance(value, dict):
                param_type = value.get("type", "string")
                param_desc = value.get("description")
                param_required = value.get("required", False)
                
                enum_values = value.get("enum")
                if enum_values:
                    properties[key] = ToolProperty(
                        type=param_type,
                        description=param_desc,
                        enum_values=enum_values
                    )
                else:
                    properties[key] = ToolProperty(
                        type=param_type,
                        description=param_desc
                    )
                
                if param_required:
                    required.append(key)
        
        tool_parameters = ToolParameters(
            required=required if required else None,
            properties=properties
        )
        
        function = ToolFunction(
            name=operation,
            description=description,
            parameters=tool_parameters
        )
        
        return Tool(function=function)
    
    def generate_schema_for_service(
        self,
        service_name: str,
        method_name: str,
        description: str,
        parameters: Dict[str, ToolProperty],
        required: List[str] = None,
    ) -> Tool:
        """Generate tool schema for a service method"""
        if required is None:
            required = []
        
        tool_parameters = ToolParameters(
            required=required if required else None,
            properties=parameters
        )
        
        function = ToolFunction(
            name=method_name,
            description=description,
            parameters=tool_parameters
        )
        
        return Tool(function=function)
    
    async def generate_schemas_for_python_modules(self) -> List[Tool]:
        """Generate schemas for all Python brain modules"""
        tools: List[Tool] = []
        
        # Reasoning module
        tools.append(self.generate_schema_for_python_module(
            module_name="reasoning",
            operation="reason",
            description="Perform analytical reasoning on a query",
            parameters={
                "reasoningType": {
                    "type": "string",
                    "description": "Type of reasoning to apply",
                    "enum": ["analytical", "creative", "strategic", "diagnostic", "comparative"],
                    "required": False
                }
            }
        ))
        
        # Critical thinking
        tools.append(self.generate_schema_for_python_module(
            module_name="critical_thinking",
            operation="critical_thinking",
            description="Apply critical thinking to evaluate information"
        ))
        
        # Step-by-step reasoning
        tools.append(self.generate_schema_for_python_module(
            module_name="step_by_step",
            operation="step_by_step_reasoning",
            description="Break down a problem into step-by-step reasoning"
        ))
        
        # Decomposition
        tools.append(self.generate_schema_for_python_module(
            module_name="decomposition",
            operation="decompose_query",
            description="Decompose a complex query into sub-questions"
        ))
        
        # Hypothesis generation
        tools.append(self.generate_schema_for_python_module(
            module_name="hypothesis_generation",
            operation="generate_hypothesis",
            description="Generate hypotheses for a problem"
        ))
        
        # Evidence evaluation
        tools.append(self.generate_schema_for_python_module(
            module_name="evidence_evaluation",
            operation="evaluate_evidence",
            description="Evaluate the quality and relevance of evidence"
        ))
        
        # Logical deduction
        tools.append(self.generate_schema_for_python_module(
            module_name="logical_deduction",
            operation="logical_deduction",
            description="Apply logical deduction to derive conclusions"
        ))
        
        # Analogical reasoning
        tools.append(self.generate_schema_for_python_module(
            module_name="analogical_reasoning",
            operation="analogical_reasoning",
            description="Use analogical reasoning to find solutions"
        ))
        
        # Causal inference
        tools.append(self.generate_schema_for_python_module(
            module_name="causal_inference",
            operation="causal_inference",
            description="Identify cause-and-effect relationships"
        ))
        
        # Counterfactual
        tools.append(self.generate_schema_for_python_module(
            module_name="counterfactual",
            operation="counterfactual_analysis",
            description="Explore alternative scenarios"
        ))
        
        # Verification
        tools.append(self.generate_schema_for_python_module(
            module_name="verification",
            operation="verify_conclusion",
            description="Verify the correctness of a conclusion"
        ))
        
        # Embeddings
        tools.append(self.generate_schema_for_service(
            service_name="embeddings",
            method_name="generate_embeddings",
            description="Generate embeddings for text",
            parameters={
                "text": ToolProperty(type="string", description="Text to generate embeddings for"),
                "modelName": ToolProperty(type="string", description="Embedding model name (optional)")
            },
            required=["text"]
        ))
        
        tools.append(self.generate_schema_for_service(
            service_name="embeddings",
            method_name="compute_similarity",
            description="Compute semantic similarity between texts",
            parameters={
                "text1": ToolProperty(type="string", description="First text"),
                "text2": ToolProperty(type="string", description="Second text"),
                "modelName": ToolProperty(type="string", description="Embedding model name (optional)")
            },
            required=["text1", "text2"]
        ))
        
        # Personality response
        tools.append(self.generate_schema_for_service(
            service_name="personality_response",
            method_name="generate_personality_response",
            description="Generate a response with specific personality",
            parameters={
                "intent": ToolProperty(type="string", description="User intent"),
                "personality": ToolProperty(type="string", description="Personality type"),
                "context": ToolProperty(type="string", description="Additional context (optional)"),
                "emotionalTone": ToolProperty(type="string", description="Emotional tone (optional)")
            },
            required=["intent", "personality"]
        ))
        
        return tools


# Global singleton instance
tool_schema_generator = ToolSchemaGenerator()

