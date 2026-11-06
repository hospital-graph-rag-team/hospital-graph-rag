import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# Load .env
ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# Add src to path to import graph retrieval
sys.path.append(str(Path(__file__).resolve().parents[1]))
from graph.retrieval import get_patient_history, get_best_medications_for_condition

def run_clinical_query(user_prompt: str):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in .env file.")

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1"
    )

    system_instruction = (
        "You are an expert clinical data assistant with direct access to a hospital knowledge graph. "
        "When answering questions, call the appropriate database tools to retrieve factual "
        "patient trajectories, lab biomarkers, and medication outcome statistics. "
        "Base your clinical assessment strictly on the returned data and explain the temporal progression."
    )

    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": user_prompt}
    ]

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_patient_history",
                "description": "Retrieves the longitudinal clinical history for a specific patient_id (e.g., 'P101').",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "patient_id": {"type": "string"}
                    },
                    "required": ["patient_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_best_medications_for_condition",
                "description": "Retrieves comparative betterment rates of different medications for a condition.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "condition": {"type": "string"}
                    },
                    "required": ["condition"]
                }
            }
        }
    ]

    print(f"\n[Query]: {user_prompt}\n")
    print("Initiating agentic chat session with Groq (Llama 3.1 70B)...")

    # The ReAct Agent Loop: The model decides when to stop calling tools
    while True:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=messages,
            tools=tools,
            temperature=0.1
        )
        
        response_message = response.choices[0].message
        messages.append(response_message)

        # If the model didn't call a tool, it means it has written the final answer
        if not response_message.tool_calls:
            print("-> Synthesizing final clinical response...")
            return response_message.content

        # If it did call tools, execute them and append the results
        for tool_call in response_message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            print(f"-> Executing Graph Tool: {function_name}({function_args})")
            
            if function_name == "get_patient_history":
                function_response = get_patient_history(function_args.get("patient_id"))
            elif function_name == "get_best_medications_for_condition":
                function_response = get_best_medications_for_condition(function_args.get("condition"))
            else:
                function_response = {"error": "Unknown function"}

            messages.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": function_name,
                "content": json.dumps(function_response, default=str)
            })

if __name__ == "__main__":
    test_query = (
        "What is the most effective medication for Hyperlipidemia in our hospital, "
        "and what medication was patient P101 given for it? Did P101's lab values improve over time?"
    )
    answer = run_clinical_query(test_query)
    print("\n--- Clinical Agent Response ---")
    print(answer)