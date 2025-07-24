// Mobile-specific JavaScript fixes for navbar and dropdown behavior

document.addEventListener('DOMContentLoaded', function() {
    // Detect if user is on a touch device
    const isTouchDevice = ('ontouchstart' in window) || 
                         (navigator.maxTouchPoints > 0) || 
                         (navigator.msMaxTouchPoints > 0);
    
    if (isTouchDevice) {
        document.body.classList.add('touch-device');
    }
    
    // Fix dropdown behavior on mobile
    const dropdownToggles = document.querySelectorAll('.dropdown-toggle');
    
    dropdownToggles.forEach(toggle => {
        // Remove any existing event listeners to prevent conflicts
        const newToggle = toggle.cloneNode(true);
        toggle.parentNode.replaceChild(newToggle, toggle);
        
        // Add improved touch handling
        newToggle.addEventListener('touchstart', function(e) {
            // Prevent ghost clicks
            e.stopPropagation();
        }, { passive: true });
        
        // Ensure dropdown closes when clicking outside
        newToggle.addEventListener('click', function(e) {
            e.stopPropagation();
        });
    });
    
    // Close dropdowns when clicking outside on mobile
    document.addEventListener('touchstart', function(e) {
        const openDropdowns = document.querySelectorAll('.dropdown.show');
        openDropdowns.forEach(dropdown => {
            if (!dropdown.contains(e.target)) {
                const toggle = dropdown.querySelector('.dropdown-toggle');
                if (toggle) {
                    // Use Bootstrap's dropdown API to close
                    const bsDropdown = bootstrap.Dropdown.getInstance(toggle);
                    if (bsDropdown) {
                        bsDropdown.hide();
                    }
                }
            }
        });
    });
    
    // Fix navbar collapse behavior on mobile
    const navbarToggler = document.querySelector('.navbar-toggler');
    const navbarCollapse = document.querySelector('#navbarNav');
    
    if (navbarToggler && navbarCollapse) {
        // Ensure smooth collapse animation
        navbarToggler.addEventListener('click', function() {
            // Remove focus from toggler after click
            setTimeout(() => {
                this.blur();
            }, 300);
        });
        
        // Close navbar when clicking a nav link on mobile
        const navLinks = navbarCollapse.querySelectorAll('.nav-link:not(.dropdown-toggle)');
        navLinks.forEach(link => {
            link.addEventListener('click', function() {
                if (window.innerWidth < 992) {
                    const bsCollapse = bootstrap.Collapse.getInstance(navbarCollapse);
                    if (bsCollapse) {
                        bsCollapse.hide();
                    }
                }
            });
        });
    }
    
    // Fix dropdown positioning on mobile
    const dropdowns = document.querySelectorAll('.dropdown');
    dropdowns.forEach(dropdown => {
        dropdown.addEventListener('shown.bs.dropdown', function() {
            const menu = this.querySelector('.dropdown-menu');
            if (menu && window.innerWidth < 992) {
                // Ensure dropdown is within viewport
                const rect = menu.getBoundingClientRect();
                if (rect.right > window.innerWidth) {
                    menu.style.left = 'auto';
                    menu.style.right = '0';
                }
                if (rect.left < 0) {
                    menu.style.left = '0';
                    menu.style.right = 'auto';
                }
            }
        });
    });
    
    // Prevent zoom on double tap for interactive elements
    let lastTouchEnd = 0;
    document.addEventListener('touchend', function(e) {
        const now = Date.now();
        if (now - lastTouchEnd <= 300) {
            e.preventDefault();
        }
        lastTouchEnd = now;
    }, false);
    
    // Fix iOS specific issues
    if (/iPad|iPhone|iPod/.test(navigator.userAgent)) {
        // Prevent iOS from auto-zooming on form inputs
        const inputs = document.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            input.addEventListener('focus', function() {
                document.querySelector('meta[name="viewport"]')
                    .setAttribute('content', 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=0');
            });
            input.addEventListener('blur', function() {
                document.querySelector('meta[name="viewport"]')
                    .setAttribute('content', 'width=device-width, initial-scale=1.0');
            });
        });
    }
});

// Utility function to close all dropdowns
window.closeAllDropdowns = function() {
    const dropdowns = document.querySelectorAll('.dropdown.show .dropdown-toggle');
    dropdowns.forEach(toggle => {
        const bsDropdown = bootstrap.Dropdown.getInstance(toggle);
        if (bsDropdown) {
            bsDropdown.hide();
        }
    });
};