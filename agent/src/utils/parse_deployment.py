
import json
from pathlib import Path
from typing import Dict, List, Tuple

def parse_deployments(broadcast_dir: str = "../broadcast") -> List[Tuple[str, str]]:
    """
    Parse contract deployments from the latest broadcast file.
    """
    try:
        # Find the latest broadcast file
        broadcast_path = Path(broadcast_dir)
        latest_files = list(broadcast_path.rglob("run-latest.json"))
        
        if not latest_files:
            raise FileNotFoundError("No run-latest.json files found")
            
        deployments = []
        
        # Parse each run-latest.json file found
        for file_path in latest_files:
            with open(file_path) as f:
                data = json.load(f)
                
            # Extract contract deployments from transactions
            for tx in data.get("transactions", []):
                if tx.get("transactionType") == "CREATE" and tx.get("contractAddress"):
                    contract_name = tx.get("contractName")
                    contract_address = tx.get("contractAddress")
                    
                    if contract_name and contract_address:
                        deployments.append((contract_name, contract_address))
        
        return deployments
                    
    except Exception as e:
        print(f"Error parsing deployments: {str(e)}")
        return []

# Example usage
if __name__ == "__main__":
    deployments = parse_deployments()
    
    print("Contract Deployments:")
    print("--------------------")
    for name, address in deployments:
        print(f"{name}: {address}")