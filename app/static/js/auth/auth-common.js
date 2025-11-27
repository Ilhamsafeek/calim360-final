// app/static/js/auth/auth-common.js
/**
 * Shared Authentication Functionality
 * Used across login, registration, and other auth screens
 */

class AuthCommon {
    constructor() {
        this.initializeElements();
        this.setupEventListeners();
        this.initializeLanguage();
        this.initializeTheme();
    }

    initializeElements() {
        // Common elements
        this.alertContainer = document.getElementById('alertContainer');
        this.modalContainer = document.getElementById('modalContainer');
        this.languageSwitcher = document.querySelector('.language-switcher');
        this.langButtons = document.querySelectorAll('.lang-btn');
        this.footerLinks = document.querySelectorAll('.footer-link[data-modal]');
    }

    setupEventListeners() {
        // Language switcher
        this.langButtons.forEach(btn => {
            btn.addEventListener('click', (e) => this.switchLanguage(e));
        });

        // Footer modal links
        this.footerLinks.forEach(link => {
            link.addEventListener('click', (e) => this.openModal(e));
        });

        // Modal close handling
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal-container') || 
                e.target.classList.contains('modal-close')) {
                this.closeModal();
            }
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeModal();
            }
        });

        // Form validation helpers
        document.addEventListener('blur', (e) => {
            if (e.target.matches('.form-input')) {
                this.validateField(e.target);
            }
        }, true);

        // Auto-hide alerts
        document.addEventListener('click', (e) => {
            if (e.target.closest('.alert')) {
                this.dismissAlert(e.target.closest('.alert'));
            }
        });
    }

    initializeLanguage() {
        const savedLang = localStorage.getItem('language') || 'en';
        this.setLanguage(savedLang);
    }

    initializeTheme() {
        const savedTheme = localStorage.getItem('theme') || 'auto';
        this.setTheme(savedTheme);
    }

    switchLanguage(e) {
        e.preventDefault();
        const newLang = e.target.closest('.lang-btn').dataset.lang;
        this.setLanguage(newLang);
    }

    setLanguage(lang) {
        // Update UI
        this.langButtons.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.lang === lang);
        });

        // Update document attributes
        document.documentElement.setAttribute('lang', lang);
        document.documentElement.setAttribute('dir', lang === 'ar' ? 'rtl' : 'ltr');

        // Save preference
        localStorage.setItem('language', lang);

        // Update text content (you can expand this with actual translations)
        this.updateLanguageContent(lang);
    }

    updateLanguageContent(lang) {
        const translations = {
            'en': {
                'sign_in': 'Sign In',
                'register': 'Register',
                'privacy_policy': 'Privacy Policy',
                'terms_of_service': 'Terms of Service',
                'support': 'Support',
                'contact': 'Contact',
                'email': 'Email Address',
                'password': 'Password',
                'remember_me': 'Remember me',
                'forgot_password': 'Forgot password?',
                'create_account': 'Create account',
                'welcome_back': 'Welcome Back',
                'sign_in_desc': 'Sign in to your Smart CLM account'
            },
            'ar': {
                'sign_in': 'تسجيل الدخول',
                'register': 'إنشاء حساب',
                'privacy_policy': 'سياسة الخصوصية',
                'terms_of_service': 'شروط الخدمة',
                'support': 'الدعم',
                'contact': 'اتصل بنا',
                'email': 'عنوان البريد الإلكتروني',
                'password': 'كلمة المرور',
                'remember_me': 'تذكرني',
                'forgot_password': 'نسيت كلمة المرور؟',
                'create_account': 'إنشاء حساب',
                'welcome_back': 'مرحباً بعودتك',
                'sign_in_desc': 'سجل الدخول إلى حساب Smart CLM الخاص بك'
            }
        };

        // Update translatable elements
        document.querySelectorAll('[data-translate]').forEach(element => {
            const key = element.dataset.translate;
            if (translations[lang] && translations[lang][key]) {
                element.textContent = translations[lang][key];
            }
        });
    }

    setTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
    }

    // Alert Management
    showAlert(message, type = 'info', duration = 5000) {
        const alertId = 'alert-' + Date.now();
        const iconMap = {
            'error': 'ti-alert-circle',
            'success': 'ti-check-circle',
            'warning': 'ti-alert-triangle',
            'info': 'ti-info-circle'
        };

        const alertHTML = `
            <div class="alert alert-${type}" id="${alertId}">
                <i class="ti ${iconMap[type]}"></i>
                <span>${message}</span>
                <button type="button" class="alert-close" onclick="authCommon.dismissAlert('${alertId}')">
                    <i class="ti ti-x"></i>
                </button>
            </div>
        `;

        this.alertContainer.insertAdjacentHTML('beforeend', alertHTML);

        // Auto-dismiss after duration
        if (duration > 0) {
            setTimeout(() => {
                this.dismissAlert(alertId);
            }, duration);
        }

        return alertId;
    }

    dismissAlert(alertIdOrElement) {
        let alertElement;
        if (typeof alertIdOrElement === 'string') {
            alertElement = document.getElementById(alertIdOrElement);
        } else {
            alertElement = alertIdOrElement;
        }

        if (alertElement) {
            alertElement.style.animation = 'slideOutRight 0.3s ease forwards';
            setTimeout(() => {
                if (alertElement.parentNode) {
                    alertElement.parentNode.removeChild(alertElement);
                }
            }, 300);
        }
    }

    // Modal Management
    openModal(e) {
        e.preventDefault();
        const modalType = e.target.dataset.modal;
        
        const modalContent = this.getModalContent(modalType);
        
        const modalHTML = `
            <div class="modal">
                <div class="modal-header">
                    <h3 class="modal-title">${modalContent.title}</h3>
                    <button type="button" class="modal-close">
                        <i class="ti ti-x"></i>
                    </button>
                </div>
                <div class="modal-content">
                    ${modalContent.content}
                </div>
            </div>
        `;

        this.modalContainer.innerHTML = modalHTML;
        this.modalContainer.classList.add('show');
        document.body.style.overflow = 'hidden';
    }

    closeModal() {
        this.modalContainer.classList.remove('show');
        document.body.style.overflow = '';
        setTimeout(() => {
            this.modalContainer.innerHTML = '';
        }, 300);
    }

    getModalContent(type) {
        const content = {
            'privacy': {
                title: 'Privacy Policy',
                content: `
                    <p>At Smart CLM, we take your privacy seriously. This privacy policy explains how we collect, use, and protect your personal information.</p>
                    <h4>Information We Collect</h4>
                    <ul>
                        <li>Account information (name, email, company details)</li>
                        <li>Usage data and analytics</li>
                        <li>Document metadata (not content)</li>
                    </ul>
                    <h4>How We Use Your Information</h4>
                    <ul>
                        <li>To provide and improve our services</li>
                        <li>To communicate with you about your account</li>
                        <li>To ensure security and prevent fraud</li>
                    </ul>
                    <h4>Data Protection</h4>
                    <p>We use industry-standard encryption and security measures to protect your data. Your documents are encrypted both in transit and at rest.</p>
                `
            },
            'terms': {
                title: 'Terms of Service',
                content: `
                    <p>Welcome to Smart CLM. By using our service, you agree to these terms.</p>
                    <h4>Service Description</h4>
                    <p>Smart CLM provides contract lifecycle management services including document creation, review, negotiation, and tracking.</p>
                    <h4>User Responsibilities</h4>
                    <ul>
                        <li>Maintain the confidentiality of your account credentials</li>
                        <li>Use the service in compliance with applicable laws</li>
                        <li>Respect intellectual property rights</li>
                    </ul>
                    <h4>Service Availability</h4>
                    <p>We strive to provide 99.9% uptime but cannot guarantee uninterrupted service availability.</p>
                `
            },
            'support': {
                title: 'Support',
                content: `
                    <p>Need help? We're here to assist you.</p>
                    <h4>Contact Options</h4>
                    <div style="margin: 1rem 0;">
                        <p><strong>Email:</strong> support@smrtclm.com</p>
                        <p><strong>Phone:</strong> +974 4444 5555</p>
                        <p><strong>Live Chat:</strong> Available 24/7</p>
                    </div>
                    <h4>Common Issues</h4>
                    <ul>
                        <li><a href="#" onclick="authCommon.closeModal()">Login Problems</a></li>
                        <li><a href="#" onclick="authCommon.closeModal()">Password Reset</a></li>
                        <li><a href="#" onclick="authCommon.closeModal()">Account Setup</a></li>
                        <li><a href="#" onclick="authCommon.closeModal()">Billing Questions</a></li>
                    </ul>
                `
            },
            'contact': {
                title: 'Contact Us',
                content: `
                    <div style="margin: 1rem 0;">
                        <h4>Headquarters</h4>
                        <p>Smart CLM<br>
                        West Bay Tower<br>
                        Doha, Qatar</p>
                        
                        <h4>Business Hours</h4>
                        <p>Sunday - Thursday: 8:00 AM - 6:00 PM (GST)<br>
                        Friday - Saturday: Closed</p>
                        
                        <h4>Contact Information</h4>
                        <p><strong>General:</strong> info@smrtclm.com<br>
                        <strong>Sales:</strong> sales@smrtclm.com<br>
                        <strong>Support:</strong> support@smrtclm.com</p>
                    </div>
                `
            }
        };

        return content[type] || { title: 'Information', content: '<p>Content not available.</p>' };
    }

    // Form Validation Helpers
    validateField(field) {
        const value = field.value.trim();
        const type = field.type;
        const required = field.hasAttribute('required');
        
        let isValid = true;
        let errorMessage = '';

        // Clear previous error state
        field.classList.remove('error');
        const errorElement = field.parentNode.querySelector('.field-error');
        if (errorElement) {
            errorElement.remove();
        }

        // Required field validation
        if (required && !value) {
            isValid = false;
            errorMessage = 'This field is required';
        }
        // Email validation
        else if (type === 'email' && value) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(value)) {
                isValid = false;
                errorMessage = 'Please enter a valid email address';
            }
        }
        // Password validation
        else if (type === 'password' && value && field.name === 'password') {
            if (value.length < 8) {
                isValid = false;
                errorMessage = 'Password must be at least 8 characters long';
            } else if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(value)) {
                isValid = false;
                errorMessage = 'Password must contain at least one uppercase letter, one lowercase letter, and one number';
            }
        }
        // Confirm password validation
        else if (field.name === 'confirmPassword' && value) {
            const passwordField = document.querySelector('input[name="password"]');
            if (passwordField && value !== passwordField.value) {
                isValid = false;
                errorMessage = 'Passwords do not match';
            }
        }

        // Show error if validation failed
        if (!isValid) {
            field.classList.add('error');
            const errorHTML = `<div class="field-error" style="color: var(--danger-color); font-size: 0.75rem; margin-top: 0.25rem;">${errorMessage}</div>`;
            field.parentNode.insertAdjacentHTML('beforeend', errorHTML);
        }

        return isValid;
    }

    validateForm(form) {
        const fields = form.querySelectorAll('.form-input');
        let isValid = true;

        fields.forEach(field => {
            if (!this.validateField(field)) {
                isValid = false;
            }
        });

        return isValid;
    }

    // Loading State Management
    setFormLoading(form, loading) {
        const submitButton = form.querySelector('button[type="submit"]');
        const inputs = form.querySelectorAll('input, select, textarea');
        
        if (loading) {
            submitButton.disabled = true;
            submitButton.classList.add('loading');
            inputs.forEach(input => input.disabled = true);
        } else {
            submitButton.disabled = false;
            submitButton.classList.remove('loading');
            inputs.forEach(input => input.disabled = false);
        }
    }

    // Password Visibility Toggle
    togglePasswordVisibility(button) {
        const input = button.parentNode.querySelector('input');
        const icon = button.querySelector('i');
        
        if (input.type === 'password') {
            input.type = 'text';
            icon.className = 'ti ti-eye-off';
        } else {
            input.type = 'password';
            icon.className = 'ti ti-eye';
        }
    }

    // Storage Helpers
    setStorage(key, value, type = 'localStorage') {
        try {
            const storage = type === 'sessionStorage' ? sessionStorage : localStorage;
            storage.setItem(key, JSON.stringify(value));
        } catch (error) {
            console.warn('Storage not available:', error);
        }
    }

    getStorage(key, type = 'localStorage') {
        try {
            const storage = type === 'sessionStorage' ? sessionStorage : localStorage;
            const value = storage.getItem(key);
            return value ? JSON.parse(value) : null;
        } catch (error) {
            console.warn('Storage not available:', error);
            return null;
        }
    }

    removeStorage(key, type = 'localStorage') {
        try {
            const storage = type === 'sessionStorage' ? sessionStorage : localStorage;
            storage.removeItem(key);
        } catch (error) {
            console.warn('Storage not available:', error);
        }
    }

    // API Helper
    async apiCall(url, options = {}) {
        try {
            const defaultOptions = {
                headers: {
                    'Content-Type': 'application/json',
                },
            };

            const response = await fetch(url, {
                ...defaultOptions,
                ...options,
                headers: {
                    ...defaultOptions.headers,
                    ...options.headers,
                },
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.message || `HTTP error! status: ${response.status}`);
            }

            return data;
        } catch (error) {
            console.error('API call failed:', error);
            throw error;
        }
    }

    // Utility Methods
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }

    // Device Detection
    isMobile() {
        return window.innerWidth <= 768;
    }

    // Accessibility Helpers
    announceToScreenReader(message) {
        const announcement = document.createElement('div');
        announcement.setAttribute('aria-live', 'polite');
        announcement.setAttribute('aria-atomic', 'true');
        announcement.style.position = 'absolute';
        announcement.style.left = '-10000px';
        announcement.style.width = '1px';
        announcement.style.height = '1px';
        announcement.style.overflow = 'hidden';
        announcement.textContent = message;
        
        document.body.appendChild(announcement);
        
        setTimeout(() => {
            document.body.removeChild(announcement);
        }, 1000);
    }
}

// Create global instance
window.authCommon = new AuthCommon();

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AuthCommon;
}

// Add utility CSS classes for animations
const utilityCSS = `
    @keyframes slideOutRight {
        from {
            opacity: 1;
            transform: translateX(0);
        }
        to {
            opacity: 0;
            transform: translateX(100%);
        }
    }
    
    .field-error {
        color: var(--danger-color);
        font-size: 0.75rem;
        margin-top: 0.25rem;
        display: flex;
        align-items: center;
        gap: 0.25rem;
    }
    
    .alert-close {
        background: none;
        border: none;
        color: inherit;
        cursor: pointer;
        font-size: 16px;
        margin-left: auto;
        padding: 0.25rem;
        border-radius: var(--radius-sm);
        transition: var(--transition);
    }
    
    .alert-close:hover {
        background: rgba(0, 0, 0, 0.1);
    }
`;

// Inject utility CSS
const styleSheet = document.createElement('style');
styleSheet.textContent = utilityCSS;
document.head.appendChild(styleSheet);