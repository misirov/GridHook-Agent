from openai import OpenAI
from dotenv import load_dotenv
from typing import List, Dict, Any
load_dotenv()
import os


class LLMAgent:
    def __init__(self, config):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = config.LLM_MODEL
        self.prompt = config.PROMPT


    def create_chat_completion(
            self, 
            messages: List[Dict[str, str]], 
            tools: List[Dict[str, Any]] = None
        ) -> Any:
        """Create a chat completion with the OpenAI API"""
        try:
            # Add system prompt to the start of messages
            if not any(msg.get("role") == "system" for msg in messages):
                messages.insert(0, {
                    "role": "system",
                    "content": self.prompt
                })
            
            # Create completion
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools if tools else None
            )
            
            return completion
        except Exception as e:
            print(f"Error creating chat completion: {str(e)}")
            raise
