// Curriculum Selector JavaScript

let selectedConfig = {
    level: null,
    subject: null,
    skill_type: null,
    difficulty_style: null,
    constraints: {}
};

async function loadCurriculumOptions() {
    try {
        const [levels, subjects, skillTypes, difficulties] = await Promise.all([
            fetch('/api/curriculum/levels').then(r => r.json()),
            fetch('/api/curriculum/subjects').then(r => r.json()),
            fetch('/api/curriculum/skill-types').then(r => r.json()),
            fetch('/api/curriculum/difficulty-styles').then(r => r.json()),
        ]);
        
        populateSelect('level-select', levels);
        populateSelect('subject-select', subjects);
        populateSelect('skill-type-select', skillTypes);
        populateSelect('difficulty-select', difficulties);
    } catch (error) {
        console.error('Error loading options:', error);
    }
}

function populateSelect(selectId, options) {
    const select = document.getElementById(selectId);
    if (!select) return;
    
    select.innerHTML = '<option value="">Select...</option>';
    options.forEach(option => {
        const optionEl = document.createElement('option');
        optionEl.value = option;
        optionEl.textContent = option;
        select.appendChild(optionEl);
    });
}

function updateConfig() {
    selectedConfig.level = document.getElementById('level-select')?.value;
    selectedConfig.subject = document.getElementById('subject-select')?.value;
    selectedConfig.skill_type = document.getElementById('skill-type-select')?.value;
    selectedConfig.difficulty_style = document.getElementById('difficulty-select')?.value;
}

async function executeTest() {
    updateConfig();
    
    if (!selectedConfig.level || !selectedConfig.subject || 
        !selectedConfig.skill_type || !selectedConfig.difficulty_style) {
        alert('Please select all curriculum options');
        return;
    }
    
    try {
        const response = await fetch('/api/tests/execute', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(selectedConfig),
        });
        
        const result = await response.json();
        console.log('Test result:', result);
        
        // Show results section
        showSection('results');
        displayResults(result);
    } catch (error) {
        console.error('Error executing test:', error);
        alert('Error executing test: ' + error.message);
    }
}

function displayResults(result) {
    const viewer = document.getElementById('results-viewer');
    if (!viewer) return;
    
    viewer.innerHTML = `
        <h3>Test Result</h3>
        <p>Status: ${result.result.pass_fail_status}</p>
        <p>Score: ${result.result.score_breakdown.final_score.toFixed(2)}</p>
        <p>Execution Time: ${result.result.execution_time.toFixed(2)}s</p>
    `;
}

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
    loadCurriculumOptions();
});

