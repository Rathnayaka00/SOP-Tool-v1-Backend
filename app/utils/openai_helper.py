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
            {"role": "system", "content": "Generate a well-structured and clear SOP with step by step based on the given topic and description."},
            {"role": "user", "content": f"Topic: {topic}\nDescription: {description}"}
        ],
        functions=[
            {
                "name": "generate_sop",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "details": {"type": "string", "description": "Detailed structured SOP."},
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
