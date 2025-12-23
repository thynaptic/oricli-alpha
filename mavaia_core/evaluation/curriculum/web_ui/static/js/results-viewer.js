// Results Viewer JavaScript

async function loadResults(resultId) {
    try {
        const response = await fetch(`/api/tests/${resultId}/results`);
        const result = await response.json();
        
        displayResultDetails(result);
    } catch (error) {
        console.error('Error loading results:', error);
    }
}

function displayResultDetails(result) {
    const viewer = document.getElementById('results-viewer');
    if (!viewer) return;
    
    viewer.innerHTML = `
        <h3>Test Result Details</h3>
        <div class="result-summary">
            <p>Status: ${result.pass_fail_status}</p>
            <p>Score: ${result.score_breakdown.final_score.toFixed(2)}</p>
            <p>Execution Time: ${result.execution_time.toFixed(2)}s</p>
        </div>
        <div class="score-breakdown">
            <h4>Score Breakdown</h4>
            <p>Accuracy: ${result.score_breakdown.accuracy.toFixed(2)}</p>
            <p>Reasoning Depth: ${result.score_breakdown.reasoning_depth.toFixed(2)}</p>
            <p>Verbosity: ${result.score_breakdown.verbosity.toFixed(2)}</p>
            <p>Structure: ${result.score_breakdown.structure.toFixed(2)}</p>
        </div>
    `;
}

