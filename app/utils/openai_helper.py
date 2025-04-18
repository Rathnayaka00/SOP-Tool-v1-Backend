import os
import openai
import json
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

async def generate_sop(topic: str, description: str):
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert SOP writer. Generate a detailed, structured, and professional Standard Operating Procedure (SOP) "
                    "based on the given topic and description. Use hierarchical numbering format for clarity and organization, such as:\n\n"
                    "1. Main Section\n"
                    "   1.1 Subsection\n"
                    "       1.1.1 Detailed Step\n"
                    "2. Next Main Section\n"
                    "   2.1 Subsection\n\n"
                    "Ensure the SOP is logically ordered, easy to follow, and practical for real-world execution."
                )
            },
            {
                "role": "user",
                "content": f"Topic: {topic}\nDescription: {description}"
            }
        ],
        functions=[
            {
                "name": "generate_sop",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "details": {"type": "string", "description": "Detailed structured SOP using hierarchical numbering."},
                        "summary": {"type": "string", "description": "Brief summary of SOP."}
                    }
                }
            }
        ],
        function_call="auto"
    )

    try:
        response_data = json.loads(response.choices[0].message.function_call.arguments)
        return response_data 
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse OpenAI response: {e}")
