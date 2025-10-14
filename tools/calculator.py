"""
Advanced Calculator Tool for LongContext Agent.
Provides mathematical computation capabilities with expression parsing and safety checks.
"""

import re
import math
import ast
import operator
from typing import Dict, Any, Union, List
from .base import BaseTool, ToolType

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "shared"))


class SafeMathEvaluator:
    """Safe mathematical expression evaluator"""
    
    # Allowed operators
    operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.BitXor: operator.xor,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
        ast.Mod: operator.mod,
    }
    
    # Allowed functions
    functions = {
        'abs': abs,
        'round': round,
        'max': max,
        'min': min,
        'sum': sum,
        'sqrt': math.sqrt,
        'sin': math.sin,
        'cos': math.cos,
        'tan': math.tan,
        'log': math.log,
        'log10': math.log10,
        'exp': math.exp,
        'floor': math.floor,
        'ceil': math.ceil,
        'pi': math.pi,
        'e': math.e,
    }
    
    def evaluate(self, expression: str) -> float:
        """Safely evaluate mathematical expression"""
        try:
            # Parse the expression
            node = ast.parse(expression, mode='eval')
            return self._eval_node(node.body)
        except Exception as e:
            raise ValueError(f"Invalid mathematical expression: {e}")
    
    def _eval_node(self, node):
        """Recursively evaluate AST nodes"""
        if isinstance(node, ast.Constant):  # Python 3.8+
            return node.value
        elif isinstance(node, ast.Num):  # Python < 3.8
            return node.n
        elif isinstance(node, ast.BinOp):
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            op = self.operators.get(type(node.op))
            if op is None:
                raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
            return op(left, right)
        elif isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand)
            op = self.operators.get(type(node.op))
            if op is None:
                raise ValueError(f"Unsupported unary operator: {type(node.op).__name__}")
            return op(operand)
        elif isinstance(node, ast.Call):
            func_name = node.func.id if isinstance(node.func, ast.Name) else None
            if func_name not in self.functions:
                raise ValueError(f"Unsupported function: {func_name}")
            
            args = [self._eval_node(arg) for arg in node.args]
            func = self.functions[func_name]
            
            # Handle special cases
            if func_name in ['pi', 'e']:
                return func
            
            return func(*args)
        elif isinstance(node, ast.Name):
            # Handle constants
            if node.id in self.functions:
                return self.functions[node.id]
            else:
                raise ValueError(f"Undefined variable: {node.id}")
        else:
            raise ValueError(f"Unsupported AST node type: {type(node).__name__}")


