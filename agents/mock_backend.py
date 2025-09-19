"""
Mock backend for testing agent integration.
This simulates the RAG backend responses without requiring Azure services.
"""

import asyncio
import json
import logging
from quart import Quart, request, jsonify

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Quart(__name__)

# Mock responses for testing
MOCK_RESPONSES = {
    "hello": {
        "answer": "Hello! I'm your AI assistant. I can help you search through documents and answer questions. How can I assist you today?",
        "data_points": {
            "text": [],
            "citations": []
        },
        "thoughts": [
            {
                "title": "Greeting Response",
                "description": "Generated a friendly greeting response"
            }
        ],
        "token_usage": {
            "prompt_tokens": 10,
            "completion_tokens": 25,
            "total_tokens": 35
        },
        "model_info": {
            "model": "gpt-4",
            "temperature": "0.3"
        }
    },
    "benefits": {
        "answer": "Based on the policy document, the main benefits include comprehensive health coverage, flexible work arrangements, professional development opportunities, and competitive compensation packages. These benefits are designed to support employee well-being and career growth.",
        "data_points": {
            "text": [
                "Policy Document: The company offers comprehensive health coverage including medical, dental, and vision insurance.",
                "Policy Document: Flexible work arrangements are available including remote work options and flexible hours.",
                "Policy Document: Professional development opportunities include training programs, conference attendance, and tuition reimbursement."
            ],
            "citations": [
                "Policy Document (Page 1)",
                "Policy Document (Page 2)",
                "Policy Document (Page 3)"
            ]
        },
        "thoughts": [
            {
                "title": "Document Search",
                "description": "Searched through policy documents for benefit information"
            },
            {
                "title": "Response Generation",
                "description": "Generated comprehensive response about benefits"
            }
        ],
        "token_usage": {
            "prompt_tokens": 150,
            "completion_tokens": 75,
            "total_tokens": 225
        },
        "model_info": {
            "model": "gpt-4",
            "temperature": "0.3"
        }
    }
}

@app.route("/", methods=["GET"])
async def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "Mock RAG Backend",
        "version": "1.0.0"
    })

@app.route("/chat", methods=["POST"])
async def chat():
    """Chat endpoint that simulates RAG responses."""
    try:
        data = await request.get_json()
        messages = data.get("messages", [])
        
        if not messages:
            return jsonify({"error": "No messages provided"}), 400
        
        # Get the last user message
        last_message = None
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_message = msg.get("content", "").lower()
                break
        
        if not last_message:
            return jsonify({"error": "No user message found"}), 400
        
        # Determine response based on message content
        if "hello" in last_message or "hi" in last_message:
            response = MOCK_RESPONSES["hello"]
        elif "benefit" in last_message or "policy" in last_message:
            response = MOCK_RESPONSES["benefits"]
        else:
            # Default response
            response = {
                "answer": f"I understand you're asking about '{last_message}'. I'm a mock backend for testing purposes. In a real implementation, I would search through your documents and provide detailed answers with citations.",
                "data_points": {
                    "text": [],
                    "citations": []
                },
                "thoughts": [
                    {
                        "title": "Mock Response",
                        "description": "Generated mock response for testing"
                    }
                ],
                "token_usage": {
                    "prompt_tokens": 50,
                    "completion_tokens": 30,
                    "total_tokens": 80
                },
                "model_info": {
                    "model": "gpt-4",
                    "temperature": "0.3"
                }
            }
        
        logger.info(f"Mock backend responding to: {last_message}")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in mock chat endpoint: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/chat/stream", methods=["POST"])
async def chat_stream():
    """Streaming chat endpoint that simulates streaming RAG responses."""
    try:
        data = await request.get_json()
        messages = data.get("messages", [])
        
        if not messages:
            return jsonify({"error": "No messages provided"}), 400
        
        # Get the last user message
        last_message = None
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_message = msg.get("content", "").lower()
                break
        
        if not last_message:
            return jsonify({"error": "No user message found"}), 400
        
        # Determine response based on message content
        if "hello" in last_message or "hi" in last_message:
            response_text = MOCK_RESPONSES["hello"]["answer"]
        elif "benefit" in last_message or "policy" in last_message:
            response_text = MOCK_RESPONSES["benefits"]["answer"]
        else:
            response_text = f"I understand you're asking about '{last_message}'. I'm a mock backend for testing purposes."
        
        # Simulate streaming by sending the response in chunks
        async def generate_stream():
            words = response_text.split()
            for i, word in enumerate(words):
                chunk = {
                    "type": "content",
                    "content": word + " " if i < len(words) - 1 else word
                }
                yield json.dumps(chunk) + "\n"
                await asyncio.sleep(0.1)  # Simulate delay
            
            # Send final chunk
            final_chunk = {
                "type": "done",
                "content": ""
            }
            yield json.dumps(final_chunk) + "\n"
        
        from quart import Response
        return Response(
            generate_stream(),
            mimetype="application/x-ndjson",
            headers={"Content-Type": "application/x-ndjson"}
        )
        
    except Exception as e:
        logger.error(f"Error in mock streaming chat endpoint: {e}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    logger.info("Starting mock backend on http://localhost:50505")
    app.run(host="0.0.0.0", port=50505, debug=True)