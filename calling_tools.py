import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from anthropic import Anthropic
from IPython.display import Markdown, display
from pydantic import BaseModel
import openai
import gradio as gr
import requests
import http.client
import json




load_dotenv(override=True)

system_prompt = """
You are a fact-conscious language model designed to prioritize epistemic accuracy over fluency or persuasion.

Your core principle is: “If it is not verifiable, do not claim it.”

Behavior rules:

1. When answering, clearly distinguish:

• Verified factual information  
• Probabilistic inference  
• Personal or cultural opinion  
• Unknown / unverifiable areas

2. Use cautious qualifiers when needed:

• “According to…”, “As of [date]…”, “It appears that…”  
• When unsure, say: “I dont know” or “This cannot be confirmed.”

3. Avoid hallucinations:

• Do not fabricate data, names, dates, events, studies, or quotes  
• Do not simulate sources or cite imaginary articles

4. When asked for evidence, only refer to known and trustworthy sources:

• Prefer primary sources, peer-reviewed studies, or official data

5. If the question contains speculative or false premises:

• Gently correct or flag the assumption  
• Do not expand upon unverifiable or fictional content as fact

Your tone is calm, informative, and precise. You are not designed to entertain or persuade, but to clarify and verify.

If browsing or retrieval tools are enabled, you may use them to confirm facts. If not, maintain epistemic humility and avoid confident speculation.

When you decide to push, call the `push_information` tool with
`payload` equal to the exact final answer you would otherwise reply with.

"""

#openai_api_base = os.getenv("OPENAI_API_BASE")
#openai_api_key = os.getenv("OPENAI_API_KEY")

#client = OpenAI(
#    base_url= openai_api_base, 
#    api_key= openai_api_key                 
#)
load_dotenv()  # this loads the variables from .env into environment
openai.api_key = os.getenv("OPENAI_API_KEY")


push_information_json = {
    "name": "push_information",
    "description": (
        "Use this tool when the user's message includes expressions such as "
        "'push it', 'run it', 'use it', 'activate it', 'start it', or similar phrases "
        "that clearly indicate the intention to execute or trigger a push information tool. "
        "This tool signals that an action should be initiated based on the user's command."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "intent_phrase": {"type": "string", "description": "Trigger phrase"},
            "context": {"type": "string", "description": "Why this is pushed"},
            "payload": {
                "type": "string",
                "description": "THE EXACT final assistant answer to push"
            }
        },
        "required": ["intent_phrase", "payload"],
        "additionalProperties": False
    }
}

web_search_json = {
    "name": "web_search",
    "description": (
        "Use this tool when the user's message clearly asks for real or recent information "
        "that must be looked up online  for example, when they say things like "
        "'search the web', 'look it up', 'find out', 'check online', 'what’s happening with', "
        "or otherwise imply they want current or factual data. "
        "This tool should be called whenever the answer requires external, up-to-date information."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The exact topic, question, or keywords to search for on the web."
            },
            "context": {
                "type": "string",
                "description": "Any relevant context or reasoning explaining why this web search is needed."
            }
        },
        "required": ["query"],
        "additionalProperties": False
    }
}

pushover_user = os.getenv("PUSHOVER_USER")
pushover_token = os.getenv("PUSHOVER_TOKEN")
pushover_url = "https://api.pushover.net/1/messages.json"
serper_token = os.getenv("SERPER_API_KEY")

def push(message):
    print(f"Push: {message}")
    payload = {"user": pushover_user, "token": pushover_token, "message": message}
    requests.post(pushover_url, data=payload)


def push_information(intent_phrase="intent_phrase not provided", context="not provided", payload=""):
    print("__________________________________________________________________________")
    print(f"push_information called: intent_phrase {intent_phrase}, context: {context}, payload: {payload}")
    push_info = "context: " + context + "\n" + payload
    push(push_info)
    return {"recorded": "ok"}

def web_search(query: str, context="not provided"):
    print("__________________________________________________________________________")
    print(f"web_search called: query {query}, context: {context}")
    conn = http.client.HTTPSConnection("google.serper.dev")
    payload = json.dumps({
    "q": f"{query}"
    })
    headers = {
    'X-API-KEY': f'{serper_token}',
    'Content-Type': 'application/json'
    }
    conn.request("POST", "/search", payload, headers)
    res = conn.getresponse()
    data = res.read()
    string_data = data.decode("utf-8")
    return string_data


def handle_tool_calls(tool_calls):
    results = []
    for tool_call in tool_calls:
        print("_____________________________________________________________________")
        print(f"hande_tool_calls called: {tool_calls}")
        tool_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        print(f"Tool called: {tool_name}", flush=True)

        # THE BIG IF STATEMENT!!!

        if tool_name == "push_information":
            print("_____________________________________________________________________")
            print("handle tool calls push_information arguments")
            print(f"arguments: {arguments}")
            result = push_information(**arguments)
        elif tool_name == "web_search":
            print("_____________________________________________________________________")
            print("handle tool calls web_search arguments")
            print(f"arguments: {arguments}")
            result = web_search(**arguments)

        results.append({"role": "tool","content": json.dumps(result),"tool_call_id": tool_call.id})
    return results

tools = [{"type": "function", "function": push_information_json},
         {"type": "function", "function": web_search_json}]

def chat(message, history):
    messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": message}]
    done = False
    while not done:
        response = openai.chat.completions.create(model="gpt-4o-mini", messages=messages, tools=tools)
        finish_reason = response.choices[0].finish_reason
        print("____________________________________________________________________________________________")
        print(f"Chat Response: {response.choices[0]}")
        print(f"Chat finish_reason {finish_reason}")
        print("____________________________________________________________________________________________")
        if finish_reason=="tool_calls":
            #print(f"message: tool call {message}")
            message = response.choices[0].message
            tool_calls = message.tool_calls
            results = handle_tool_calls(tool_calls)
            messages.append(message)
            messages.extend(results)
        else:
            done = True
    return response.choices[0].message.content



gr.ChatInterface(chat, type="messages").launch()