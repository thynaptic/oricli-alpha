import os
import requests

api_key = os.environ.get("OricliAlpha_Key")
headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

query = """
mutation TerminatePod($input: PodTerminateInput!) {
  podTerminate(input: $input)
}
"""

response = requests.post(
    "https://api.runpod.io/graphql", 
    json={"query": query, "variables": {"input": {"podId": "9hsv5gmq05hgub"}}}, 
    headers=headers
)
print(response.json())
