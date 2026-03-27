import json
import subprocess
from pathlib import Path

from openai import OpenAI

SYSTEM_PROMPT = {
    "role": "system",
    "content": "You are a coding agent, use the tools to complete the task",
}


def read_file(path):
    try:
        content = Path(path).read_text()
        return {"text": content}
    except FileNotFoundError:
        return {"error": f"File not found: {path}"}
    except Exception as e:
        return {"error": str(e)}


def echo(text):
    result = subprocess.run(["/usr/bin/echo", text], capture_output=True, text=True)
    return {"result": result.stdout}


available_tools = [
    {
        "type": "function",
        "name": "echo",
        "description": "Run the Linux echo command",
        "parameters": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
    {
        "type": "function",
        "name": "read_file",
        "description": "Read the contents of a file",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
]

tool_cmds = {"echo": lambda text: ["/usr/bin/echo", text], "read_file": read_file}


def agent_loop(client, user_msg):
    input_items = [SYSTEM_PROMPT, {"role": "user", "content": user_msg}]
    print("agent_loop")
    while True:
        print(f"Before calling LLM： {input_items=}")
        response = client.responses.create(
            model="gpt-4.1",
            input=input_items,
            tools=available_tools,
        )
        if not response.output:
            print("No response.output received!")
            break
        # non_text_types = []
        # for item in response.output:
        #    non_text_types.append(item.type)
        # print(f"The non text types: {non_text_types}")
        tool_calls = [item for item in response.output if item.type == "function_call"]
        input_items.extend(list(response.output))
        if not tool_calls:
            print("No tool calls needed, can complet here.")
            break

        for tool_call in tool_calls:
            print("name: ", tool_call.name)
            print("call_id: ", tool_call.call_id)
            args = json.loads(tool_call.arguments)
            print("arguments: ", args)
            print("tool_call: ", tool_call)
            tool_output = tool_cmds[tool_call.name](**args)
            # tool_output = subprocess.run(
            #    tool_cmds[tool_call.name](**args),
            #    capture_output=True,
            #    text=True,
            # )
            print(f"tool call output: {type(tool_output)}, {tool_output=}")
            input_items.append(
                {
                    "type": "function_call_output",
                    "call_id": tool_call.call_id,
                    "output": json.dumps(tool_output),
                }
            )
    return response.output_text


def main():
    print("Hello World!")
    client = OpenAI()
    # for model in client.models.list().data[:20]:
    #    print(model.id)
    user_msg = ""
    result = ""
    while True:
        user_msg = input("> ")
        if user_msg in ["q", "quit"]:
            break
        result = agent_loop(client, user_msg)
        print(f"{result}")
    print(result)


if __name__ == "__main__":
    main()
