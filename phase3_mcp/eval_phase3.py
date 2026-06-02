import sys
import os
import asyncio

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from phase3_mcp.mcp_client import GrowwMCPClient

PASS = "[PASS]"
FAIL = "[FAIL]"
results = []

def record(test_name: str, passed: bool, detail: str = ""):
    """Record a test result."""
    status = PASS if passed else FAIL
    results.append((test_name, passed))
    msg = f"  {status}  {test_name}"
    if detail:
        msg += f" - {detail}"
    print(msg)

async def test_mcp_connection():
    print("\n--- Test Group 1: MCP Server Connection & Tool Fetching ---")
    
    # We must ensure auth is done or the server will fail to start/run properly.
    # Actually, auth.py is called from docs_tool.py which is imported at the top of mcp_server.py.
    # We will test connection first.
    
    try:
        async with GrowwMCPClient() as client:
            record("MCP Client connected via stdio", True)
            
            tools = await client.list_tools()
            tool_names = [t['name'] for t in tools]
            
            record("Fetched tools successfully", True, f"Found: {tool_names}")
            record("append_doc tool is available", 'append_doc' in tool_names)
            record("create_draft tool is available", 'create_draft' in tool_names)
    except Exception as e:
        record("MCP Client connected via stdio", False, str(e))
        record("Fetched tools successfully", False)
        record("append_doc tool is available", False)
        record("create_draft tool is available", False)

def main():
    print("\n" + "=" * 60)
    print("  Phase 3 Evaluation: MCP Client & Server")
    print("=" * 60 + "\n")
    
    asyncio.run(test_mcp_connection())
    
    print("\n" + "=" * 60)
    total = len(results)
    passed = sum(1 for _, p in results if p)
    failed = total - passed
    print(f"  RESULTS: {passed}/{total} passed, {failed} failed")

    if failed == 0:
        print("  >>> Phase 3 EXIT CRITERIA MET - Ready for Phase 4!")
    else:
        print("  >>> Phase 3 BLOCKED - Fix failing tests before proceeding.")
        for name, p in results:
            if not p:
                print(f"      X {name}")

    print("=" * 60 + "\n")
    sys.exit(0 if failed == 0 else 1)

if __name__ == "__main__":
    main()
