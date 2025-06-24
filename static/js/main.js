document.addEventListener('DOMContentLoaded', function() {
console.log("main.js loaded!");

// Toggle credential method
const credentialMode = document.getElementById('credentialMode');
if (credentialMode) {
    credentialMode.onchange = function() {
        document.getElementById('credentialFileGroup').style.display = this.value === 'file' ? '' : 'none';
        document.getElementById('credentialTokenGroup').style.display = this.value === 'token' ? '' : 'none';
    };
}

// Add Account Form Show/Hide
const showAddAccountFormBtn = document.getElementById('showAddAccountFormBtn');
const addAccountModal = document.getElementById('addAccountModal'); // Get the modal element

// Wrap initialization in a check for required elements
if (showAddAccountFormBtn && addAccountModal) { // Check for modal element
    try {
        showAddAccountFormBtn.addEventListener('click', () => {
            // Bootstrap handles showing the modal based on data attributes.
            // No manual class manipulation needed here.
            console.log('Show Add Account button clicked.');
        });

        // Handle modal close event to reset form if needed (optional)
        addAccountModal.addEventListener('hidden.bs.modal', () => {
            const addAccountForm = document.getElementById('addAccountForm');
            if (addAccountForm) {
                 addAccountForm.reset(); // Clear form on modal close
                 console.log('Add Account modal closed, form reset.');
            }
        });

    } catch (error) {
        console.error('Error initializing Add Account form show/hide logic:', error);
    }
}

// Account Selection Logic (elements might not be on all pages, add checks)
const accountManagementSection = document.getElementById('account-management');
const uploadContentSection = document.getElementById('upload-content-section');
const selectedAccountIdInput = document.getElementById('selectedAccountId'); // This might only exist on certain pages
const selectedAccountNameDisplay = document.getElementById('selectedAccountName'); // This might only exist on certain pages
const accountsList = document.querySelector('.accounts-list');

// Function to handle account selection (add checks for elements used)
function selectAccount(accountId, accountName) {
    console.log(`Selecting account ID: ${accountId}, Name: ${accountName}`);
    // Set selected account in the upload form
    if (selectedAccountIdInput && selectedAccountNameDisplay) {
         selectedAccountIdInput.value = accountId;
         selectedAccountNameDisplay.textContent = accountName;
         console.log('Upload form account fields updated.');
    }

    // Highlight the selected account (add check for accountsList)
    if (accountsList) {
        document.querySelectorAll('.account-card').forEach(card => {
            card.classList.remove('selected');
            if (card.dataset.accountId === accountId) {
                card.classList.add('selected');
                console.log(`Highlighted account card for ID: ${accountId}`);
            }
        });
    }

    // Show upload section and keep the account management section visible
    const addAccountForm = document.getElementById('addAccountForm'); // Get the form element
    if (accountManagementSection && uploadContentSection) {
        uploadContentSection.classList.remove('hidden'); // Show upload section
        console.log('Upload content section shown.');
    }
     // Scroll to the upload section
     if(uploadContentSection) { 
         uploadContentSection.scrollIntoView({ behavior: 'smooth' });
         console.log('Scrolled to upload content section.');
     }
}

// Add event listeners to select account buttons (add check for accountsList)
try {
    if (accountsList) { // Only add listeners if account list is present
        document.querySelectorAll('.btn-select-account').forEach(button => {
            button.addEventListener('click', () => {
                const accountCard = button.closest('.account-card');
                const accountId = accountCard.dataset.accountId;
                const accountName = accountCard.dataset.accountName;
                selectAccount(accountId, accountName);
            });
        });
        console.log('Select Account button listeners added.');
    }
} catch (error) {
    console.error('Error initializing Select Account button listeners:', error);
}

// --- Toast Notification System ---
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        console.warn('Toast container not found.', message);
        return;
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;

    toastContainer.appendChild(toast);
    console.log(`Showing toast: ${message} (${type})`);

    // Show the toast
    requestAnimationFrame(() => {
        toast.classList.add('show');
    });

    // Hide and remove the toast after 5 seconds
    setTimeout(() => {
        toast.classList.remove('show');
        toast.addEventListener('transitionend', () => toast.remove(), { once: true });
        console.log(`Hiding toast: ${message}`);
    }, 5000);
}
// --- End Toast Notification System ---

// Add Account Form Submission
const addAccountForm = document.getElementById('addAccountForm');

// Attach event listener directly to the form's submit event
if (addAccountForm) {
    try {
        addAccountForm.addEventListener('submit', function(e) {
            const form = this; // The form element
            console.log('Add Account form submitted.');

            // The form action is /api/accounts
            // The backend at /api/accounts will handle the redirect for YouTube (platform_id=1)
            // For other platforms, it might handle differently (e.g., return JSON)

            // We will NOT prevent default here. Let the browser handle the standard form submission.
            // The backend will respond with a 302 redirect for YouTube, which the browser handles naturally.
            // For other platforms, the backend should respond with a normal HTTP status (e.g., 200, 400).
            // If the backend for non-YouTube platforms requires AJAX, we would add conditional e.preventDefault() here.

            // For now, let standard form submission handle all cases, relying on backend redirects.
            console.log('Allowing standard form submission for Add Account.');

             // Disable the submit button to prevent double submission
            const submitButton = form.querySelector('button[type="submit"]');
             if (submitButton) {
                 submitButton.disabled = true;
                 submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...'; // Indicate processing
                 console.log('Add Account submit button disabled.');
             }

        });
         console.log('Add Account form submit listener attached.');
    } catch (error) {
        console.error('Error attaching Add Account form submit listener:', error);
    }
}

// Upload Content Form AJAX (add check for uploadContentForm)
const uploadContentForm = document.getElementById('uploadContentForm');
// Add checks for elements within the form
const mediaInput = uploadContentForm ? uploadContentForm.querySelector('input[name="media"]') : null;
const mediaPreviewArea = document.getElementById('mediaPreviewArea'); // Assuming preview area is outside the form but related

if (uploadContentForm) { // Only initialize if the form exists
    try {
        if (mediaInput && mediaPreviewArea) { // Check for related elements
            // Event listener for media file input change
            mediaInput.addEventListener('change', function(event) {
                console.log('Media file input changed.');
                const file = event.target.files[0];
                if (!file) {
                    mediaPreviewArea.innerHTML = ''; // Clear preview if no file selected
                    console.log('No file selected, cleared preview.');
                    return;
                }

                const reader = new FileReader();
                reader.onload = function(e) {
                    mediaPreviewArea.innerHTML = ''; // Clear previous preview
                    console.log('File reader loaded.');

                    if (file.type.startsWith('image/')) {
                        const img = document.createElement('img');
                        img.src = e.target.result;
                        img.style.maxWidth = '100%';
                        img.style.maxHeight = '200px';
                        img.style.objectFit = 'contain';
                        mediaPreviewArea.appendChild(img);
                        console.log('Image preview added.');
                    } else if (file.type.startsWith('video/')) {
                        const video = document.createElement('video');
                        video.src = e.target.result;
                        video.controls = true;
                        video.style.maxWidth = '100%';
                        video.style.maxHeight = '200px';
                        video.style.objectFit = 'contain';
                        mediaPreviewArea.appendChild(video);
                        console.log('Video preview added.');
                    } else {
                        mediaPreviewArea.innerHTML = '<p>Preview not available for this file type.</p>';
                        console.log('Preview not available for file type:', file.type);
                    }
                };
                reader.readAsDataURL(file);
            });
             console.log('Media file input change listener attached.');
        }

        uploadContentForm.onsubmit = async function(e) {
            console.log('Upload Content form submitted.');
            e.preventDefault();

            const submitBtn = uploadContentForm.querySelector('button[type="submit"]');
            const originalBtnText = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Uploading...';
            console.log('Upload Content submit button disabled.');

            const formData = new FormData(uploadContentForm);
            
            try {
                const res = await fetch('/api/content', { method: 'POST', body: formData });
                console.log('Upload Content fetch response received.', res);
                
                if (res.ok) {
                     showToast('Content uploaded successfully!', 'success');
                     console.log('Content upload successful, reloading page.');
                     setTimeout(() => window.location.reload(), 500);
                } else {
                    const errorData = await res.json();
                    showToast('Failed to upload content: ' + (errorData.error || res.statusText), 'error');
                    console.error('Upload Content failed:', errorData);
                }
            } catch (error) {
                showToast('An error occurred during upload: ' + error.message, 'error');
                console.error('Error uploading content:', error);
            } finally {
                // Reset button state
                 if (submitBtn) { // Check if submitBtn exists
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalBtnText;
                    console.log('Upload Content submit button re-enabled.');
                 }
            }
        };
         console.log('Upload Content form submit listener attached.');
    } catch (error) {
        console.error('Error initializing Upload Content form:', error);
    }
}

// --- Delete Form AJAX ---
const deleteForms = document.querySelectorAll('form.delete-form');

// Wrap initialization in a check for the existence of forms
if (deleteForms.length > 0) {
    try {
        deleteForms.forEach(deleteForm => {
            deleteForm.addEventListener('submit', async function(e) {
                e.preventDefault();
                const form = this;
                const itemType = form.dataset.itemType;
                const submitButton = form.querySelector('button[type="submit"]');
                const originalBtnText = submitButton ? submitButton.innerHTML : '';
                if (!confirm(`Are you sure you want to delete this ${itemType}?`)) return;
                if (submitButton) {
                    submitButton.disabled = true;
                    submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Deleting...';
                }
                try {
                    const res = await fetch(form.action, {
                        method: 'POST',
                        body: new FormData(form)
                    });
                    if (res.ok) {
                        showToast(`${itemType.charAt(0).toUpperCase() + itemType.slice(1)} deleted successfully!`, 'success');
                        const itemRow = form.closest('tr');
                        if (itemRow) itemRow.remove();
                        if (itemType === 'account' && selectedAccountIdInput && uploadContentSection) {
                            const deletedAccountId = form.action.split('/').pop();
                            if (deletedAccountId && selectedAccountIdInput.value === deletedAccountId) {
                                uploadContentSection.classList.add('hidden');
                                selectedAccountIdInput.value = '';
                                if (selectedAccountNameDisplay) selectedAccountNameDisplay.textContent = 'None';
                            }
                        }
                    } else {
                        const errorData = await res.json();
                        showToast(`Failed to delete ${itemType}: ` + (errorData.error || res.statusText), 'error');
                    }
                } catch (error) {
                    showToast(`An error occurred while deleting ${itemType}: ` + error.message, 'error');
                } finally {
                    if (submitButton && form.closest('tr')) {
                        submitButton.disabled = false;
                        submitButton.innerHTML = originalBtnText;
                    }
                }
            });
        });
         console.log('Delete form submit listeners attached.');
    } catch (error) {
        console.error('Error initializing Delete Form listeners:', error);
    }
}

console.log("Delete form submitted!");

console.log('main.js script finished execution.');
}); 