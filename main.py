import json
import subprocess
from pathlib import Path

from openai import OpenAI

SYSTEM_PROMPT = {
    "role": "system",
    "content": "You are a coding agent, use the tools to complete the task",
}

SKIP_DIRS = {".git", ".venv", "__pycache__"}


def list_files(path="."):
    try:
        base_path = Path(path)
        if not base_path.exists():
            return {"error": f"Path not found: {path}"}
        if base_path.is_file():
            return {"files": [str(base_path)]}

        files = sorted(
            str(file_path)
            for file_path in base_path.rglob("*")
            if not any(part in SKIP_DIRS for part in file_path.parts)
        )
        return {"files": files}
    except Exception as e:
        return {"error": str(e)}


def read_file(path):
    try:
        content = Path(path).read_text()
        return {"text": content}
    except FileNotFoundError:
        return {"error": f"File not found: {path}"}
    except Exception as e:
        return {"error": str(e)}


def search(query, path="."):
    try:
        base_path = Path(path)
        if not base_path.exists():
            return {"error": f"Path not found: {path}"}

        search_paths = (
            [base_path]
            if base_path.is_file()
            else sorted(
                file_path
                for file_path in base_path.rglob("*")
                if not any(part in SKIP_DIRS for part in file_path.parts)
            )
        )
        matches = []
        for file_path in search_paths:
            if not file_path.is_file():
                continue
            try:
                for line_number, line in enumerate(file_path.read_text().splitlines(), start=1):
                    if query in line:
                        matches.append(
                            {
                                "path": str(file_path),
                                "line_number": line_number,
                                "line": line,
                            }
                        )
            except Exception:
                continue

        return {"matches": matches}
    except Exception as e:
        return {"error": str(e)}


def write_file(path, content):
    try:
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        return {"status": "ok", "path": str(file_path)}
    except Exception as e:
        return {"error": str(e)}


def edit_file(path, old_text, new_text):
    try:
        file_path = Path(path)
        content = file_path.read_text()
        if old_text not in content:
            return {"error": f"Text not found in file: {path}"}

        updated_content = content.replace(old_text, new_text, 1)
        file_path.write_text(updated_content)
        return {"status": "ok", "path": str(file_path)}
    except FileNotFoundError:
        return {"error": f"File not found: {path}"}
    except Exception as e:
        return {"error": str(e)}


def run_command(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
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
        "name": "list_files",
        "description": "List files under a directory recursively",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
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
    {
        "type": "function",
        "name": "search",
        "description": "Search for text in a file or directory",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "path": {"type": "string"},
            },
            "required": ["query"],
        },
    },
    {
        "type": "function",
        "name": "edit_file",
        "description": "Replace the first occurrence of text in a file",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old_text": {"type": "string"},
                "new_text": {"type": "string"},
            },
            "required": ["path", "old_text", "new_text"],
        },
    },
    {
        "type": "function",
        "name": "write_file",
        "description": "Create or overwrite a file with new content",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "type": "function",
        "name": "run_command",
        "description": "Run a shell command and capture stdout, stderr, and exit code",
        "parameters": {
            "type": "object",
            "properties": {"cmd": {"type": "string"}},
            "required": ["cmd"],
        },
    },
]

tool_cmds = {
    "echo": echo,
    "list_files": list_files,
    "read_file": read_file,
    "search": search,
    "edit_file": edit_file,
    "write_file": write_file,
    "run_command": run_command,
}


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
