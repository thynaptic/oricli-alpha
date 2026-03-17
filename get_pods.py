import os
import json
import requests

api_key = os.environ.get("OricliAlpha_Key")
headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

query = """
query MyPods {
  myself {
    pods {
      id
      name
      desiredStatus
      runtime {
        uptimeInSeconds
        ports {
          ip
          isIpPublic
          privatePort
          publicPort
        }
      }
    }
  }
}
"""

response = requests.post("https://api.runpod.io/graphql", json={"query": query}, headers=headers)
print(json.dumps(response.json(), indent=2))
