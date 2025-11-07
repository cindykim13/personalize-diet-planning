/**
 * Interactive Password Strength Checker
 * Provides real-time visual feedback as user types password
 */

(function() {
    'use strict';

    // Wait for DOM to be ready
    document.addEventListener('DOMContentLoaded', function() {
        const passwordInput = document.getElementById('id_password1');
        const strengthContainer = document.getElementById('password-strength-container');
        const strengthBar = document.getElementById('password-strength-bar');
        const requirements = {
            length: document.getElementById('req-length'),
            uppercase: document.getElementById('req-uppercase'),
            number: document.getElementById('req-number'),
            special: document.getElementById('req-special')
        };

        // Only initialize if password input exists
        if (!passwordInput || !strengthContainer) {
            return;
        }

        // Hide strength checker initially
        strengthContainer.style.display = 'none';

        // Add event listener for password input
        passwordInput.addEventListener('input', function() {
            const password = passwordInput.value;
            
            // Show/hide strength checker
            if (password.length > 0) {
                strengthContainer.style.display = 'block';
                strengthContainer.classList.add('active');
            } else {
                strengthContainer.style.display = 'none';
                strengthContainer.classList.remove('active');
                // Reset all requirements
                resetRequirements();
                return;
            }

            // Check each requirement
            const checks = {
                length: password.length >= 8,
                uppercase: /[A-Z]/.test(password),
                number: /[0-9]/.test(password),
                special: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)
            };

            // Update requirement indicators
            updateRequirement(requirements.length, checks.length);
            updateRequirement(requirements.uppercase, checks.uppercase);
            updateRequirement(requirements.number, checks.number);
            updateRequirement(requirements.special, checks.special);

            // Calculate strength score and update bar
            const score = Object.values(checks).filter(Boolean).length;
            updateStrengthBar(score, strengthBar);
        });

        // Function to reset all requirements
        function resetRequirements() {
            Object.values(requirements).forEach(function(req) {
                if (req) {
                    req.classList.remove('valid', 'invalid');
                    req.classList.add('invalid');
                }
            });
            if (strengthBar) {
                strengthBar.classList.remove('weak', 'medium', 'strong');
                strengthBar.style.width = '0%';
            }
        }

        // Function to update requirement indicator
        function updateRequirement(element, isValid) {
            if (!element) return;
            
            // Remove all classes
            element.classList.remove('valid', 'invalid');
            
            if (isValid) {
                element.classList.add('valid');
            } else {
                element.classList.add('invalid');
            }
        }

        // Function to update strength bar
        function updateStrengthBar(score, barElement) {
            if (!barElement) return;

            // Remove all strength classes
            barElement.classList.remove('weak', 'medium', 'strong');

            if (score === 0 || score === 1) {
                barElement.classList.add('weak');
            } else if (score === 2 || score === 3) {
                barElement.classList.add('medium');
            } else if (score === 4) {
                barElement.classList.add('strong');
            }
        }

        // Also check password confirmation match
        const password2Input = document.getElementById('id_password2');
        if (password2Input) {
            password2Input.addEventListener('input', function() {
                const password1 = passwordInput.value;
                const password2 = password2Input.value;
                
                if (password2.length > 0) {
                    if (password1 === password2) {
                        password2Input.setCustomValidity('');
                    } else {
                        password2Input.setCustomValidity('Passwords do not match');
                    }
                } else {
                    password2Input.setCustomValidity('');
                }
            });
        }

        // Trigger initial validation if a value is prefilled (e.g., after validation errors)
        if (passwordInput.value) {
            passwordInput.dispatchEvent(new Event('input'));
        }
    });
})();
