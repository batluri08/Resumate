/**
 * RestlessResume - Profile-based Resume Optimizer
 * Upload once, optimize for multiple jobs
 */

// ========================================
// UI UTILITY FUNCTIONS
// ========================================

/**
 * Show a toast notification
 */
function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    if (!toast) return;
    
    toast.textContent = message;
    toast.className = '';
    toast.classList.add(type);
    
    // Auto-hide after 4 seconds
    setTimeout(() => {
        toast.className = '';
    }, 4000);
}

/**
 * Set button loading state
 */
function setButtonLoading(button, isLoading, originalText = null) {
    if (!button) return;
    
    if (isLoading) {
        if (!originalText) {
            button.dataset.originalText = button.textContent;
        }
        button.classList.add('loading');
        button.disabled = true;
    } else {
        button.classList.remove('loading');
        button.disabled = false;
        if (button.dataset.originalText) {
            button.textContent = button.dataset.originalText;
            delete button.dataset.originalText;
        }
    }
}

/**
 * Show full-page loading overlay
 */
function showLoading(message = 'Processing...') {
    const loadingOverlay = document.getElementById('loading-overlay');
    if (loadingOverlay) {
        const loadingText = loadingOverlay.querySelector('.loading-text');
        if (loadingText) {
            loadingText.textContent = message;
        }
        loadingOverlay.classList.add('show');
    }
}

/**
 * Hide full-page loading overlay
 */
function hideLoading() {
    const loadingOverlay = document.getElementById('loading-overlay');
    if (loadingOverlay) {
        loadingOverlay.classList.remove('show');
    }
}

/**
 * Add error styling to form input
 */
function addFormError(input, errorMessage) {
    if (!input) return;
    input.classList.add('form-error');
    
    const errorEl = input.parentElement?.querySelector('.form-error-message');
    if (errorEl) {
        errorEl.textContent = errorMessage;
    }
}

/**
 * Remove error styling from form input
 */
function removeFormError(input) {
    if (!input) return;
    input.classList.remove('form-error');
    
    const errorEl = input.parentElement?.querySelector('.form-error-message');
    if (errorEl) {
        errorEl.textContent = '';
    }
}

/**
 * Toggle mobile sidebar
 */
function toggleSidebar() {
    const sidebar = document.querySelector('.sidebar');
    const mainContainer = document.querySelector('.main-container');
    if (sidebar) {
        sidebar.classList.toggle('open');
    }
    if (mainContainer) {
        mainContainer.classList.toggle('sidebar-open');
    }
}

/**
 * Close mobile sidebar when link is clicked
 */
function closeSidebar() {
    const sidebar = document.querySelector('.sidebar');
    const mainContainer = document.querySelector('.main-container');
    if (sidebar) {
        sidebar.classList.remove('open');
    }
    if (mainContainer) {
        mainContainer.classList.remove('sidebar-open');
    }
}

// ========================================
// STATE MANAGEMENT
// ========================================
const state = {
    sessionId: null,
    resumeId: null,
    fileName: null,
    fileExt: null,
    isUploaded: false,
    isOptimized: false,
    previewImage: null,
    resumes: [] // All user's resumes
};

// DOM Elements - with null safety
let fileInput, changeResumeBtn, jobDescription, optimizeBtn, analyzeBtn, vectorSearchBtn;
let keywordPanel, results, suggestionsList, originalPreview, optimizedPreview;
let downloadBtn, newJobBtn, loadingOverlay, toast;
let sidebarUploadBtn, noResumeState, resumeList, addResumeBtn;

