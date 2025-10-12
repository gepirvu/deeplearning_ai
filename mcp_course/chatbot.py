# %%
import arxiv
import json
import os
import gradio as gr
from typing import List, Generator
from dotenv import load_dotenv
import anthropic

# %%

PAPER_DIR = "papers"
load_dotenv()


# %%

def search_papers(topic: str, max_results: int = 5) -> List[str]:
    """
    Search for papers on arXiv based on a topic and store their information.
    
    Args:
        topic: The topic to search for
        max_results: Maximum number of results to retrieve (default: 5)
        
    Returns:
        List of paper IDs found in the search
    """
    
    # Use arxiv to find the papers 
    client = arxiv.Client()

    # Search for the most relevant articles matching the queried topic
    search = arxiv.Search(
        query = topic,
        max_results = max_results,
        sort_by = arxiv.SortCriterion.Relevance
    )

    papers = client.results(search)
    
    # Create directory for this topic
    path = os.path.join(PAPER_DIR, topic.lower().replace(" ", "_"))
    os.makedirs(path, exist_ok=True)
    
    file_path = os.path.join(path, "papers_info.json")

    # Try to load existing papers info
    try:
        with open(file_path, "r") as json_file:
            papers_info = json.load(json_file)
    except (FileNotFoundError, json.JSONDecodeError):
        papers_info = {}

    # Process each paper and add to papers_info  
    paper_ids = []
    for paper in papers:
        paper_ids.append(paper.get_short_id())
        paper_info = {
            'title': paper.title,
            'authors': [author.name for author in paper.authors],
            'summary': paper.summary,
            'pdf_url': paper.pdf_url,
            'published': str(paper.published.date())
        }
        papers_info[paper.get_short_id()] = paper_info
    
    # Save updated papers_info to json file
    with open(file_path, "w") as json_file:
        json.dump(papers_info, json_file, indent=2)
    
    print(f"Results are saved in: {file_path}")
    
    return paper_ids

# %%
search_papers("llm")

# %%
def extract_info(paper_id: str) -> str:
    """
    Search for information about a specific paper across all topic directories.
    
    Args:
        paper_id: The ID of the paper to look for
        
    Returns:
        JSON string with paper information if found, error message if not found
    """
 
    for item in os.listdir(PAPER_DIR):
        item_path = os.path.join(PAPER_DIR, item)
        if os.path.isdir(item_path):
            file_path = os.path.join(item_path, "papers_info.json")
            if os.path.isfile(file_path):
                try:
                    with open(file_path, "r") as json_file:
                        papers_info = json.load(json_file)
                        if paper_id in papers_info:
                            return json.dumps(papers_info[paper_id], indent=2)
                except (FileNotFoundError, json.JSONDecodeError) as e:
                    print(f"Error reading {file_path}: {str(e)}")
                    continue
    
    return f"There's no saved information related to paper {paper_id}."

# %%
extract_info('2412.18022v1')


# %%
### Tool Schema
tools = [
    {
        "name": "search_papers",
        "description": "Search for papers on arXiv based on a topic and store their information.",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "The topic to search for"
                }, 
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to retrieve",
                    "default": 5
                }
            },
            "required": ["topic"]
        }
    },
    {
        "name": "extract_info",
        "description": "Search for information about a specific paper across all topic directories.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paper_id": {
                    "type": "string",
                    "description": "The ID of the paper to look for"
                }
            },
            "required": ["paper_id"]
        }
    }
]

# %%# Tool Mapping

mapping_tool_function = {
    "search_papers": search_papers,
    "extract_info": extract_info
}

def execute_tool(tool_name, tool_args):
    """
    Execute a tool function by name with the provided arguments.
    
    Args:
        tool_name: Name of the tool to execute (must be in mapping_tool_function)
        tool_args: Dictionary of arguments to pass to the tool function
        
    Returns:
        String representation of the tool execution result
    """

    result = mapping_tool_function[tool_name](**tool_args)

    if result is None:
        result = "The operation completed but didn't return any results."
        
    elif isinstance(result, list):
        result = ', '.join(result)
        
    elif isinstance(result, dict):
        # Convert dictionaries to formatted JSON strings
        result = json.dumps(result, indent=2)
    
    else:
        # For any other type, convert using str()
        result = str(result)
    return result

# %%

#####Query Processing

client = anthropic.Anthropic()

def chat_with_claude(message: str, history: List[List[str]]) -> Generator[str, None, None]:
    
    """
    Process a chat message with Claude and yield responses for streaming.
    
    Args:
        message: The user's message
        history: Chat history in Gradio format [[user_msg, assistant_msg], ...]
        
    Yields:
        Partial responses as they are generated
    """
    
    # Convert Gradio history format to Anthropic messages format
    messages = []
    for user_msg, assistant_msg in history:
        messages.append({'role': 'user', 'content': user_msg})
        if assistant_msg:
            messages.append({'role': 'assistant', 'content': assistant_msg})
    
    # Add current message
    messages.append({'role': 'user', 'content': message})
    
    # Process with Claude
    response = client.messages.create(
        max_tokens=2024,
        model='claude-3-7-sonnet-20250219', 
        tools=tools,
        messages=messages
    )
    
    full_response = ""
    process_query = True
    
    while process_query:
        assistant_content = []

        for content in response.content:
            if content.type == 'text':
                full_response += content.text
                yield full_response
                assistant_content.append(content)
                
                if len(response.content) == 1:
                    process_query = False
            
            elif content.type == 'tool_use':
                assistant_content.append(content)
                messages.append({'role': 'assistant', 'content': assistant_content})
                
                tool_id = content.id
                tool_args = content.input
                tool_name = content.name
                
                # Show tool usage to user
                tool_msg = f"\n\n🔧 Using tool: `{tool_name}` with args: `{tool_args}`\n\n"
                full_response += tool_msg
                yield full_response
                
                # Execute tool
                result = execute_tool(tool_name, tool_args)
                messages.append({
                    "role": "user", 
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": result
                        }
                    ]
                })
                
                # Get next response
                response = client.messages.create(
                    max_tokens=2024,
                    model='claude-3-7-sonnet-20250219', 
                    tools=tools,
                    messages=messages
                ) 
                
                if len(response.content) == 1 and response.content[0].type == "text":
                    full_response += response.content[0].text
                    yield full_response
                    process_query = False




# %%
# Create Gradio interface
def create_interface():
    """
    Create and launch the Gradio chat interface.
    
    Returns:
        Gradio ChatInterface object
    """
    
    interface = gr.ChatInterface(
        fn=chat_with_claude,
        title="📚 arXiv Paper Search Assistant",
        description="Ask me to search for papers on arXiv or get information about specific papers!",
        examples=[
            "Search for papers about large language models",
            "Search for recent papers on reinforcement learning",
            "Who are the authors of paper 2411.15764v1?",
        ],
        theme=gr.themes.Soft(),


    )
    
    return interface

# %%
if __name__ == "__main__":
    #mcp.run(transport='stdio') # Run MCP in stdio mode for local testing, for production use 'sse'
    interface = create_interface()
    interface.launch()