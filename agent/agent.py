import os
import json
from datetime import datetime
from openai import OpenAI
from .config import AgentConfig

class Agent:
    def __init__(self, name, tools, user_id=None, add_timestamp=False, config: AgentConfig | None = None):
        """AI Agent wrapper.

        Parameters:
            name: Agent display/name identifier.
            tools: Iterable of tool objects exposing a 'schema' attribute and 'run' method.
            user_id: Required unique user identifier (used for caching, etc.).
            add_timestamp: (reserved) whether to add timestamps to messages.
            config: Optional AgentConfig instance. If omitted, a default AgentConfig() is created.
        """
        self.name = name
        self.tools = tools
        self.user_id = user_id
        self.add_timestamp = add_timestamp
        self.config = config or AgentConfig()
        self.client = OpenAI()
        # Use config's system prompt (supports custom template modifications)
        self.instructions = self.config.get_system_prompt(self.name)
        self.tool_schemas = [tool.schema for tool in self.tools]
        self.token_usage = {}
        self.token_usage_history = {}
        self.function_call_detected = False
        self.iteration = 1
        self.chat_history_during_run = []  # per-run ephemeral history additions
        self.generated_images = []

        if not self.user_id or not isinstance(self.user_id, str):
            raise ValueError("user_id must be a non-empty string.")

    def color_text(self, text, color_code):
        # Windows PowerShell supports ANSI escape codes in recent versions
        return f"\033[{color_code}m{text}\033[0m"

    def run(self, input_messages=None, max_turns=16):
        self.chat_history_during_run = []
        self.function_call_detected = False
        self.iteration = 1
        self._run_start_time = datetime.now()

        # if messages None or is not string or is empty, return None
        if input_messages is None:
            yield{
                "type": "response.agent.done",
                "message": "No user input provided or input is invalid.",
                "duration_seconds": (datetime.now() - self._run_start_time).total_seconds(),
                "chat_history": self.chat_history_during_run,
                "generated_images": self.generated_images
            }
            return

        # start the Agent loop
        while True:
            # Guard against runaway loops (SDK would raise MaxTurnsExceeded)
            if self.iteration > max_turns:
                yield {
                    "type": "response.agent.done",
                    "message": f"Max turns exceeded (max_turns={max_turns}).",
                    "duration_seconds": (datetime.now() - self._run_start_time).total_seconds(),
                    "chat_history": self.chat_history_during_run,
                    "generated_images": self.generated_images
                }
                return
            # if this is not the first iteration and no function call was detected, break the agent loop
            if self.iteration > 1 and not self.function_call_detected:
                yield {
                    "type": "response.agent.done",
                    "message": "Agent run completed without further user input or function calls.",
                    "duration_seconds": (datetime.now() - self._run_start_time).total_seconds(),
                    "chat_history": self.chat_history_during_run,
                    "generated_images": self.generated_images
                }
                return
            elif self.iteration == 1:
                self.chat_history_during_run = []

            # clear the function call detection flag for the next iteration
            self.function_call_detected = False

            # Effective settings come straight from the config object
            model = self.config.model_name
            temperature = self.config.temperature
            reasoning = self.config.reasoning
            text = self.config.text
            store = self.config.store
            stream = self.config.stream
            tool_choice = self.config.tool_choice
            include = self.config.include
            prompt_cache_key = self.user_id

            # wrap the request in try except
            try:
                # exclude text and reasoning if a model's name does not start with "gpt-5"
                if not model.startswith("gpt-5"):
                    reasoning = None
                    text = None
                    include = []
                
                stream = self.client.responses.create(
                    model=model,
                    instructions=self.instructions,
                    input=input_messages + self.chat_history_during_run,
                    prompt_cache_key=prompt_cache_key,
                    store=store,
                    stream=stream,
                    reasoning=reasoning,
                    text=text,
                    temperature=temperature,
                    tool_choice=tool_choice,
                    tools=self.tool_schemas,
                    include=include
                )
                for event in stream:
                    if event.type == "response.reasoning_summary_part.added":
                        yield {"type": "response.reasoning_summary_part.added"}
                    elif event.type == "response.reasoning_summary_text.delta":
                        yield {"type": "response.reasoning_summary_text.delta", "delta": event.delta}
                    elif event.type == "response.reasoning_summary_text.done":
                        yield {"type": "response.reasoning_summary_text.done", "text": event.text}
                    elif event.type == "response.content_part.added":
                        yield {"type": "response.content_part.added"}
                    elif event.type == "response.output_text.delta":
                        yield {"type": "response.output_text.delta", "delta": event.delta}
                    elif event.type == "response.output_text.done":
                        yield {"type": "response.output_text.done", "text": event.text}
                    elif event.type == "response.output_item.done":
                        if event.item.type in ["function_call", "custom_tool_call"]:
                            yield {"type": "response.output_item.done", "item": event.item}
                    elif event.type == "response.image_generation_call.generating":
                        yield {"type": "response.image_generation_call.generating"}

                    elif event.type == "response.image_generation_call.partial_image":
                        yield {"type": "response.image_generation_call.partial_image", "data": event}

                    elif event.type == "response.image_generation_call.completed":
                        yield {"type": "response.image_generation_call.completed", "data": event}

                    elif event.type == "response.completed":
                        # Collect token usage for this iteration
                        self.token_usage = {
                            "iteration": self.iteration,
                            "input_tokens": event.response.usage.input_tokens,
                            "cached_tokens": event.response.usage.input_tokens_details.cached_tokens,
                            "output_tokens": event.response.usage.output_tokens,
                            "reasoning_tokens": event.response.usage.output_tokens_details.reasoning_tokens,
                            "total_tokens": event.response.usage.total_tokens
                        }
                        # Retain token usage for this iteration
                        self.token_usage_history[self.iteration] = self.token_usage

                        # Append the AI agent output items to the chat history
                        for output_item in event.response.output:
                            # Check if the output item is a function call
                            if output_item.type == "function_call":
                                # Check if a function call was detected
                                self.function_call_detected = True

                                # Get the function call details
                                function_call = output_item
                                function_call_id = function_call.call_id
                                function_call_arguments = json.loads(function_call.arguments)
                                function_call_name = function_call.name
                                function_call_result = None

                                try:
                                    # Find and run the correct tool
                                    for tool in self.tools:
                                        if tool.schema["name"] == function_call_name:
                                            function_call_result = tool.run(**function_call_arguments)
                                            break
                                except Exception as e:
                                    function_call_result = {"type": "error", "message": f"Error occurred while calling function {function_call_name}: {e}"}

                                # Append the function call and its result to the chat history
                                self.chat_history_during_run.append(make_serializable(function_call))
                                self.chat_history_during_run.append({
                                    "type": "function_call_output",
                                    "call_id": function_call_id,
                                    "output": json.dumps(function_call_result),
                                })

                            elif output_item.type == "custom_tool_call":
                                # Append the custom tool call output item to the chat history
                                # self.chat_history_during_run.append(output_item)
                                pass

                            elif output_item.type == "reasoning":
                                # Append the reasoning output item to the chat history
                                final_item = make_serializable(output_item)
                                # remove status from final_item
                                final_item.pop("status", None)
                                self.chat_history_during_run.append(make_serializable(final_item))
                                pass

                            elif output_item.type == "message":
                                # Append the assistant message output item to the chat history
                                self.chat_history_during_run.append(make_serializable(output_item))

                            elif output_item.type == "image_generation_call":
                                # Handle image generation call output item
                                base64_image = output_item.result
                                self.generated_images.append({
                                    "type": "input_image",
                                    "image_url": f"data:image/png;base64,{base64_image}",
                                })

                        yield {"type": "response.completed", "usage": self.token_usage}

                    elif event.type == "error":
                        # Handle error output item
                        assistant_message_with_error = {
                            "role": "assistant",
                            "content": [
                                {
                                    "type": "output_text",
                                    "text": f"An error occurred: {event.message}",
                                }
                            ]
                        }
                        self.chat_history_during_run.append(make_serializable(assistant_message_with_error))

            except Exception as e:
                # Handle error output item
                assistant_message_with_error = {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "output_text",
                            "text": f"An error occurred: {str(e)}",
                        }
                    ]
                }
                self.chat_history_during_run.append(make_serializable(assistant_message_with_error))

                yield {
                    "type": "response.agent.done",
                    "message": f"An error occurred during agent run: {str(e)}",
                    "duration_seconds": (datetime.now() - self._run_start_time).total_seconds(),
                    "chat_history": self.chat_history_during_run,
                    "generated_images": self.generated_images
                }
                return 

            self.iteration += 1

def make_serializable(obj):
    if hasattr(obj, '__dict__'):
        return {k: make_serializable(v) for k, v in obj.__dict__.items()}
    elif isinstance(obj, list):
        return [make_serializable(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: make_serializable(v) for k, v in obj.items()}
    else:
        return obj
