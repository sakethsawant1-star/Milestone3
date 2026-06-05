import asyncio
from dotenv import load_dotenv
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from phase3_mcp.mcp_client import GrowwMCPClient

async def test_docs():
    load_dotenv()
    print(f"Connecting to MCP Server at: {os.environ.get('MCP_SERVER_URL', 'stdio (local)')}")
    
    doc_id = input("\nEnter your Google Document ID: ").strip()
    
    if not doc_id:
        print("Error: Document ID is required.")
        return

    content = "Hello from Railway! If you are reading this, the MCP integration is 100% working! 🎉\n\n"
    print("\nSending request to Railway server...")

    try:
        async with GrowwMCPClient() as client:
            result = await client.call_tool("append_doc", {
                "doc_id": doc_id,
                "content": content
            })
            print("\n✅ SUCCESS!")
            print(f"Response from server: {result}")
            print("\nCheck your Google Doc, the text should be there!")
    except Exception as e:
        print(f"\n❌ FAILED!")
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_docs())