function initDOMElements() {
    fileInput = document.getElementById('resume-file');
    changeResumeBtn = document.getElementById('change-resume-btn');
    jobDescription = document.getElementById('job-description');
    optimizeBtn = document.getElementById('optimize-btn');
    analyzeBtn = document.getElementById('analyze-btn');
    vectorSearchBtn = document.getElementById('vector-search-btn');
    keywordPanel = document.getElementById('keyword-panel');
    results = document.getElementById('results');
    suggestionsList = document.getElementById('suggestions-list');
    originalPreview = document.getElementById('original-preview');
    optimizedPreview = document.getElementById('optimized-preview');
    downloadBtn = document.getElementById('download-btn');
    newJobBtn = document.getElementById('new-job-btn');
    loadingOverlay = document.getElementById('loading-overlay');
    toast = document.getElementById('toast');
    
    // Sidebar elements
    sidebarUploadBtn = document.getElementById('sidebar-upload-btn');
    noResumeState = document.getElementById('no-resume-state');
    resumeList = document.getElementById('resume-list');
    addResumeBtn = document.getElementById('add-resume-btn');
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Setup logout handler to clear localStorage
    setupLogoutHandler();
    
    initDOMElements();
    setupSidebarNavigation();
    loadAllResumes();
    setupSidebarUpload();
    setupOptimizeButton();
    setupAnalyzeButton();
    setupDownloadButton();
    setupNewJobButton();
    setupChangeResumeButton();
    setupJobDescriptionListener();
    setupProfilePictureUpload();
    setupVectorSearchButton();
// Setup vector search button
function setupVectorSearchButton() {
    if (!vectorSearchBtn || !jobDescription) return;
    vectorSearchBtn.addEventListener('click', handleVectorSearch);
}

// Handle vector search for best-matching resumes
async function handleVectorSearch() {
    if (!jobDescription || !jobDescription.value.trim()) {
        showToast('Please enter a job description', 'error');
        return;
    }
    vectorSearchBtn.disabled = true;
    vectorSearchBtn.textContent = 'Searching...';
    try {
        const response = await fetch('/resume/api/resumes/vector-search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ job_description: jobDescription.value.trim() })
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Vector search failed');
        displayVectorSearchResults(data.matches);
        showToast('Vector search complete!', 'success');
    } catch (error) {
        console.error('Vector search error:', error);
        showToast('Error: ' + error.message, 'error');
    } finally {
        vectorSearchBtn.disabled = false;
        vectorSearchBtn.textContent = 'Find Best Resume';
    }
}

// Display vector search results
function displayVectorSearchResults(matches) {
    let resultsPanel = document.getElementById('vector-search-results');
    if (!resultsPanel) {
        resultsPanel = document.createElement('div');
        resultsPanel.id = 'vector-search-results';
        jobDescription.parentNode.insertBefore(resultsPanel, jobDescription.nextSibling);
    }
    if (!matches || matches.length === 0) {
        resultsPanel.innerHTML = '<div class="no-matches">No similar resumes found.</div>';
        return;
    }
    resultsPanel.innerHTML = '<h4>Best Matching Resumes:</h4>' + matches.map(m =>
        `<div class="vector-match">
            <b>${m.name}</b> (${m.file_name}) <span class="score">Score: ${m.score !== null ? m.score.toFixed(3) : 'N/A'}</span>
        </div>`
    ).join('');
}
});

/**
 * Setup logout handler to clear localStorage and prevent profile picture sharing
 * This prevents different users from seeing each other's profile pictures when logged in on the same browser
 */
function setupLogoutHandler() {
    const logoutForms = document.querySelectorAll('form[action="/auth/logout"]');
    logoutForms.forEach(form => {
        form.addEventListener('submit', (e) => {
            // Clear all user-specific localStorage before logout
            localStorage.removeItem('profilePicture');
            localStorage.removeItem('userProfile');
            localStorage.removeItem('resumeProfile');
            localStorage.removeItem('resumateProfile');
            // Allow form submission to proceed
        });
    });
}

