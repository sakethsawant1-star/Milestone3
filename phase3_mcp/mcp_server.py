import sys
import os

# Add the project root to sys.path so we can import modules
# In Railway, the working directory is the project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.fastmcp import FastMCP
import logging

from phase3_mcp.docs_tool import append_to_doc
from phase3_mcp.gmail_tool import create_email_draft

# Setup basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("mcp_server")

# ---------------------------------------------------------------------------
# Determine transport mode from environment
# ---------------------------------------------------------------------------
# Railway sets PORT and RAILWAY_* env vars automatically.
# If we detect those, use SSE transport on that port.
# Otherwise, fall back to stdio for local development.
RAILWAY = bool(os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RAILWAY_PROJECT_ID"))
PORT = int(os.environ.get("PORT", 8000))

# Create the FastMCP server with the correct host/port for SSE mode
if RAILWAY:
    mcp = FastMCP(
        "GoogleWorkspaceMCP",
        host="0.0.0.0",
        port=PORT,
    )
else:
    mcp = FastMCP("GoogleWorkspaceMCP")


# ---------------------------------------------------------------------------
# Tool definitions (identical for both transports)
# ---------------------------------------------------------------------------

@mcp.tool()
def append_doc(doc_id: str, content: str) -> str:
    """
    Append content to a Google Document.

    Args:
        doc_id: The ID of the Google Document (found in the URL).
        content: The text content to append to the document.
    """
    logger.info(f"Tool append_doc called with doc_id: {doc_id}")

    result = append_to_doc(doc_id, content)

    if result.get("status") == "success":
        return f"Successfully appended to document. Document ID: {result.get('document_id')}"
    else:
        raise Exception(f"Failed to append to document: {result.get('message')} - {result.get('details', '')}")


@mcp.tool()
def create_draft(to: str, subject: str, body: str) -> str:
    """
    Create a Gmail draft.

    Args:
        to: The email address of the recipient.
        subject: The subject of the email.
        body: The main content/body of the email.
    """
    logger.info(f"Tool create_draft called with to: {to}, subject: {subject}")

    result = create_email_draft(to, subject, body)

    if result.get("status") == "success":
        return f"Successfully created email draft. Draft ID: {result.get('draft_id')}"
    else:
        raise Exception(f"Failed to create draft: {result.get('message')} - {result.get('details', '')}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if RAILWAY:
        logger.info(f"Starting MCP server in SSE mode on 0.0.0.0:{PORT}")
        mcp.run(transport="sse")
    else:
        logger.info("Starting MCP server in stdio mode (local development)")
        mcp.run(transport="stdio")
