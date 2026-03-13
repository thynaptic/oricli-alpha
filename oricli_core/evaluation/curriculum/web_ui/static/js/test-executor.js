// Test Executor JavaScript

let currentTestId = null;
let websocket = null;

async function startTest(config) {
    try {
        const response = await fetch('/api/tests/execute', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(config),
        });
        
        const result = await response.json();
        currentTestId = result.test_id;
        
        // Connect WebSocket for updates
        connectWebSocket(currentTestId);
        
        // Poll for status
        pollTestStatus(currentTestId);
    } catch (error) {
        console.error('Error starting test:', error);
    }
}

function connectWebSocket(testId) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/ws/test/${testId}`;
    
    websocket = new WebSocket(wsUrl);
    
    websocket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        updateTestProgress(data);
    };
    
    websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
    };
}

async function pollTestStatus(testId) {
    const interval = setInterval(async () => {
        try {
            const response = await fetch(`/api/tests/${testId}/status`);
            const status = await response.json();
            
            if (status.status === 'completed') {
                clearInterval(interval);
                displayTestResult(status.result);
            }
        } catch (error) {
            console.error('Error polling status:', error);
        }
    }, 1000);
}

function updateTestProgress(data) {
    const executor = document.getElementById('test-executor');
    if (!executor) return;
    
    executor.innerHTML = `
        <div class="progress-bar">
            <div class="progress-fill" style="width: 50%">Running...</div>
        </div>
        <p>Status: ${data.status}</p>
    `;
}

function displayTestResult(result) {
    const executor = document.getElementById('test-executor');
    if (!executor) return;
    
    executor.innerHTML = `
        <h3>Test Completed</h3>
        <p>Status: ${result.pass_fail_status}</p>
        <p>Score: ${result.score_breakdown.final_score.toFixed(2)}</p>
    `;
}

