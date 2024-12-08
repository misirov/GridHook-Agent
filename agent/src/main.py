import json
from datetime import datetime
from utils.llm import LLMAgent
from utils.contract_functions import ContractFunctions
from config import Config
from utils.initialize_web3 import initialize_web3
from utils.contract_functions import ContractFunctions


def main():
    try:
        web3 = initialize_web3(Config.RPC_URL)
        print(f"Connected to network at {Config.RPC_URL}")
        
        llm = LLMAgent(Config)
        
        # Initialize Contract Functions
        contract_functions = ContractFunctions(Config)
        
        # Contract functions
        tools = contract_functions.available_tools
        
        messages = []
        
        print("\nGrid Trading Bot initialized. Type 'exit' or 'bye' to quit.")
        print(f"Connected to Grid Hook at: {Config.GRID_HOOK_ADDRESS}")
        print(f"Using account (public key): {web3.eth.account.from_key(Config.PRIVATE_KEY).address}\n")
        
        while True:
            user_input = input("> ").strip()
            if user_input.lower() in ['exit', 'bye']:
                print("Goodbye!")
                break
            
            # Add user message to conversation
            messages.append({"role": "user", "content": user_input})
            
            # Get LLM response
            completion = llm.create_chat_completion(messages, tools)
            
            # Handle the response
            assistant_message = completion.choices[0].message
            tool_calls = assistant_message.tool_calls
            
            if tool_calls:
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    # Call the appropriate function
                    if hasattr(contract_functions, function_name):
                        result = getattr(contract_functions, function_name)(**function_args)
                    else:
                        result = f"Function {function_name} not found"
                    
                    # Add function call and result to messages
                    messages.append(assistant_message)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": function_name,
                        "content": str(result)
                    })
                
                # Get final response
                completion = llm.client.chat.completions.create(
                    model="gpt-4-turbo-preview",
                    messages=messages
                )
                print("\nAssistant:", completion.choices[0].message.content)
            else:
                messages.append(assistant_message)
                print("\nAssistant:", assistant_message.content)

    except Exception as e:
        print(f"\nError: {str(e)}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code if exit_code is not None else 0)