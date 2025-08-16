import os
from openai import OpenAI
from agent.config import MODEL_NAME, TEMPERATURE, REASONING, STORE, STREAM, TOOL_CHOICE, VERBOSITY, get_system_prompt
import json
from datetime import datetime

class Agent:
    def __init__(self, name, tools, user_id=None, chat_history=[], generated_images=[], add_timestamp=False):
        self.name = name
        self.tools = tools
        self.user_id = user_id
        self.add_timestamp = add_timestamp
        self.client = OpenAI()
        self.instructions = get_system_prompt(self.name)
        self.tool_schemas = [tool.schema for tool in self.tools]
        self.token_usage = {}
        self.token_usage_history = {}
        self.function_call_detected = False
        self.iteration = 1
        self.chat_history = chat_history
        self.chat_history_during_run = []
        self.generated_images = generated_images

        # throw an error if user_id is None or empty
        if not self.user_id or not isinstance(self.user_id, str):
            raise ValueError("user_id must be a non-empty string.")

        print(self.color_text(f"\n{'='*50}\nWelcome to your virtual assistant '{self.name}'!\n{'='*50}", '36'))

    def color_text(self, text, color_code):
        # Windows PowerShell supports ANSI escape codes in recent versions
        return f"\033[{color_code}m{text}\033[0m"

    def run(self, user_input=None):
        self.chat_history_during_run = []
        self.function_call_detected = False
        self.iteration = 1

        # if user_input None or is not string or is empty, return None
        if user_input is None or not isinstance(user_input, str) or not user_input.strip():
            yield{
                "type": "response.agent.done",
                "message": "No user input provided or input is invalid.",
                "chat_history": self.chat_history_during_run,
                "generated_images": self.generated_images
            }
            return

        # start the Agent loop
        while True:
            # if user_input is None and no function call was detected in the previous iteration, break the agent loop
            if user_input is None and not self.function_call_detected:
                yield {
                    "type": "response.agent.done",
                    "message": "Agent run completed without further user input.",
                    "chat_history": self.chat_history_during_run,
                    "generated_images": self.generated_images
                }
                return

            # if user_input is not None and no function call was detected, it means we are in the first iteration or the user provided new input
            if user_input and not self.function_call_detected:
                # if self.add_timestamp is True, append a timestamp to the user input in markdown format
                if self.add_timestamp:
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    user_input = f"> **Timestamp:** `{timestamp}`\nUser's input: {user_input}"
                # Append user input to chat history

                user_message = {
                    "role": "user",
                    "content": [{ "type": "input_text", "text": user_input },]
                }
                if self.generated_images:
                    for img in self.generated_images:
                        user_message["content"].append(img)
                self.chat_history.append(user_message)

                # set user_input to None to avoid reusing it in the next iteration
                user_input = None

            # clear the function call detection flag for the next iteration
            self.function_call_detected = False
            self.chat_history_during_run = []

            stream = self.client.responses.create(
                model=MODEL_NAME,
                instructions=self.instructions,
                input=self.chat_history,
                prompt_cache_key=self.user_id,
                store=STORE,
                stream=STREAM,
                reasoning=REASONING,
                text=VERBOSITY,
                temperature=TEMPERATURE,
                tool_choice=TOOL_CHOICE,
                tools=self.tool_schemas
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
                    with open(os.path.join("events_logs", f"event_{self.iteration}.json"), "w") as f:
                        json.dump(make_serializable(event), f, indent=4)

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
                            # self.chat_history_during_run.append(output_item)
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

                else:
                    # Handle other event types if necessary
                    pass
        
            if self.chat_history_during_run:
                # Append the chat history during this run to the main chat history
                self.chat_history += self.chat_history_during_run
                # Reset the chat history for the next iteration
                self.chat_history_during_run = []

            user_input = None
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
