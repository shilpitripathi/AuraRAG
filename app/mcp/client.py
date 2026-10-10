import json
import os

from dotenv import load_dotenv
from mcp import Client

# Load variables from .env
load_dotenv()


def format_mcp_result(result) -> str:
    """
    Convert an MCP CallToolResult into clean, readable text context for the LLM.
    Inspects both result.structured_content and result.content to safely extract
    title, URL, publication date, and excerpts.
    """
    if not result:
        return ""

    formatted_items = []

    def _extract_from_dict(data: dict):
        if not isinstance(data, dict):
            return
        results_list = data.get("results")
        if isinstance(results_list, list) and results_list:
            for r in results_list:
                if not isinstance(r, dict):
                    continue
                title = r.get("title") or "Untitled Source"
                url = r.get("url") or ""
                date_val = r.get("publish_date")
                date_info = f" ({date_val})" if date_val else ""
                raw_excerpts = r.get("excerpts", [])
                if isinstance(raw_excerpts, list):
                    excerpts = "\n".join(
                        f"- {exp.strip()}" for exp in raw_excerpts if isinstance(exp, str) and exp.strip()
                    )
                elif isinstance(raw_excerpts, str) and raw_excerpts.strip():
                    excerpts = f"- {raw_excerpts.strip()}"
                else:
                    excerpts = ""

                entry_lines = [f"Source: {title}{date_info}"]
                if url:
                    entry_lines.append(f"URL: {url}")
                if excerpts:
                    entry_lines.append(f"Key Information:\n{excerpts}")
                formatted_items.append("\n".join(entry_lines))

    # 1. Try structured_content first
    structured = getattr(result, "structured_content", None)
    if isinstance(structured, dict):
        _extract_from_dict(structured)

    # 2. Try content items (e.g. JSON strings or text) if structured_content didn't yield results
    if not formatted_items and hasattr(result, "content") and result.content:
        for item in result.content:
            text = getattr(item, "text", "")
            if not text:
                continue
            try:
                data = json.loads(text)
                if isinstance(data, dict):
                    _extract_from_dict(data)
                elif isinstance(data, list):
                    for d in data:
                        if isinstance(d, dict):
                            _extract_from_dict(d)
            except Exception:
                formatted_items.append(text.strip())

    # 3. Fallback to raw text representation if nothing was extracted
    if not formatted_items:
        if hasattr(result, "content") and result.content:
            for item in result.content:
                text = getattr(item, "text", "")
                if text and text.strip():
                    formatted_items.append(text.strip())
        elif isinstance(result, str):
            return result
        else:
            return str(result)

    return "\n\n---\n\n".join(formatted_items)


async def get_mcp_tools():
    """
    Connect to the external MCP server and discover the tools it provides.
    """
    server_url = os.getenv("MCP_SERVER_URL", "https://search.parallel.ai/mcp")
    if not server_url:
        raise ValueError("MCP_SERVER_URL is not configured in the environment or .env file.")

    try:
        async with Client(server_url) as client:
            tools_response = await client.list_tools()
            return tools_response.tools
    except Exception as e:
        raise RuntimeError(f"Failed to connect or discover tools from MCP server at {server_url}: {e}") from e


async def call_mcp_tool(tool_name: str, arguments: dict):
    """
    Connect to the external MCP server, discover available tools,
    verify that the requested tool exists, inspect its input_schema,
    validate arguments, and execute it.
    """
    server_url = os.getenv("MCP_SERVER_URL", "https://search.parallel.ai/mcp")
    if not server_url:
        raise ValueError("MCP_SERVER_URL is not configured in the environment or .env file.")

    try:
        async with Client(server_url) as client:
            # 1. Discover available tools
            tools_response = await client.list_tools()
            tools_list = tools_response.tools
            available_tool_names = [t.name for t in tools_list]

            # 2. Validate tool presence
            target_tool = next((t for t in tools_list if t.name == tool_name), None)
            if not target_tool:
                raise RuntimeError(
                    f"Requested MCP tool '{tool_name}' is not provided by the MCP server at {server_url}. "
                    f"Available tools: {available_tool_names}"
                )

            # 3. Inspect input_schema and validate required arguments
            schema = target_tool.input_schema if isinstance(target_tool.input_schema, dict) else {}
            required_properties = schema.get("required", [])
            missing_args = [arg for arg in required_properties if arg not in arguments]
            if missing_args:
                expected_props = list(schema.get("properties", {}).keys())
                raise ValueError(
                    f"Missing required argument(s) {missing_args} for tool '{tool_name}'. "
                    f"Tool input_schema requires: {required_properties}. Expected properties: {expected_props}"
                )

            # 4. Call the tool
            result = await client.call_tool(tool_name, arguments)

            # 5. Check if tool returned an error
            if getattr(result, "is_error", False):
                err_text = ""
                if hasattr(result, "content") and result.content:
                    err_text = " ".join(getattr(c, "text", "") for c in result.content if getattr(c, "text", ""))
                raise RuntimeError(f"MCP tool '{tool_name}' returned error: {err_text}")

            # 6. Diagnostic debug logging (safe, no secrets)
            print("\n========== MCP DEBUG ==========")
            print(f"Server: {server_url}")
            print(f"Available tools: {available_tool_names}")
            print(f"Tool: {tool_name}")
            print(f"Arguments: {json.dumps(arguments, ensure_ascii=False)}")
            res_summary = ""
            if hasattr(result, "structured_content") and result.structured_content:
                if isinstance(result.structured_content, dict) and "results" in result.structured_content:
                    res_summary = f"{len(result.structured_content['results'])} structured results"
                else:
                    res_summary = f"structured_content keys: {list(result.structured_content.keys())}"
            elif hasattr(result, "content") and result.content:
                res_summary = f"{len(result.content)} content items, text length: {sum(len(getattr(c, 'text', '')) for c in result.content)}"
            else:
                res_summary = str(result)[:300]
            print(f"Result: {res_summary}")
            print("================================\n")

            return result
    except Exception as e:
        if not isinstance(e, (RuntimeError, ValueError)):
            raise RuntimeError(f"MCP client failed while executing '{tool_name}' on {server_url}: {e}") from e
        raise