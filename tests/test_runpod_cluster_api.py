#!/usr/bin/env python3
"""
Test RunPod Cluster API integration.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.runpod_bridge import RunPodBridge

def test_get_clusters():
    """Verify get_clusters query."""
    bridge = RunPodBridge(api_key="mock-key")
    
    mock_response = {
        "data": {
            "clusters": [
                {
                    "id": "cluster-1",
                    "name": "test-cluster",
                    "status": "RUNNING",
                    "nodeCount": 2,
                    "pods": [{"id": "pod-1"}, {"id": "pod-2"}]
                }
            ]
        }
    }
    
    with patch.object(bridge, "_query", return_value=mock_response):
        clusters = bridge.get_clusters()
        assert len(clusters) == 1
        assert clusters[0]["id"] == "cluster-1"
        assert clusters[0]["nodeCount"] == 2
        print("✓ get_clusters verified")

def test_create_cluster():
    """Verify create_cluster mutation."""
    bridge = RunPodBridge(api_key="mock-key")
    
    mock_response = {
        "data": {
            "createCluster": {
                "id": "new-cluster-id",
                "name": "mavaia-cluster",
                "podCount": 2,
                "pods": [{"id": "p1"}, {"id": "p2"}]
            }
        }
    }

    
    with patch.object(bridge, "_query", return_value=mock_response) as mock_query:
        cluster = bridge.create_cluster(
            name="mavaia-cluster",
            gpu_type_id="NVIDIA RTX A6000",
            pod_count=2,
            bid_per_gpu=0.50,
            image="runpod/pytorch"
        )
        
        assert cluster["id"] == "new-cluster-id"
        assert cluster["podCount"] == 2
        
        # Verify input structure
        args, kwargs = mock_query.call_args
        sent_input = kwargs["variables"]["input"]
        assert sent_input["clusterName"] == "mavaia-cluster"
        assert sent_input["podCount"] == 2
        assert sent_input["type"] == "SLURM"
        assert sent_input["bidPerGpu"] == 0.50
        print("✓ create_cluster verified")

def test_delete_cluster():
    """Verify delete_cluster mutation."""
    bridge = RunPodBridge(api_key="mock-key")
    
    mock_response = {"data": {"deleteCluster": True}}
    
    with patch.object(bridge, "_query", return_value=mock_response) as mock_query:
        res = bridge.delete_cluster("cluster-to-delete")
        
        assert res is True
        
        # Verify input
        args, kwargs = mock_query.call_args
        assert kwargs["variables"]["input"]["clusterId"] == "cluster-to-delete"
        print("✓ delete_cluster verified")

if __name__ == "__main__":
    try:
        test_get_clusters()
        test_create_cluster()
        test_delete_cluster()
        print("\n✨ All Cluster API tests passed!")
    except Exception as e:
        print(f"✗ Tests failed: {e}")
        sys.exit(1)
