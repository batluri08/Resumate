/**
 * RestlessResume - Profile Page
 */

// Profile state
const profile = {
    sessionId: null,
    fileName: null,
    fileExt: null,
    previewImage: null,
    targetRole: '',
    experienceLevel: '',
    industries: '',
    mustHaveSkills: '',
    secondarySkills: '',
    prefConservative: true,
    prefKeywords: true,
    prefMetrics: false
};

// DOM Elements
const uploadArea = document.getElementById('upload-area');
const fileInput = document.getElementById('resume-file');
const uploadContainer = document.getElementById('upload-container');
const resumeUploaded = document.getElementById('resume-uploaded');
const resumeFilename = document.getElementById('resume-filename');
const resumePreviewMini = document.getElementById('resume-preview-mini');
const changeResumeBtn = document.getElementById('change-resume-btn');
const profileForm = document.getElementById('profile-form');
const saveProfileBtn = document.getElementById('save-profile-btn');
const clearProfileBtn = document.getElementById('clear-profile-btn');
const loadingOverlay = document.getElementById('loading-overlay');
const toast = document.getElementById('toast');

// Form fields
const targetRoleInput = document.getElementById('target-role');
const experienceLevelSelect = document.getElementById('experience-level');
const industriesInput = document.getElementById('industries');
const mustHaveSkillsInput = document.getElementById('must-have-skills');
const secondarySkillsInput = document.getElementById('secondary-skills');
const prefConservativeCheck = document.getElementById('pref-conservative');
const prefKeywordsCheck = document.getElementById('pref-keywords');
const prefMetricsCheck = document.getElementById('pref-metrics');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupLogoutHandler();
    loadProfile();
    setupUploadArea();
    setupFormHandlers();
    setupProfilePictureUpload();
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

// Setup profile picture upload
function setupProfilePictureUpload() {
    const avatarContainer = document.getElementById('profile-avatar-container');
    const profilePictureInput = document.getElementById('profile-picture-input');
    
    if (!avatarContainer || !profilePictureInput) return;
    
    avatarContainer.addEventListener('click', () => {
        profilePictureInput.click();
    });
    
    profilePictureInput.addEventListener('change', async (e) => {
        if (e.target.files.length > 0) {
            const file = e.target.files[0];
            
            // Validate file type
            if (!file.type.startsWith('image/')) {
                alert('Please select an image file.');
                return;
            }
            
            // Validate file size (max 2MB)
            if (file.size > 2 * 1024 * 1024) {
                alert('Image size must be less than 2MB.');
                return;
            }
            
            // Convert to base64 and display
            const reader = new FileReader();
            reader.onload = async (event) => {
                const imageData = event.target.result;
                
                // Update avatar display immediately
                updateAvatarDisplay(imageData);
                
                // Save to database via API
                try {
                    const response = await fetch('/resume/api/profile/picture', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            picture: imageData
                        })
                    });
                    
                    if (!response.ok) {
                        throw new Error(`API error: ${response.status}`);
                    }
                    
                    const result = await response.json();
                    if (result.success) {
                        // Also cache in localStorage for faster local access
                        localStorage.setItem('profilePicture', imageData);
                        showToast('Profile picture updated successfully!');
                    }
                } catch (error) {
                    console.error('Error saving profile picture:', error);
                    // Fallback to localStorage if API fails
                    localStorage.setItem('profilePicture', imageData);
                    showToast('Profile picture saved locally (sync pending)');
                }
            };
            reader.readAsDataURL(file);
        }
    });
    
    // Load saved profile picture on init from database
    loadProfilePictureFromDatabase();
}

// Helper function to update avatar display
function updateAvatarDisplay(imageData) {
    const avatarContainer = document.getElementById('profile-avatar-container');
    if (!avatarContainer) return;
    
    avatarContainer.innerHTML = `
        <img src="${imageData}" alt="Profile" class="avatar-image" style="width: 100%; height: 100%; object-fit: cover; border-radius: 50%;">
        <input type="file" id="profile-picture-input" accept="image/*" hidden>
    `;
    
    // Re-attach event listener to new input
    const newInput = document.getElementById('profile-picture-input');
    if (newInput) {
        newInput.addEventListener('change', arguments.callee);
    }
}

// Load profile picture from database
async function loadProfilePictureFromDatabase() {
    try {
        const response = await fetch('/resume/api/profile/picture', {
            method: 'GET'
        });
        
        if (response.ok) {
            const result = await response.json();
            if (result.success && result.picture) {
                updateAvatarDisplay(result.picture);
                // Cache in localStorage
                localStorage.setItem('profilePicture', result.picture);
                return;
            }
        }
    } catch (error) {
        console.error('Error loading profile picture from database:', error);
    }
    
    // Fallback to localStorage if database fetch fails
    const savedPicture = localStorage.getItem('profilePicture');
    if (savedPicture) {
        updateAvatarDisplay(savedPicture);
        return;
    }
    
    // If no picture exists, setup event listeners for new upload
    const profilePictureInput = document.getElementById('profile-picture-input');
    if (profilePictureInput) {
        profilePictureInput.addEventListener('change', function(e) {
            if (e.target.files.length > 0) {
                const file = e.target.files[0];
                if (!file.type.startsWith('image/')) {
                    alert('Please select an image file.');
                    return;
                }
                if (file.size > 2 * 1024 * 1024) {
                    alert('Image size must be less than 2MB.');
                    return;
                }
                const reader = new FileReader();
                reader.onload = (event) => {
                    const imageData = event.target.result;
                    updateAvatarDisplay(imageData);
                        localStorage.setItem('profilePicture', imageData);
                        showToast('Profile picture updated!');
                    };
                    reader.readAsDataURL(file);
                }
            });
        }
    }
}

