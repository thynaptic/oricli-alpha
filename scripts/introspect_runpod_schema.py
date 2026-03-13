
import os
import requests
import json

RUNPOD_API_KEY = os.environ.get("OricliAlpha_Key")
RUNPOD_ENDPOINT = "https://api.runpod.io/graphql"

query = """
query IntrospectionQuery {
  __type(name: "CreateClusterInput") {
    name
    inputFields {
      name
      type {
        name
        kind
        ofType {
          name
          kind
        }
      }
    }
  }
}
"""

def introspect():
    if not RUNPOD_API_KEY:
        print("Error: OricliAlpha_Key (RunPod API Key) not found in environment.")
        return

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {RUNPOD_API_KEY}"
    }
    
    response = requests.post(
        RUNPOD_ENDPOINT,
        json={"query": query},
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"HTTP Error: {response.status_code}")
        print(response.text)
        return

    data = response.json()
    if "errors" in data:
        print("GraphQL Errors:")
        print(json.dumps(data["errors"], indent=2))
        return

    input_fields = data.get("data", {}).get("__type", {}).get("inputFields", [])
    print("\nFields for CreateClusterInput:")
    print("-" * 30)
    for field in input_fields:
        f_name = field["name"]
        f_type = field["type"]["name"] or (field["type"]["ofType"]["name"] if field["type"]["ofType"] else "Unknown")
        print(f" - {f_name}: {f_type}")
    print("-" * 30)

if __name__ == "__main__":
    introspect()
