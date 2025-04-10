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

async def edit_sop(topic: str, existing_details: str, user_suggestion: str):
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Edit the existing SOP based on the user's suggestion while maintaining the structure and format."},
            {"role": "user", "content": f"Topic: {topic}\nExisting SOP:\n{existing_details}\n\nUser Suggestion: {user_suggestion}"}
        ],
        functions=[
            {
                "name": "edit_sop",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "details": {"type": "string", "description": "Edited detailed structured SOP."},
                        "summary": {"type": "string", "description": "Brief summary of the edited SOP."}
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