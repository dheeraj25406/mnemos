import pytest
from mnemos.mcp.server import mcp_server


def test_mcp_server_initialization():
    assert mcp_server.name == "mnemos"
    # Verify tools registered on mcp server
    assert hasattr(mcp_server, "_tool_manager") or hasattr(mcp_server, "list_tools")
