/**
 * CSRF Token Management System
 * Provides automatic token refresh, caching, and error handling
 */

class CSRFManager {
    constructor() {
        this.token = null;
        this.refreshInterval = 25 * 60 * 1000; // 25 minutes (Django default is 30 minutes)
        this.maxRetries = 3;
        this.retryDelay = 1000; // 1 second
        this.isRefreshing = false;
        this.refreshPromise = null;
        
        // Initialize token on page load
        this.init();
    }
    
    /**
     * Initialize CSRF manager
     */
    init() {
        // Get initial token from cookie or meta tag
        this.token = this.getCookieToken() || this.getMetaToken();
        
        // Set up periodic refresh
        this.startPeriodicRefresh();
        
        // Handle page visibility changes
        this.handleVisibilityChange();
        
        // Set up beforeunload handler for cleanup
        window.addEventListener('beforeunload', () => {
            this.stopPeriodicRefresh();
        });
    }
    
    /**
     * Get CSRF token from cookie
     */
    getCookieToken() {
        const name = 'csrftoken';
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    /**
     * Get CSRF token from meta tag
     */
    getMetaToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : null;
    }
    
    /**
     * Get current CSRF token
     */
    async getToken() {
        // If token is null or expired, refresh it
        if (!this.token) {
            await this.refreshToken();
        }
        return this.token;
    }
    
    /**
     * Refresh CSRF token from server
     */
    async refreshToken(retryCount = 0) {
        // Prevent multiple simultaneous refresh requests
        if (this.isRefreshing && this.refreshPromise) {
            return this.refreshPromise;
        }
        
        this.isRefreshing = true;
        this.refreshPromise = this._performRefresh(retryCount);
        
        try {
            const result = await this.refreshPromise;
            return result;
        } finally {
            this.isRefreshing = false;
            this.refreshPromise = null;
        }
    }
    
    /**
     * Perform the actual token refresh
     */
    async _performRefresh(retryCount = 0) {
        try {
            const response = await fetch('/api/csrf-token/', {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                },
                credentials: 'same-origin'
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.status === 'success' && data.csrf_token) {
                this.token = data.csrf_token;
                
                // Update meta tag if exists
                const meta = document.querySelector('meta[name="csrf-token"]');
                if (meta) {
                    meta.setAttribute('content', this.token);
                }
                
                // Update all CSRF input fields
                this.updateCSRFInputs();
                
                // Dispatch event for other scripts
                window.dispatchEvent(new CustomEvent('csrfTokenRefreshed', {
                    detail: { token: this.token }
                }));
                
                console.log('CSRF token refreshed successfully');
                return this.token;
            } else {
                throw new Error('Invalid response from server');
            }
        } catch (error) {
            console.error('Failed to refresh CSRF token:', error);
            
            // Retry logic
            if (retryCount < this.maxRetries) {
                console.log(`Retrying CSRF token refresh (${retryCount + 1}/${this.maxRetries})`);
                await this.sleep(this.retryDelay * Math.pow(2, retryCount)); // Exponential backoff
                return this._performRefresh(retryCount + 1);
            }
            
            // If all retries failed, try to get token from cookie as fallback
            const fallbackToken = this.getCookieToken();
            if (fallbackToken) {
                console.log('Using fallback token from cookie');
                this.token = fallbackToken;
                return this.token;
            }
            
            throw error;
        }
    }
    
    /**
     * Update all CSRF input fields in the page
     */
    updateCSRFInputs() {
        const inputs = document.querySelectorAll('input[name="csrfmiddlewaretoken"]');
        inputs.forEach(input => {
            input.value = this.token;
        });
    }
    
    /**
     * Start periodic token refresh
     */
    startPeriodicRefresh() {
        this.stopPeriodicRefresh(); // Clear any existing interval
        this.refreshIntervalId = setInterval(() => {
            this.refreshToken().catch(error => {
                console.error('Periodic CSRF token refresh failed:', error);
            });
        }, this.refreshInterval);
    }
    
    /**
     * Stop periodic token refresh
     */
    stopPeriodicRefresh() {
        if (this.refreshIntervalId) {
            clearInterval(this.refreshIntervalId);
            this.refreshIntervalId = null;
        }
    }
    
    /**
     * Handle page visibility changes
     */
    handleVisibilityChange() {
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                // Page is hidden, stop periodic refresh
                this.stopPeriodicRefresh();
            } else {
                // Page is visible again, restart periodic refresh and refresh token immediately
                this.startPeriodicRefresh();
                this.refreshToken().catch(error => {
                    console.error('CSRF token refresh on visibility change failed:', error);
                });
            }
        });
    }
    
    /**
     * Handle CSRF failures in fetch requests
     */
    async handleCSRFFailure(originalRequest) {
        console.log('CSRF failure detected, refreshing token...');
        
        try {
            await this.refreshToken();
            
            // Clone the original request with new token
            const newHeaders = new Headers(originalRequest.headers);
            newHeaders.set('X-CSRFToken', this.token);
            
            const newRequest = new Request(originalRequest.url, {
                method: originalRequest.method,
                headers: newHeaders,
                body: originalRequest.body,
                credentials: originalRequest.credentials,
                mode: originalRequest.mode,
                cache: originalRequest.cache,
                redirect: originalRequest.redirect,
                referrer: originalRequest.referrer,
                integrity: originalRequest.integrity
            });
            
            return fetch(newRequest);
        } catch (error) {
            console.error('Failed to handle CSRF failure:', error);
            throw error;
        }
    }
    
    /**
     * Enhanced fetch with automatic CSRF handling
     */
    async fetch(url, options = {}) {
        // Ensure we have a token
        const token = await this.getToken();
        
        // Set up headers
        const headers = new Headers(options.headers || {});
        if (!headers.has('X-CSRFToken') && token) {
            headers.set('X-CSRFToken', token);
        }
        if (!headers.has('X-Requested-With')) {
            headers.set('X-Requested-With', 'XMLHttpRequest');
        }
        
        const requestOptions = {
            ...options,
            headers,
            credentials: options.credentials || 'same-origin'
        };
        
        try {
            const response = await fetch(url, requestOptions);
            
            // Check for CSRF failure (403 Forbidden)
            if (response.status === 403) {
                const text = await response.text();
                if (text.includes('CSRF') || text.includes('Forbidden')) {
                    // Create a request object for retry
                    const originalRequest = new Request(url, requestOptions);
                    return this.handleCSRFFailure(originalRequest);
                }
            }
            
            return response;
        } catch (error) {
            console.error('Fetch error:', error);
            throw error;
        }
    }
    
    /**
     * Sleep utility function
     */
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    /**
     * Get debug information
     */
    getDebugInfo() {
        return {
            token: this.token ? `${this.token.substring(0, 10)}...` : null,
            isRefreshing: this.isRefreshing,
            refreshInterval: this.refreshInterval,
            hasRefreshInterval: !!this.refreshIntervalId
        };
    }
}

// Global instance
window.csrfManager = new CSRFManager();

// Backward compatibility: provide getCookie function
window.getCookie = function(name) {
    if (name === 'csrftoken') {
        return window.csrfManager.token || window.csrfManager.getCookieToken();
    }
    return window.csrfManager.getCookieToken.call({}, name);
};

// Enhanced fetch for global use
window.csrfFetch = function(url, options) {
    return window.csrfManager.fetch(url, options);
};

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CSRFManager;
}
