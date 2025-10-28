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
from rich.console import Console

console = Console(record=True)



load_dotenv(override=True)

system_prompt = f"You have the ability to use the tool to search on internet and send the result to the user"

openai_api_base = os.getenv("OPENAI_API_BASE")
openai_api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(
    base_url= openai_api_base, 
    api_key= openai_api_key                 
)
load_dotenv()  # this loads the variables from .env into environment
#openai.api_key = os.getenv("OPENAI_API_KEY")


push_information_json = {
    "name": "push_information",
    "description": (
        "Use this tool to record the result of a question asked by the user"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "intent_phrase": {"type": "string", "description": "Trigger phrase"},
            "context": {"type": "string", "description": "Why this is recorded"},
            "payload": {
                "type": "string",
                "description": "The final assistant answer to record"
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
        "that must be looked up online"
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
    console.print(f"[green]Push: {message}[/green]")
    payload = {"user": pushover_user, "token": pushover_token, "message": message}
    requests.post(pushover_url, data=payload)


def push_information(intent_phrase="intent_phrase not provided", context="not provided", payload=""):
    console.print("[dim]__________________________________________________________________________[/dim]")
    console.print(f"[green]push_information called: intent_phrase={intent_phrase}, context={context}, payload={payload}[/green]")

    push_info = "context: " + context + "\n" + payload
    push(push_info)
    return {"recorded": "ok"}

def web_search(query: str, context="not provided"):
    console.print("[dim]__________________________________________________________________________[/dim]")
    console.print(f"[green]web_search called: query {query}, context: {context}[/green]")
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
    console.print(f"[red]")
    return string_data


def handle_tool_calls(tool_calls):
    results = []
    for tool_call in tool_calls:
        console.print("[dim]__________________________________________________________________________[/dim]")
        console.print(f"[cyan]hande_tool_calls called: {tool_calls}[/cyan]")
        tool_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        console.print(f"[cyan]Tool called: {tool_name}[/cyan]")

        # THE BIG IF STATEMENT!!!

        if tool_name == "push_information":
            console.print("[dim]__________________________________________________________________________[/dim]")
            console.print("[cyan]handle tool calls push_information arguments[/cyan]")
            console.print(f"[cyan]arguments: {arguments}[/cyan]")
            result = push_information(**arguments)
        elif tool_name == "web_search":
            console.print("[dim]__________________________________________________________________________[/dim]")
            console.print("[cyan]handle tool calls web_search arguments[/cyan]")
            console.print(f"[cyan]arguments: {arguments}[/cyan]")
            result = web_search(**arguments)

        results.append({"role": "tool","content": json.dumps(result),"tool_call_id": tool_call.id})
    return results

tools = [{"type": "function", "function": push_information_json},
         {"type": "function", "function": web_search_json}]

def chat(message, history):
    messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": message}]
    done = False
    while not done:
        response = client.chat.completions.create(model="gpt-oss-120b", messages=messages, tools=tools)
        finish_reason = response.choices[0].finish_reason
        console.print("[dim]__________________________________________________________________________[/dim]")
        console.print(f"[green]Chat Response: {response.choices[0]}[/green]")
        console.print(f"[green]Chat finish_reason {finish_reason}[/green]")
        console.print("[dim]__________________________________________________________________________[/dim]")
        if finish_reason=="tool_calls":
            #print(f"message: tool call {message}")
            message = response.choices[0].message
            tool_calls = message.tool_calls
            results = handle_tool_calls(tool_calls)
            messages.append(message)
            messages.extend(results)
        else:
            done = True
            console.print("[dim]__________________________________________________________________________[/dim]")
            console.print(f"[red]result displayed[/red]")
    content = response.choices[0].message.content
    if content is None:
        content = "(Keine Textantwort vom Modell)"
    return response.choices[0].message.content




gr.ChatInterface(chat, type="messages").launch()
console.save_text("logs/run-gpt-oss-120b.md")