// Setup profile picture upload in sidebar
function setupProfilePictureUpload() {
    const avatarContainer = document.getElementById('profile-avatar-container');
    const profilePictureInput = document.getElementById('profile-picture-input');
    const avatarInitial = document.getElementById('avatar-initial');
    
    if (!avatarContainer || !profilePictureInput) return;
    
    // Load saved profile picture
    const savedPicture = localStorage.getItem('profilePicture');
    if (savedPicture && avatarInitial) {
        avatarInitial.style.display = 'none';
        const img = document.createElement('img');
        img.src = savedPicture;
        img.alt = 'Profile';
        img.style.cssText = 'width: 100%; height: 100%; object-fit: cover; border-radius: 50%;';
        avatarContainer.insertBefore(img, avatarInitial);
    }
    
    avatarContainer.addEventListener('click', () => {
        profilePictureInput.click();
    });
    
    profilePictureInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            const file = e.target.files[0];
            
            if (!file.type.startsWith('image/')) {
                showToast('Please select an image file.', 'error');
                return;
            }
            
            if (file.size > 2 * 1024 * 1024) {
                showToast('Image size must be less than 2MB.', 'error');
                return;
            }
            
            const reader = new FileReader();
            reader.onload = (event) => {
                const imageData = event.target.result;
                
                // Remove initial and add image
                if (avatarInitial) avatarInitial.style.display = 'none';
                
                // Remove existing image if any
                const existingImg = avatarContainer.querySelector('img');
                if (existingImg) existingImg.remove();
                
                const img = document.createElement('img');
                img.src = imageData;
                img.alt = 'Profile';
                img.style.cssText = 'width: 100%; height: 100%; object-fit: cover; border-radius: 50%;';
                avatarContainer.insertBefore(img, profilePictureInput);
                
                localStorage.setItem('profilePicture', imageData);
                showToast('Profile picture updated!');
            };
            reader.readAsDataURL(file);
        }
    });
}

// Update process step indicator
function updateProcessStep(step) {
    const steps = document.querySelectorAll('.process-steps .step');
    steps.forEach((s, index) => {
        s.classList.remove('active', 'completed');
        if (index < step - 1) {
            s.classList.add('completed');
        } else if (index === step - 1) {
            s.classList.add('active');
        }
    });
}

// Setup sidebar navigation
function setupSidebarNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        // Remove active class from all items
        const allItems = document.querySelectorAll('.nav-item');
        
        // Set active based on current page (optional - or let the nav links naturally navigate)
        // The nav links will navigate to their href values automatically
    });
}

// Load all resumes and display in sidebar
async function loadAllResumes() {
    try {
        const response = await fetch('/resume/api/resumes');
        const resumes = await response.json();
        
        state.resumes = resumes;
        
        if (resumes.length > 0) {
            renderResumeList(resumes);
            
            // Auto-select the default resume
            const defaultResume = resumes.find(r => r.is_default);
            if (defaultResume) {
                await selectResume(defaultResume.id);
            } else {
                await selectResume(resumes[0].id);
            }
        } else {
            showNoResumeState();
            updateProcessStep(1);
        }
    } catch (error) {
        console.error('Failed to load resumes:', error);
        showNoResumeState();
        updateProcessStep(1);
    }
}

// Render resume list in sidebar
function renderResumeList(resumes) {
    if (!resumeList) return;
    
    if (resumes.length === 0) {
        resumeList.innerHTML = '';
        showNoResumeState();
        return;
    }
    
    // Hide "no resume" state
    if (noResumeState) noResumeState.classList.add('hidden');
    
    resumeList.innerHTML = resumes.map(resume => `
        <div class="resume-item ${resume.id === state.resumeId ? 'selected' : ''}" data-id="${resume.id}">
            <div class="resume-icon">${resume.file_ext.replace('.', '').toUpperCase()}</div>
            <div class="resume-info">
                <div class="resume-name" title="${resume.name}">${resume.name}</div>
                <div class="resume-meta">
                    ${resume.is_default ? '<span class="default-badge">Default</span>' : ''}
                </div>
            </div>
            <div class="resume-actions">
                <button class="btn-action" onclick="event.stopPropagation(); renameResume(${resume.id}, '${resume.name.replace(/'/g, "\\'")}')" title="Rename">R</button>
                <button class="btn-action delete" onclick="event.stopPropagation(); deleteResume(${resume.id})" title="Delete">X</button>
            </div>
        </div>
    `).join('');
    
    // Add click handlers for selection
    resumeList.querySelectorAll('.resume-item').forEach(item => {
        item.addEventListener('click', () => {
            const id = parseInt(item.dataset.id);
            selectResume(id);
        });
    });
}

