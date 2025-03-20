import os
import logging
import dotenv
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    GetPromptResult,
    Prompt,
    PromptMessage,
    PromptArgument
)
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import chromadb
from chromadb.utils.embedding_functions import openai_embedding_function
import glob
from importlib import metadata
from langchain_community.document_loaders import PyPDFLoader

# logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("document-search-mcp")

# Environment Variables
dotenv.load_dotenv()

# Initialize Server
server = Server("document-search")

# Initialize ChromaDB Client
client = None
embedding_function = None
collection = None

# Format search result helper function for query_document tool
def format_search_result(document: str, distance: float, metadata: dict[str, object] = None) -> str:
    result = f"Score: {1 - distance:.4f} (closer to 1 is better)\n"

    if metadata:
        page_num = metadata.get('page', 'Unknown')
        result += f"Page: {page_num}"
        
    result += f"Content: {document}"
    return result


# List avaliable tools in the server
@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    return [
        Tool(
            name="query_document",
            description="Search for information in the document based on semantic similarity",
            inputSchema={
                "type": "object",
                "properties":{
                    "query_text": {
                        "type": "string",
                        "description": "The search query text"
                    },
                    "num_results": {
                        "type": "integer",
                        "description": "Number of results to return (default: 5)"
                    }
                },
                "required": ["query_text"]
            }
        ),
        Tool(
            name="get_collection_info",
            description="Get information about the ChromaDB collection",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
    ]


# Handle tool execution requests
@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[TextContent | ImageContent | EmbeddedResource]:
    if name == "query_document":
        query_text = arguments.get("query_text", "")
        num_results = arguments.get("num_results", 5)

        try:
            if not collection:
                return [TextContent(
                    type="text",
                    text="Error: ChromaDB collection is not initialized. Please run chroma_setup.ipynb first."
                )]
            
            results = collection.query(
                query_text=[query_text],
                n_results = num_results
            )

            if not results or 'documents' not in results or not results['documents'][0]:
                return [TextContent(type="text", text="No results found for you query.")]
            
            formatted_result = []
            for i, (doc, distance, metadata) in enumerate(zip(
                results['documents'][0],
                results['distances'][0],
                results['metadatas'][0] if 'metadata' in results else [{}] * len(results['documents'[0]])
            )):
                formatted_result.append(f"Result {i+1}: \n{format_search_result(doc, distance, metadata)}")

            return [TextContent(
                type="text",
                text="\n\n---\n\n".join(formatted_result)
            )]

        except Exception as ex:
            error_message = f"Error getting collection info: {str(ex)}"
            logger.error(error_message)
            return [TextContent(type="text", text=error_message)]
        
    elif name == "get_collection_info":
        try:
            if not collection:
                return [TextContent(
                    type="text",
                    text="Error: ChromaDB collection is not initialized. Please run chroma_setup.ipynb first."
                )]
            
            count = collection.count()
            return [TextContent(
                    type="text",
                    text=f"Collection name: pdf_collection\nNumber of documents: {count}"
                )]
        except Exception as ex:
            error_message = f"Error getting collection info: {str(ex)}"
            logger.error(error_message)
            return [TextContent(type="text", text=error_message)]
    else:
        raise ValueError(f"Unknown tool: {name}")



# List avaliable resources in the server
@server.list_resources()
async def handle_list_resource() -> list[Resource]:
    resources = []

    try:
        pdf_files = glob.glob("../test/*.pdf")
        for pdf_path in pdf_files:
            filename = os.path.basename(pdf_path)
            name_without_ext = os.path.splitext(filename)[0]

            resources.append(
                Resource(
                    uri=f"document://pdf/{name_without_ext}",
                    name=name_without_ext.replace('_', ' ').title(),
                    description=f"PDF Document: {name_without_ext}",
                    mimeType="application/pdf"
                )
            )
    except Exception as ex:
        logger.error(f"Error scanning for PDF files: {ex}")

    return resources


# Handle reading PDF resources
@server.read_resource()
async def handle_read_resource(uri: str):
    if not str(uri).startswith("document://"):
        raise ValueError(f"Unsupported URI scheme: {uri}")
    
    path_parts = str(uri).split("/")
    if len(path_parts) < 4:
        raise ValueError(f"Invalie URI format: {uri}")
    
    resouce_type = path_parts[2]
    if resouce_type != "pdf":
        raise ValueError(f"Unsupported resource type: {resouce_type}")
    
    document_name = path_parts[3]

    try:
        path = f"../test/{document_name}"
        if not path.endswith(".pdf"):
            path += ".pdf"

        # Load the document
        loader = PyPDFLoader(path)
        pages = loader.load()

        # Combine all pages into one text with page markers
        full_text = ""
        for i, page in enumerate(pages):
            full_text += f"\n\n--- Page (i + 1) ---\n\n"
            full_text += page.page_content

        logger.info(f"Loaded document {document_name} with {len(pages)} pages, Preview: {full_text[:200]}...")
        return full_text
    except Exception as ex:
        error_message = f"Error loading document: {str(ex)}"
        logger.error(error_message)
        return error_message
    

# List avaliable prompts in the server
@server.list_prompts()
async def handle_list_prompts() -> list[Prompt]:
    return [
        Prompt(
            name="deep_analysis",
            description="Perform deep analysis on ducument sections",
            arguments=[
                PromptArgument(
                    name="query",
                    description="What aspect to analyze (e.g., 'main themes', 'methodology')",
                    required=True
                )
            ]
        ),
        Prompt(
            name="extract_key_information",
            description="Extract specific types of information from ducument sections",
            arguments=[
                PromptArgument(
                    name="info_type",
                    description="Type of information to extract(definitions, people, statistics, processes, arguments)",
                    required=True
                )
            ]
        )
    ]


# Handle prompt execution requires
@server.get_prompt()
async def handle_get_prompt(name: str, arguments: dict[str, str] | None) -> GetPromptResult:
    if arguments is None:
        arguments = {}

    
    if name =="deep_analysis":
        print(f"mcp server: {name}, {arguments}")
        query = arguments.get("query", "main themes")
        print(f"mcp server: {name}, {query}")

        return GetPromptResult(
            description=f"Deep analysis focusing on {query}",
            messages=[
                PromptMessage(
                    role="assistant",
                    content=TextContent(
                        type="text",
                        text="I am a document analysis expert specializing in identifying key themes, arguments, and evidence in academic and the technical documents."
                    )
                ),
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=f"""Please perform a deep analysis of the document section provided in the conversation, focusing on {query}.
                        Include in your analysis:
                        - Main themes and arguments presented
                        - Key evidence and supporting details
                        - Logical structure and flow of information
                        - Implicit assumptions made in the test
                        - Strengths and weakness of the arguments
                        - Connections to broader context if applicable
                        
                        Format your analysis in a well-structured manner with clear heading and concise explanations."""
                    )
                )
            ]
        )

    elif name == "extract_key_information":
        info_type = arguments.get("info_type", "key information")

        return GetPromptResult(
            description=f"Extracting all mentions of {info_type} from document",
            messages=[
                PromptMessage(
                    role="assistant",
                    content=TextContent(
                        type="text",
                        text="I am a precise information extraction specialist expertise in technical documents."
                    )
                ),
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=f"""Based on the document section provided in the conversation, please extract all mentions of {info_type}.
                        Format your response as a structured list with:
                        1. Clear headers for each extracted element
                        2. Direct quotes or references when applicable
                        3. Brief explanations of significance where helpful
                        4. Page or section references if avaliable
                        Be comprehensive but foces on quality over quantity. If no mention of the requested info_type is found, just return "No mentions of {info_type}" found.
                        """
                    )
                )
            ]
        )
    else:
        raise ValueError(f"Unknown prompt: {name}")


# Run the mcp server using stdio/stdout streams
async def main():
    try:
        dist = metadata.distribution("document-search-mcp")
        version = dist.version
    except:
        version = "0.1.0"

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="document-search-mcp",
                server_version=version,
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                )
            )
        )


# Main Function
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())