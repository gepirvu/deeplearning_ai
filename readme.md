I can't directly create downloadable files, but I can provide you with the content that you can easily save as README.md. Here's what you should do:
Option 1: Copy and Save

Copy the text below
Create a new file named README.md in your project directory
Paste the content and save

Option 2: Use Command Line
Copy the content below and run:
bashcat > README.md << 'EOF'
[paste content here]
EOF
Here's the complete README.md content:

markdown# arXiv Research MCP Server

A Model Context Protocol (MCP) server that provides tools for searching and retrieving information from arXiv papers, with both terminal and web interfaces.

## 🔍 Overview

This project implements an MCP server for searching academic papers on arXiv. It provides two interfaces:

1. **Terminal Chatbot** (`chatbot_mcp.py`): Command-line interface using Anthropic's SDK
2. **Gradio Web UI** (`research_mcp_server.py`): Browser-based chat interface with streaming responses

**Key Features:**
- 🔎 Search arXiv papers by topic with configurable result limits
- 📄 Extract detailed paper information (title, authors, summary, PDF URL, publication date)
- 💾 Automatic local caching of paper metadata in JSON format
- ⚡ Streaming responses and real-time tool usage visualization

**Tech Stack:**
- **FastMCP** for MCP server implementation
- **arXiv API** for paper search and retrieval
- **Anthropic Claude 3.7 Sonnet** for natural language understanding
- **Gradio** for web interface
- **stdio transport** for local communication

## 📦 Prerequisites

- **Python 3.12+** installed on your system
- **uv** Python package manager (install via `curl -LsSf https://astral.sh/uv/install.sh | sh` on macOS/Linux)
- **Anthropic API Key** from https://console.anthropic.com/
- **Node.js and npm** (optional, only needed for MCP Inspector)

## 🚀 Installation

1. Create and navigate to project directory
2. Add the three project files: `research_mcp_server.py`, `chatbot_mcp.py`, and `pyproject.toml`
3. Create a `.env` file with your `ANTHROPIC_API_KEY`
4. Initialize virtual environment with `uv venv` and activate it
5. Install dependencies with `uv sync`

## 📁 Project Structure
mcp-course/
├── research_mcp_server.py  # MCP server with Gradio UI and tools
├── chatbot_mcp.py          # Terminal chatbot client
├── pyproject.toml          # Dependencies and metadata
├── .env                    # API keys (never commit!)
├── papers/                 # Auto-created cache directory
│   └── [topic]/
│       └── papers_info.json
└── .venv/                  # Virtual environment

**Key Files:**

- **`research_mcp_server.py`**: Contains MCP tool implementations (`search_papers`, `extract_info`), Anthropic integration, and Gradio web interface
- **`chatbot_mcp.py`**: MCP client that connects to the server via stdio and provides a terminal chat interface
- **`pyproject.toml`**: Defines all dependencies including `mcp`, `anthropic`, `arxiv`, `gradio`, and `nest-asyncio`

## 🎯 Usage

### Running the Gradio Web UI

Run `uv run research_mcp_server.py` to launch the web interface at `http://127.0.0.1:7860` with streaming responses, tool usage visualization, and pre-loaded example queries.

**Example queries:**
- "Search for papers about large language models"
- "Who are the authors of paper 2411.15764v1?"

### Running the Terminal Chatbot

Run `uv run chatbot_mcp.py` for an interactive command-line interface. Type queries or 'quit' to exit.

### Testing with MCP Inspector

Run `npx @modelcontextprotocol/inspector uv run research_mcp_server.py` to open a web UI at `http://localhost:5173` for testing tools directly.

### Using with Claude Desktop

1. Locate the config file at `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows)
2. Add server configuration with command `uv` and args pointing to your project directory
3. Restart Claude Desktop completely

### Available Tools

**`search_papers(topic: str, max_results: int = 5)`**
- Searches arXiv and caches results locally
- Returns list of paper IDs

**`extract_info(paper_id: str)`**
- Retrieves cached paper details
- Returns JSON with title, authors, summary, PDF URL, publication date

## 🏗️ Architecture

### MCP Server Architecture

The `research_mcp_server.py` file contains:
- **FastMCP Server Setup** with `@mcp.tool()` decorated functions running in stdio transport mode
- **Tool Functions** that interface with arXiv API and manage local JSON cache
- **Anthropic Integration** using Claude 3.7 Sonnet with tool calling and streaming responses
- **Gradio Interface** with chat history management and tool usage display

### Terminal Chatbot Architecture

The `chatbot_mcp.py` file contains:
- **MCP_chatbot Class** managing ClientSession, Anthropic API client, and tool schemas
- **Connection Flow** using StdioServerParameters and stdio_client context manager
- **Query Processing Loop** handling user input, tool use detection, and response formatting

### Data Flow

User queries flow through Anthropic Claude for tool decision making. Text responses are displayed directly, while tool use triggers MCP server execution. Tool results are formatted and returned to the user.

**Key Components:**

1. **FastMCP Decorators**: Automatically expose functions as MCP tools
2. **Async/Await**: Both files use asyncio for concurrent operations
3. **stdio Transport**: Server and client communicate via standard input/output
4. **Tool Schema**: JSON schemas define parameters for Claude's tool calling
5. **Message History**: Maintains conversation context across tool uses