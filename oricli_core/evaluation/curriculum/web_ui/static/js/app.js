// Main App JavaScript

function showSection(sectionId) {
    // Hide all sections
    document.querySelectorAll('.section').forEach(section => {
        section.classList.remove('active');
    });
    
    // Show selected section
    const section = document.getElementById(sectionId);
    if (section) {
        section.classList.add('active');
    }
}

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    console.log('Oricli-Alpha Curriculum Testing Framework Web UI loaded');
});

