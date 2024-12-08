from pathlib import Path
import json


def load_abi(contract_name: str) -> dict:
    """Load ABI from Foundry artifacts"""
    current_dir = Path(__file__).parent
    project_root = current_dir.parent.parent.parent
    artifact_path = project_root / 'out' / f'{contract_name}.sol' / f'{contract_name}.json'    
    with open(artifact_path) as f:
        contract_json = json.load(f)
        return contract_json['abi']

