"""Tools module - Tool interface, loader, and YAML tool implementations.

This module provides the core abstractions for defining and loading tools
that can be used by AI agents in sandbox scenarios.

Submodules:
    sandboxy.tools.base:
        - Tool: Protocol defining the tool interface
        - BaseTool: Base class for tool implementations
        - ToolConfig: Configuration model for tool instances
        - ToolResult: Result model for tool invocations

    sandboxy.tools.loader:
        - ToolLoader: Loader for creating tool instances from config
        - get_yaml_tool_libraries: List available YAML tool libraries
        - load_tool_class: Load a tool class from module path
        - load_yaml_tool_library: Load tools from a YAML library
        - load_yaml_tools_from_scenario: Load tools from scenario data

    sandboxy.tools.yaml_tools:
        - YamlMockTool: YAML-defined mock tool implementation
        - YamlToolLoader: Loader for YAML tool libraries
        - ActionSpec: Specification for a tool action
        - ParamSchema: Schema for action parameters
        - SideEffect: State modification specification
        - ToolSpec: Full tool specification
        - ToolLibrary: Collection of tool specifications
        - load_scenario_tools: Load tools from scenario data

Note:
    Import directly from submodules to avoid circular dependencies:
        from sandboxy.tools.base import BaseTool, ToolConfig, ToolResult
        from sandboxy.tools.loader import ToolLoader
"""