class CalculatorTool(BaseTool):
    """Advanced calculator tool with expression parsing"""
    
    def __init__(self):
        super().__init__(
            name="calculator",
            description="Perform mathematical calculations and evaluate expressions",
            tool_type=ToolType.CALCULATOR
        )
        self.evaluator = SafeMathEvaluator()
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """Validate calculator parameters"""
        if not isinstance(parameters, dict):
            return False
        
        # Check for required expression parameter
        if "expression" not in parameters:
            return False
        
        expression = parameters["expression"]
        if not isinstance(expression, str) or not expression.strip():
            return False
        
        return True
    
    def _get_parameter_schema(self) -> Dict[str, Any]:
        """Return parameter schema for calculator"""
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression to evaluate (e.g., '2 + 3 * 4', 'sqrt(16)', 'sin(pi/2)')"
                },
                "precision": {
                    "type": "integer",
                    "description": "Number of decimal places for the result (default: 6)",
                    "default": 6,
                    "minimum": 0,
                    "maximum": 15
                }
            },
            "required": ["expression"]
        }
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute calculator with given expression"""
        expression = parameters["expression"].strip()
        precision = parameters.get("precision", 6)
        
        try:
            # Clean and prepare expression
            cleaned_expression = self._clean_expression(expression)
            
            # Evaluate the expression
            result = self.evaluator.evaluate(cleaned_expression)
            
            # Format result
            if isinstance(result, float):
                if result.is_integer():
                    formatted_result = str(int(result))
                else:
                    formatted_result = f"{result:.{precision}f}".rstrip('0').rstrip('.')
            else:
                formatted_result = str(result)
            
            return {
                "result": formatted_result,
                "numeric_result": float(result),
                "expression": expression,
                "cleaned_expression": cleaned_expression,
                "calculation_type": self._determine_calculation_type(cleaned_expression)
            }
            
        except Exception as e:
            # Try alternative parsing methods
            fallback_result = self._try_fallback_evaluation(expression)
            
            if fallback_result is not None:
                return {
                    "result": str(fallback_result),
                    "numeric_result": fallback_result,
                    "expression": expression,
                    "method": "fallback",
                    "calculation_type": "basic_arithmetic"
                }
            
            raise Exception(f"Calculation failed: {str(e)}")
    
    def _clean_expression(self, expression: str) -> str:
        """Clean and normalize mathematical expression"""
        # Remove common text patterns
        expression = re.sub(r'\b(calculate|compute|what\s+is|equals?)\b', '', expression, flags=re.IGNORECASE)
        expression = re.sub(r'[=?]', '', expression)
        
        # Replace common mathematical notation
        replacements = {
            'x': '*',
            '÷': '/',
            '×': '*',
            '^': '**',
        }
        
        for old, new in replacements.items():
            expression = expression.replace(old, new)
        
        # Handle implicit multiplication (e.g., "2pi" -> "2*pi")
        expression = re.sub(r'(\d)([a-zA-Z])', r'\1*\2', expression)
        expression = re.sub(r'([a-zA-Z])(\d)', r'\1*\2', expression)
        
        return expression.strip()
    
    def _determine_calculation_type(self, expression: str) -> str:
        """Determine the type of calculation being performed"""
        expression_lower = expression.lower()
        
        if any(func in expression_lower for func in ['sin', 'cos', 'tan']):
            return "trigonometric"
        elif any(func in expression_lower for func in ['log', 'ln', 'exp']):
            return "logarithmic"
        elif 'sqrt' in expression_lower or '**0.5' in expression_lower:
            return "root_calculation"
        elif '**' in expression or '^' in expression:
            return "exponential"
        elif any(op in expression for op in ['+', '-', '*', '/']):
            return "basic_arithmetic"
        else:
            return "constant_evaluation"
    
    def _try_fallback_evaluation(self, expression: str) -> Union[float, None]:
        """Try simple fallback evaluation for basic expressions"""
        try:
            # Extract simple mathematical expressions
            pattern = r'(\d+(?:\.\d+)?)\s*([+\-*/])\s*(\d+(?:\.\d+)?)'
            match = re.search(pattern, expression)
            
            if match:
                num1, operator_str, num2 = match.groups()
                num1, num2 = float(num1), float(num2)
                
                if operator_str == '+':
                    return num1 + num2
                elif operator_str == '-':
                    return num1 - num2
                elif operator_str == '*':
                    return num1 * num2
                elif operator_str == '/':
                    if num2 == 0:
                        raise ValueError("Division by zero")
                    return num1 / num2
            
            # Try to extract just a number
            number_match = re.search(r'(\d+(?:\.\d+)?)', expression)
            if number_match:
                return float(number_match.group(1))
            
        except Exception:
            pass
        
        return None
    
    def get_examples(self) -> List[Dict[str, str]]:
        """Get example calculations"""
        return [
            {
                "expression": "2 + 3 * 4",
                "description": "Basic arithmetic with order of operations",
                "expected_result": "14"
            },
            {
                "expression": "sqrt(16) + 2**3",
                "description": "Square root and exponentiation",
                "expected_result": "12"
            },
            {
                "expression": "sin(pi/2)",
                "description": "Trigonometric function",
                "expected_result": "1"
            },
            {
                "expression": "log10(100)",
                "description": "Logarithmic function",
                "expected_result": "2"
            },
            {
                "expression": "(15 + 25) / 2",
                "description": "Parentheses and division",
                "expected_result": "20"
            }
        ]


class StatisticsCalculator(BaseTool):
    """Statistics calculator for data analysis"""
    
    def __init__(self):
        super().__init__(
            name="statistics",
            description="Calculate statistical measures for datasets",
            tool_type=ToolType.CALCULATOR
        )
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """Validate statistics parameters"""
        if not isinstance(parameters, dict):
            return False
        
        if "data" not in parameters:
            return False
        
        data = parameters["data"]
        if not isinstance(data, list) or len(data) == 0:
            return False
        
        # Check if all items are numbers
        try:
            [float(x) for x in data]
            return True
        except (ValueError, TypeError):
            return False
    
    def _get_parameter_schema(self) -> Dict[str, Any]:
        """Return parameter schema for statistics"""
        return {
            "type": "object",
            "properties": {
                "data": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Array of numbers to analyze",
                    "minItems": 1
                },
                "operations": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["mean", "median", "mode", "std", "variance", "min", "max", "sum", "count"]
                    },
                    "description": "Statistical operations to perform",
                    "default": ["mean", "median", "std", "min", "max"]
                }
            },
            "required": ["data"]
        }
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute statistical calculations"""
        data = [float(x) for x in parameters["data"]]
        operations = parameters.get("operations", ["mean", "median", "std", "min", "max"])
        
        results = {}
        n = len(data)
        
        try:
            if "count" in operations:
                results["count"] = n
            
            if "sum" in operations:
                results["sum"] = sum(data)
            
            if "min" in operations:
                results["min"] = min(data)
            
            if "max" in operations:
                results["max"] = max(data)
            
            if "mean" in operations:
                results["mean"] = sum(data) / n
            
            if "median" in operations:
                sorted_data = sorted(data)
                if n % 2 == 0:
                    results["median"] = (sorted_data[n//2 - 1] + sorted_data[n//2]) / 2
                else:
                    results["median"] = sorted_data[n//2]
            
            if "mode" in operations:
                from collections import Counter
                counts = Counter(data)
                max_count = max(counts.values())
                modes = [k for k, v in counts.items() if v == max_count]
                results["mode"] = modes[0] if len(modes) == 1 else modes
            
            if "variance" in operations or "std" in operations:
                mean = sum(data) / n
                variance = sum((x - mean) ** 2 for x in data) / n
                
                if "variance" in operations:
                    results["variance"] = variance
                
                if "std" in operations:
                    results["std"] = math.sqrt(variance)
            
            return {
                "statistics": results,
                "data_size": n,
                "operations_performed": operations
            }
            
        except Exception as e:
            raise Exception(f"Statistics calculation failed: {str(e)}")


# Tool registration function
def register_calculator_tools():
    """Register all calculator tools"""
    from .base import get_tool_manager
    
    tool_manager = get_tool_manager()
    
    # Register calculator tool
    calculator = CalculatorTool()
    tool_manager.register_tool(calculator)
    
    # Register statistics tool
    statistics = StatisticsCalculator()
    tool_manager.register_tool(statistics)
    
    return tool_manager
