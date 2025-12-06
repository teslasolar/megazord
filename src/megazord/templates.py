"""
Megazord UDT Template Generator
Generate ISA-compliant templates from UDT definitions
"""

from __future__ import annotations

import json
from dataclasses import fields, is_dataclass
from typing import Any, get_type_hints, get_origin, get_args

from megazord.core.udts import UDT_GPU, UDT_Model, UDT_Request, UDT_Alarm
from megazord.core.states import ST, RS, RM, AlarmClass


def get_isa_type(python_type: type) -> str:
    """Convert Python type to ISA-95 type."""
    type_map = {
        str: "STRING",
        int: "DINT",
        float: "REAL",
        bool: "BOOL",
        list: "ARRAY",
    }

    origin = get_origin(python_type)
    if origin is list:
        return "ARRAY"

    return type_map.get(python_type, "ANY")


def generate_tag_template(
    udt_class: type,
    area: str = "GPUCluster",
    unit: str = "INF",
    module: str = "GPU00",
) -> dict[str, str]:
    """
    Generate ISA-95 tag names from a UDT class.

    Args:
        udt_class: The UDT dataclass
        area: ISA-95 area name
        unit: ISA-95 unit name
        module: ISA-95 module name

    Returns:
        Dict mapping field names to ISA-95 tag names
    """
    if not is_dataclass(udt_class):
        raise ValueError(f"{udt_class} is not a dataclass")

    tags = {}
    hints = get_type_hints(udt_class)

    for field in fields(udt_class):
        field_type = hints.get(field.name, str)
        isa_type = get_isa_type(field_type)

        # Convert snake_case to PascalCase
        pascal_name = "".join(word.capitalize() for word in field.name.split("_"))

        tag_name = f"{area}_{unit}_{module}_{pascal_name}"
        tags[field.name] = {
            "tag": tag_name,
            "type": isa_type,
            "python_type": str(field_type),
        }

    return tags


def generate_json_schema(udt_class: type) -> dict[str, Any]:
    """
    Generate JSON Schema from a UDT class.

    Args:
        udt_class: The UDT dataclass

    Returns:
        JSON Schema dictionary
    """
    if not is_dataclass(udt_class):
        raise ValueError(f"{udt_class} is not a dataclass")

    hints = get_type_hints(udt_class)
    properties = {}
    required = []

    type_map = {
        str: {"type": "string"},
        int: {"type": "integer"},
        float: {"type": "number"},
        bool: {"type": "boolean"},
    }

    for field in fields(udt_class):
        field_type = hints.get(field.name, str)
        origin = get_origin(field_type)

        if origin is list:
            args = get_args(field_type)
            item_type = args[0] if args else str
            properties[field.name] = {
                "type": "array",
                "items": type_map.get(item_type, {"type": "string"}),
            }
        else:
            properties[field.name] = type_map.get(field_type, {"type": "string"})

        # Check if field has a default
        if field.default is field.default_factory is None:
            required.append(field.name)

    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": udt_class.__name__,
        "type": "object",
        "properties": properties,
        "required": required,
    }


def generate_typescript_interface(udt_class: type) -> str:
    """
    Generate TypeScript interface from a UDT class.

    Args:
        udt_class: The UDT dataclass

    Returns:
        TypeScript interface string
    """
    if not is_dataclass(udt_class):
        raise ValueError(f"{udt_class} is not a dataclass")

    hints = get_type_hints(udt_class)

    type_map = {
        str: "string",
        int: "number",
        float: "number",
        bool: "boolean",
    }

    lines = [f"interface {udt_class.__name__} {{"]

    for field in fields(udt_class):
        field_type = hints.get(field.name, str)
        origin = get_origin(field_type)

        if origin is list:
            args = get_args(field_type)
            item_type = args[0] if args else str
            ts_type = f"{type_map.get(item_type, 'any')}[]"
        else:
            ts_type = type_map.get(field_type, "any")

        lines.append(f"  {field.name}: {ts_type};")

    lines.append("}")
    return "\n".join(lines)


def generate_sql_schema(udt_class: type, table_name: str | None = None) -> str:
    """
    Generate SQL CREATE TABLE statement from a UDT class.

    Args:
        udt_class: The UDT dataclass
        table_name: Optional table name (defaults to lowercase class name)

    Returns:
        SQL CREATE TABLE statement
    """
    if not is_dataclass(udt_class):
        raise ValueError(f"{udt_class} is not a dataclass")

    hints = get_type_hints(udt_class)
    table = table_name or udt_class.__name__.lower().replace("udt_", "")

    type_map = {
        str: "TEXT",
        int: "INTEGER",
        float: "REAL",
        bool: "INTEGER",
    }

    columns = []
    for field in fields(udt_class):
        field_type = hints.get(field.name, str)
        origin = get_origin(field_type)

        if origin is list:
            sql_type = "TEXT"  # Store as JSON
        else:
            sql_type = type_map.get(field_type, "TEXT")

        # Mark 'h' as primary key
        if field.name == "h":
            columns.append(f"    {field.name} {sql_type} PRIMARY KEY")
        else:
            columns.append(f"    {field.name} {sql_type}")

    return f"CREATE TABLE {table} (\n" + ",\n".join(columns) + "\n);"


def generate_all_templates() -> dict[str, Any]:
    """Generate all templates for all UDTs."""
    udts = [UDT_GPU, UDT_Model, UDT_Request, UDT_Alarm]

    templates = {
        "udts": {},
        "enums": {},
    }

    for udt in udts:
        name = udt.__name__
        templates["udts"][name] = {
            "tags": generate_tag_template(udt),
            "json_schema": generate_json_schema(udt),
            "typescript": generate_typescript_interface(udt),
            "sql": generate_sql_schema(udt),
        }

    # Add enums
    for enum_class in [ST, RS, RM, AlarmClass]:
        templates["enums"][enum_class.__name__] = {
            name: value for name, value in enum_class.__members__.items()
        }

    return templates


def export_templates(output_path: str = "templates.json") -> None:
    """Export all templates to a JSON file."""
    templates = generate_all_templates()
    with open(output_path, "w") as f:
        json.dump(templates, f, indent=2, default=str)
    print(f"Templates exported to {output_path}")


# CLI support
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        output = sys.argv[1]
    else:
        output = "templates.json"

    export_templates(output)
