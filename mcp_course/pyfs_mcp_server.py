from mcp.server.fastmcp import FastMCP
import os

mcp = FastMCP("filesystem")

@mcp.tool()
def write_file(path: str, content: str) -> str:
    """
    Write content to a file.
    
    Args:
        path: Path to the file
        content: Content to write
        
    Returns:
        Success message
    """
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote to {path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"

@mcp.tool()
def read_text_file(path: str) -> str:
    """
    Read content from a text file.
    
    Args:
        path: Path to the file
        
    Returns:
        File content
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

@mcp.tool()
def list_directory(path: str = ".") -> str:
    """
    List files in a directory.
    
    Args:
        path: Directory path (default: current directory)
        
    Returns:
        List of files and directories
    """
    try:
        items = os.listdir(path)
        return "\n".join(sorted(items))
    except Exception as e:
        return f"Error listing directory: {str(e)}"

@mcp.tool()
def create_directory(path: str) -> str:
    """
    Create a new directory.
    
    Args:
        path: Path for the new directory
        
    Returns:
        Success message
    """
    try:
        os.makedirs(path, exist_ok=True)
        return f"Successfully created directory: {path}"
    except Exception as e:
        return f"Error creating directory: {str(e)}"

if __name__ == "__main__":
    mcp.run(transport='stdio')