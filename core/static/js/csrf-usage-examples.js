/**
 * CSRF Manager Usage Examples
 * This file demonstrates how to use the enhanced CSRF token management system
 */

// Example 1: Basic CSRF-protected fetch request
async function exampleBasicFetch() {
    try {
        const response = await window.csrfFetch('/api/some-endpoint/', {
            method: 'POST',
            body: JSON.stringify({ data: 'example' }),
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        console.log('Success:', data);
    } catch (error) {
        console.error('Error:', error);
    }
}

// Example 2: Using the CSRF manager directly
async function exampleDirectUsage() {
    try {
        // Get current token
        const token = await window.csrfManager.getToken();
        console.log('Current token:', token.substring(0, 10) + '...');
        
        // Manually refresh token
        await window.csrfManager.refreshToken();
        console.log('Token refreshed');
        
        // Get debug info
        const debugInfo = window.csrfManager.getDebugInfo();
        console.log('Debug info:', debugInfo);
    } catch (error) {
        console.error('Error managing CSRF token:', error);
    }
}

// Example 3: Form submission with automatic CSRF handling
function exampleFormSubmission() {
    const form = document.getElementById('myForm');
    if (form) {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            
            try {
                const response = await window.csrfFetch('/api/form-endpoint/', {
                    method: 'POST',
                    body: formData
                });
                
                if (response.ok) {
                    const result = await response.json();
                    console.log('Form submitted successfully:', result);
                } else {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
            } catch (error) {
                console.error('Form submission error:', error);
                // Handle error - show message to user
            }
        });
    }
}

// Example 4: Listening for token refresh events
function exampleEventHandling() {
    window.addEventListener('csrfTokenRefreshed', function(event) {
        console.log('CSRF token was refreshed:', event.detail.token.substring(0, 10) + '...');
        
        // You can update your application state here
        // For example, update any cached tokens or notify components
    });
}

// Example 5: Handling long-running operations
async function exampleLongRunningOperation() {
    // For operations that might take longer than the token lifetime
    try {
        // Refresh token before starting
        await window.csrfManager.refreshToken();
        
        // Perform long-running operation
        const response = await window.csrfFetch('/api/long-operation/', {
            method: 'POST',
            body: JSON.stringify({ operation: 'process-data' }),
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const result = await response.json();
        console.log('Long operation completed:', result);
    } catch (error) {
        console.error('Long operation failed:', error);
    }
}

// Example 6: Backward compatibility with existing code
function exampleBackwardCompatibility() {
    // Old way using getCookie - still works!
    const oldWayToken = getCookie('csrftoken');
    console.log('Token via old method:', oldWayToken?.substring(0, 10) + '...');
    
    // Old jQuery AJAX - will automatically get fresh token
    if (typeof $ !== 'undefined') {
        $.ajax({
            url: '/api/jquery-endpoint/',
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'X-Requested-With': 'XMLHttpRequest'
            },
            data: { test: 'data' },
            success: function(data) {
                console.log('jQuery AJAX success:', data);
            },
            error: function(xhr, status, error) {
                console.error('jQuery AJAX error:', error);
            }
        });
    }
}

// Example 7: Error handling and retry logic
async function exampleErrorHandling() {
    const maxRetries = 3;
    let retries = 0;
    
    while (retries < maxRetries) {
        try {
            const response = await window.csrfFetch('/api/unreliable-endpoint/', {
                method: 'POST',
                body: JSON.stringify({ attempt: retries + 1 }),
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                console.log('Success after', retries + 1, 'attempts:', data);
                break;
            } else if (response.status === 403) {
                // CSRF error - the manager should handle this automatically
                // but we can add additional logic if needed
                console.log('CSRF error detected, retrying...');
                await window.csrfManager.refreshToken();
            } else {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
        } catch (error) {
            retries++;
            if (retries >= maxRetries) {
                console.error('Max retries exceeded:', error);
                throw error;
            }
            console.log(`Retry ${retries}/${maxRetries} after error:`, error.message);
            
            // Wait before retrying (exponential backoff)
            await new Promise(resolve => setTimeout(resolve, Math.pow(2, retries) * 1000));
        }
    }
}

// Example 8: File upload with CSRF protection
async function exampleFileUpload() {
    const fileInput = document.getElementById('fileInput');
    if (fileInput && fileInput.files[0]) {
        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        formData.append('description', 'Uploaded via CSRF manager');
        
        try {
            const response = await window.csrfFetch('/api/upload/', {
                method: 'POST',
                body: formData
                // No need to set Content-Type for FormData
            });
            
            if (response.ok) {
                const result = await response.json();
                console.log('File uploaded successfully:', result);
            } else {
                throw new Error(`Upload failed: ${response.status}`);
            }
        } catch (error) {
            console.error('File upload error:', error);
        }
    }
}

// Initialize examples when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Set up event handlers
    exampleEventHandling();
    
    // You can call other examples as needed
    // exampleBasicFetch();
    // exampleDirectUsage();
    
    console.log('CSRF Manager examples loaded. Available functions:');
    console.log('- exampleBasicFetch()');
    console.log('- exampleDirectUsage()');
    console.log('- exampleFormSubmission()');
    console.log('- exampleLongRunningOperation()');
    console.log('- exampleBackwardCompatibility()');
    console.log('- exampleErrorHandling()');
    console.log('- exampleFileUpload()');
});
