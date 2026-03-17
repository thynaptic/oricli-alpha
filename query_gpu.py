import os
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

res = requests.post("https://api.runpod.io/graphql", json={"query": query}, headers=headers).json()
pods = res.get("data", {}).get("myself", {}).get("pods", [])
for p in pods:
    if p["desiredStatus"] == "RUNNING":
        ports = p.get("runtime", {}).get("ports", [])
        ssh_port = next((pt for pt in ports if pt.get("privatePort") == 22), None)
        if ssh_port:
            print(f"Pod ID: {p['id']}")
            print(f"IP: {ssh_port.get('ip')}")
            print(f"Port: {ssh_port.get('publicPort')}")
