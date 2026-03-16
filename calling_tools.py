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


system_prompt = (
    "You have exactly ONE tool available: web_search. "
    "Do NOT invent or call any other tools. "
    "After ONE web search, always summarize the results and answer the user directly. "
    "Never call web_search more than once per user question."
)

openai_api_base = "http://ip:8000/v1"
openai_api_key = "no_key"

client = OpenAI(
   base_url= openai_api_base, 
   api_key= openai_api_key                 
)

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

serper_token = "token" #you can get a free one on the official website


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
        tool_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        console.print(f"[cyan]Tool called: {tool_name}, args: {arguments}[/cyan]")

        if tool_name == "web_search":
            query = arguments.get("query", "")
            context = arguments.get("context", "not provided")
            result = web_search(query=query, context=context)
        else:
            # Unbekanntes Tool abfangen
            console.print(f"[red]Unbekanntes Tool: {tool_name} — wird ignoriert[/red]")
            result = f"Tool '{tool_name}' existiert nicht. Nur 'web_search' ist verfügbar."

        results.append({
            "role": "tool",
            "content": json.dumps(result),
            "tool_call_id": tool_call.id
        })
    return results

tools = [{"type": "function", "function": web_search_json}]

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




gr.ChatInterface(chat).launch()