// Load profile from localStorage
function loadProfile() {
    const saved = localStorage.getItem('userProfile');
    if (saved) {
        const data = JSON.parse(saved);
        Object.assign(profile, data);
        
        // Populate form fields
        targetRoleInput.value = profile.targetRole || '';
        experienceLevelSelect.value = profile.experienceLevel || '';
        industriesInput.value = profile.industries || '';
        mustHaveSkillsInput.value = profile.mustHaveSkills || '';
        secondarySkillsInput.value = profile.secondarySkills || '';
        prefConservativeCheck.checked = profile.prefConservative !== false;
        prefKeywordsCheck.checked = profile.prefKeywords !== false;
        prefMetricsCheck.checked = profile.prefMetrics === true;
        
        // Show resume if uploaded
        if (profile.sessionId && profile.fileName) {
            showResumeUploaded();
        }
    }
}

// Save profile to localStorage
function saveProfile() {
    // Gather form data
    profile.targetRole = targetRoleInput.value.trim();
    profile.experienceLevel = experienceLevelSelect.value;
    profile.industries = industriesInput.value.trim();
    profile.mustHaveSkills = mustHaveSkillsInput.value.trim();
    profile.secondarySkills = secondarySkillsInput.value.trim();
    profile.prefConservative = prefConservativeCheck.checked;
    profile.prefKeywords = prefKeywordsCheck.checked;
    profile.prefMetrics = prefMetricsCheck.checked;
    
    localStorage.setItem('userProfile', JSON.stringify(profile));
    
    // Also save to the simpler resumeProfile for backwards compatibility
    if (profile.sessionId) {
        localStorage.setItem('resumeProfile', JSON.stringify({
            sessionId: profile.sessionId,
            fileName: profile.fileName,
            fileExt: profile.fileExt,
            previewImage: profile.previewImage
        }));
    }
    
    showToast('Profile saved!');
}

// Clear profile
function clearProfile() {
    if (!confirm('Are you sure you want to clear your profile? This will remove your uploaded resume and all settings.')) {
        return;
    }
    
    localStorage.removeItem('userProfile');
    localStorage.removeItem('resumeProfile');
    
    // Reset state
    Object.keys(profile).forEach(key => {
        if (typeof profile[key] === 'boolean') {
            profile[key] = key === 'prefConservative' || key === 'prefKeywords';
        } else {
            profile[key] = null;
        }
    });
    
    // Reset form
    profileForm.reset();
    prefConservativeCheck.checked = true;
    prefKeywordsCheck.checked = true;
    
    // Reset upload UI
    showUploadArea();
    
    showToast('Profile cleared');
}

// Setup upload area
function setupUploadArea() {
    uploadArea.addEventListener('click', () => fileInput.click());
    
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileUpload(e.target.files[0]);
        }
    });
    
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });
    
    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });
    
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            handleFileUpload(e.dataTransfer.files[0]);
        }
    });
    
    changeResumeBtn.addEventListener('click', () => fileInput.click());
}

// Handle file upload
async function handleFileUpload(file) {
    const validTypes = ['.pdf', '.docx'];
    const fileExt = '.' + file.name.split('.').pop().toLowerCase();
    
    if (!validTypes.includes(fileExt)) {
        alert('Please upload a PDF or DOCX file.');
        return;
    }
    
    showLoading('Uploading resume...');
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch('/resume/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'Upload failed');
        }
        
        // Update profile
        profile.sessionId = data.session_id;
        profile.fileName = data.filename;
        profile.fileExt = fileExt;
        profile.previewImage = data.preview_image;
        
        showResumeUploaded();
        showToast('Resume uploaded!');
        
    } catch (error) {
        console.error('Upload error:', error);
        alert('Error uploading: ' + error.message);
    } finally {
        hideLoading();
    }
}

// Show upload area
function showUploadArea() {
    uploadArea.classList.remove('hidden');
    resumeUploaded.classList.add('hidden');
    resumePreviewMini.innerHTML = '';
}

// Show resume uploaded state
function showResumeUploaded() {
    uploadArea.classList.add('hidden');
    resumeUploaded.classList.remove('hidden');
    resumeFilename.textContent = profile.fileName;
    
    if (profile.previewImage) {
        resumePreviewMini.innerHTML = `<img src="data:image/png;base64,${profile.previewImage}" alt="Resume">`;
    }
}

// Setup form handlers
function setupFormHandlers() {
    profileForm.addEventListener('submit', (e) => {
        e.preventDefault();
        saveProfile();
    });
    
    clearProfileBtn.addEventListener('click', clearProfile);
}

// Toast
function showToast(message) {
    toast.textContent = message;
    toast.classList.remove('hidden');
    setTimeout(() => toast.classList.add('hidden'), 2000);
}

// Loading
function showLoading(message) {
    document.getElementById('loading-message').textContent = message;
    loadingOverlay.classList.remove('hidden');
}

function hideLoading() {
    loadingOverlay.classList.add('hidden');
}