// Select a resume
async function selectResume(resumeId) {
    try {
        const response = await fetch(`/resume/api/resumes/${resumeId}/select`, {
            method: 'POST'
        });
        const data = await response.json();
        
        if (data.success) {
            state.sessionId = data.session_id;
            state.resumeId = resumeId;
            state.fileName = data.resume.file_name;
            state.fileExt = data.resume.file_ext;
            state.previewImage = data.resume.preview_image;
            state.isUploaded = true;
            
            // Update UI to show selected resume
            document.querySelectorAll('.resume-item').forEach(item => {
                item.classList.remove('selected');
                if (parseInt(item.dataset.id) === resumeId) {
                    item.classList.add('selected');
                }
            });
            
            updateOptimizeButton();
            updateProcessStep(2);
        }
    } catch (error) {
        console.error('Failed to select resume:', error);
        showToast('Failed to select resume', 'error');
    }
}

// Delete a resume
async function deleteResume(resumeId) {
    if (!confirm('Are you sure you want to delete this resume?')) return;
    
    try {
        const response = await fetch(`/resume/api/resumes/${resumeId}`, {
            method: 'DELETE'
        });
        const data = await response.json();
        
        if (data.success) {
            showToast('Resume deleted');
            loadAllResumes(); // Reload the list
        }
    } catch (error) {
        console.error('Failed to delete resume:', error);
        showToast('Failed to delete resume', 'error');
    }
}

// Rename a resume
async function renameResume(resumeId, currentName) {
    const newName = prompt('Enter new name for this resume:', currentName);
    if (!newName || newName === currentName) return;
    
    try {
        const response = await fetch(`/resume/api/resumes/${resumeId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: newName })
        });
        const data = await response.json();
        
        if (data.success) {
            showToast('Resume renamed');
            loadAllResumes(); // Reload the list
        }
    } catch (error) {
        console.error('Failed to rename resume:', error);
        showToast('Failed to rename resume', 'error');
    }
}

// Show no resume state in sidebar
function showNoResumeState() {
    if (!noResumeState) return;
    
    noResumeState.classList.remove('hidden');
    if (resumeList) resumeList.innerHTML = '';
    state.isUploaded = false;
}

// Setup file selection
function setupSidebarUpload() {
    // Setup sidebar upload button
    if (sidebarUploadBtn && fileInput) {
        sidebarUploadBtn.addEventListener('click', () => {
            promptAndUpload();
        });
    }
    
    // Setup add resume button
    if (addResumeBtn && fileInput) {
        addResumeBtn.addEventListener('click', () => {
            promptAndUpload();
        });
    }
    
    // Setup file input change
    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                const resumeName = fileInput.dataset.resumeName || null;
                handleFileSelect(e.target.files[0], resumeName);
                fileInput.dataset.resumeName = ''; // Clear after use
            }
        });
    }
}

// Prompt for name and trigger file upload
function promptAndUpload() {
    const name = prompt('Enter a name for this resume (e.g., "Software Engineer Resume"):');
    if (name === null) return; // User cancelled
    
    if (fileInput) {
        fileInput.dataset.resumeName = name.trim() || '';
        fileInput.click();
    }
}

// Save profile to localStorage
function saveProfile() {
    const profile = {
        sessionId: state.sessionId,
        fileName: state.fileName,
        fileExt: state.fileExt,
        previewImage: state.previewImage
    };
    localStorage.setItem('resumeProfile', JSON.stringify(profile));
}

// Show profile uploaded state (legacy - now handled by sidebar)
function showProfileState() {
    // Updated to use sidebar resume display
    if (state.fileName) {
        showResumeInSidebar(state.fileName, new Date().toISOString());
    }
    updateOptimizeButton();
}

// Show no profile state (legacy - now handled by sidebar)
function showNoProfileState() {
    showNoResumeState();
    updateOptimizeButton();
}

// Setup change resume button
function setupChangeResumeButton() {
    if (changeResumeBtn) {
        changeResumeBtn.addEventListener('click', () => {
            fileInput.click();
        });
    }
}

// Handle file selection
async function handleFileSelect(file, resumeName = null) {
    const validTypes = ['.pdf', '.docx'];
    const fileExt = '.' + file.name.split('.').pop().toLowerCase();
    
    if (!validTypes.includes(fileExt)) {
        alert('Please upload a PDF or DOCX file.');
        return;
    }
    
    // Show loading
    showLoading('Uploading and parsing your resume...');
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        if (resumeName) {
            formData.append('resume_name', resumeName);
        }
        
        const response = await fetch('/resume/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        hideLoading();
        
        if (!data.success) {
            alert('Error uploading resume: ' + data.detail);
            return;
        }
        
        // Update state
        state.sessionId = data.session_id;
        state.resumeId = data.resume_id;
        state.fileName = data.filename;
        state.fileExt = data.file_ext;
        state.previewImage = data.preview_image;
        state.isUploaded = true;
        
        // Reload resume list to show the new resume
        await loadAllResumes();
        
        // Update buttons
        updateOptimizeButton();
        
        // Update process step to 2 (paste job description)
        updateProcessStep(2);
        
        showToast('Resume uploaded successfully!');
        
    } catch (error) {
        hideLoading();
        console.error('Upload failed:', error);
        alert('Failed to upload resume. Please try again.');
    }
}

// Reset profile
function resetProfile() {
    localStorage.removeItem('resumeProfile');
    
    state.sessionId = null;
    state.fileName = null;
    state.fileExt = null;
    state.isUploaded = false;
    state.isOptimized = false;
    state.previewImage = null;

    if (fileInput) fileInput.value = '';
    if (results) results.classList.add('hidden');
    if (jobDescription) jobDescription.value = '';
    if (keywordPanel) keywordPanel.classList.add('hidden');
    
    showNoProfileState();
}

// Setup job description listener
function setupJobDescriptionListener() {
    if (!jobDescription) return;
    
    jobDescription.addEventListener('input', () => {
        updateOptimizeButton();
        // Hide keyword panel when job description changes
        if (keywordPanel) keywordPanel.classList.add('hidden');
    });
}

// Update optimize button state
function updateOptimizeButton() {
    if (!optimizeBtn || !jobDescription) return;
    
    const hasResume = state.isUploaded;
    const hasJobDesc = jobDescription.value.trim().length > 50;
    
    optimizeBtn.disabled = !(hasResume && hasJobDesc);
    if (analyzeBtn) {
        analyzeBtn.disabled = !(hasResume && hasJobDesc);
    }
}

// Setup analyze button
function setupAnalyzeButton() {
    if (!analyzeBtn) return;
    
    analyzeBtn.addEventListener('click', handleAnalyze);
}

// Handle keyword analysis
async function handleAnalyze() {
    if (!state.sessionId) {
        showToast('Please select a resume first', 'error');
        return;
    }
    
    if (!jobDescription || !jobDescription.value.trim()) {
        showToast('Please enter a job description', 'error');
        return;
    }
    
    analyzeBtn.disabled = true;
    analyzeBtn.textContent = 'Analyzing...';
    
    try {
        const formData = new FormData();
        formData.append('session_id', state.sessionId);
        formData.append('job_description', jobDescription.value.trim());
        
        const response = await fetch('/resume/analyze-keywords', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'Analysis failed');
        }
        
        // Display results
        displayKeywordAnalysis(data);
        showToast('Keyword analysis complete!', 'success');
        
    } catch (error) {
        console.error('Analysis error:', error);
        showToast('Error analyzing keywords: ' + error.message, 'error');
    } finally {
        analyzeBtn.disabled = false;
        analyzeBtn.textContent = 'Analyze Keywords';
    }
}

// Display keyword analysis results
function displayKeywordAnalysis(data) {
    if (!keywordPanel) {
        console.error('Keyword panel not found');
        return;
    }
    
    // Show panel
    keywordPanel.classList.remove('hidden');
    
    // Update match score badge
    const scoreBadge = document.getElementById('match-score-badge');
    if (scoreBadge) {
        scoreBadge.textContent = `${data.match_score}% Match`;
        scoreBadge.className = 'match-score-badge';
        if (data.match_score >= 70) {
            scoreBadge.classList.add('high');
        } else if (data.match_score >= 50) {
            scoreBadge.classList.add('medium');
        } else {
            scoreBadge.classList.add('low');
        }
    }
    
    // Update keywords matched stat
    const keywordsMatchedEl = document.getElementById('keywords-matched');
    if (keywordsMatchedEl) {
        keywordsMatchedEl.textContent = data.found_keywords.length;
    }
    
    // Update found keywords
    const foundContainer = document.getElementById('found-keywords');
    const foundCount = document.getElementById('found-count');
    if (foundCount) foundCount.textContent = data.found_keywords.length;
    if (foundContainer) {
        foundContainer.innerHTML = data.found_keywords.map(kw => 
            `<span class="keyword-tag found">${kw}</span>`
        ).join('') || '<span class="keyword-tag">None found</span>';
    }
    
    // Update missing keywords
    const missingContainer = document.getElementById('missing-keywords');
    const missingCount = document.getElementById('missing-count');
    if (missingCount) missingCount.textContent = data.missing_keywords.length;
    if (missingContainer) {
        missingContainer.innerHTML = data.missing_keywords.map(kw => 
            `<span class="keyword-tag missing">${kw}</span>`
        ).join('') || '<span class="keyword-tag found">All keywords found!</span>';
    }
    
    console.log('Keyword analysis displayed:', data);
}

// Setup optimize button
function setupOptimizeButton() {
    if (!optimizeBtn) return;
    optimizeBtn.addEventListener('click', handleOptimize);
}

// Handle optimization
async function handleOptimize() {
    if (!state.sessionId || !jobDescription || !jobDescription.value.trim()) {
        alert('Please upload a resume and enter a job description.');
        return;
    }

    showLoading('Analyzing your resume with AI...');
    
    // Update process step to 3 (optimizing)
    updateProcessStep(3);
    
    const btnText = optimizeBtn ? optimizeBtn.querySelector('.btn-text') : null;
    const btnLoading = optimizeBtn ? optimizeBtn.querySelector('.btn-loading') : null;
    if (btnText) btnText.classList.add('hidden');
    if (btnLoading) btnLoading.classList.remove('hidden');
    if (optimizeBtn) optimizeBtn.disabled = true;

    try {
        const formData = new FormData();
        formData.append('session_id', state.sessionId);
        formData.append('job_description', jobDescription.value.trim());

        // Add profile preferences if available
        const userProfile = localStorage.getItem('userProfile');
        if (userProfile) {
            const profile = JSON.parse(userProfile);
            if (profile.targetRole) formData.append('target_role', profile.targetRole);
            if (profile.mustHaveSkills) formData.append('must_have_skills', profile.mustHaveSkills);
            if (profile.secondarySkills) formData.append('secondary_skills', profile.secondarySkills);
            if (profile.prefConservative) formData.append('pref_conservative', profile.prefConservative);
        }

        const response = await fetch('/resume/optimize', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Optimization failed');
        }

        // Update state
        state.isOptimized = true;

        // Show results with visual comparison
        displayResults(data);
        
        // Update process step to 4 (download ready)
        updateProcessStep(4);
        
        // Update total optimized stat
        const totalEl = document.getElementById('total-optimized');
        if (totalEl) {
            totalEl.textContent = parseInt(totalEl.textContent || 0) + 1;
        }
        
    } catch (error) {
        console.error('Optimization error:', error);
        alert('Error optimizing resume: ' + error.message);
    } finally {
        hideLoading();
        
        const btnText = optimizeBtn ? optimizeBtn.querySelector('.btn-text') : null;
        const btnLoading = optimizeBtn ? optimizeBtn.querySelector('.btn-loading') : null;
        if (btnText) btnText.classList.remove('hidden');
        if (btnLoading) btnLoading.classList.add('hidden');
        updateOptimizeButton();
    }
}

// Display optimization results with visual comparison
function displayResults(data) {
    if (!results) return;
    
    results.classList.remove('hidden');

    // Display suggestions
    if (suggestionsList) {
        suggestionsList.innerHTML = '';
        if (data.suggestions && data.suggestions.length > 0) {
            data.suggestions.forEach(suggestion => {
                const li = document.createElement('li');
                li.textContent = suggestion;
                suggestionsList.appendChild(li);
            });
        }
    }

    // Display visual preview images
    if (originalPreview) {
        if (data.original_preview) {
            originalPreview.innerHTML = `<img src="data:image/png;base64,${data.original_preview}" alt="Original Resume">`;
        } else if (state.previewImage) {
            originalPreview.innerHTML = `<img src="data:image/png;base64,${state.previewImage}" alt="Original Resume">`;
        }
    }
    
    if (optimizedPreview && data.optimized_preview) {
        optimizedPreview.innerHTML = `<img src="data:image/png;base64,${data.optimized_preview}" alt="Optimized Resume">`;
    }

    // Scroll to results
    results.scrollIntoView({ behavior: 'smooth' });
}

// Setup new job button - clears job description but keeps resume
function setupNewJobButton() {
    if (!newJobBtn) return;
    
    newJobBtn.addEventListener('click', () => {
        if (jobDescription) jobDescription.value = '';
        if (results) results.classList.add('hidden');
        state.isOptimized = false;
        updateOptimizeButton();
        
        // Scroll to job description
        const jobSection = document.getElementById('job-section');
        if (jobSection) {
            jobSection.scrollIntoView({ behavior: 'smooth' });
            if (jobDescription) jobDescription.focus();
        }
        
        showToast('Ready for a new job description!');
    });
}

// Setup download button
function setupDownloadButton() {
    if (!downloadBtn) return;
    downloadBtn.addEventListener('click', handleDownload);
}

// Handle download
async function handleDownload() {
    if (!state.sessionId || !state.isOptimized) {
        alert('Please optimize your resume first.');
        return;
    }

    try {
        const response = await fetch(`/resume/download/${state.sessionId}`);
        
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.detail || 'Download failed');
        }

        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = state.fileName ? state.fileName.replace(/\.(pdf|docx)$/i, '_optimized.docx') : 'optimized_resume.docx';
        if (contentDisposition) {
            const match = contentDisposition.match(/filename\*?=(?:UTF-8'')?["']?([^"';\n]+)["']?/i);
            if (match) {
                filename = decodeURIComponent(match[1]);
            }
        }

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();

        showToast('Download started!');

    } catch (error) {
        console.error('Download error:', error);
        alert('Error downloading file: ' + error.message);
    }
}

// Show toast notification
// Old implementations (kept for reference but now using new utility functions above)
// These are deprecated - use the utility functions at the top of the file instead
