/**
 * Password Strength Checker
 * Real-time validation with visual feedback
 */

function initPasswordStrengthChecker() {
    const passwordInput = document.getElementById('id_password1');
    const strengthFill = document.getElementById('passwordStrengthFill');
    const requirements = {
        length: document.getElementById('reqLength'),
        uppercase: document.getElementById('reqUppercase'),
        number: document.getElementById('reqNumber'),
        special: document.getElementById('reqSpecial'),
    };

    if (!passwordInput || !strengthFill) return;

    passwordInput.addEventListener('input', function() {
        const password = passwordInput.value;
        checkPasswordStrength(password, strengthFill, requirements);
    });
}

function checkPasswordStrength(password, strengthFill, requirements) {
    // Check individual requirements
    const hasLength = password.length >= 8;
    const hasUppercase = /[A-Z]/.test(password);
    const hasNumber = /[0-9]/.test(password);
    const hasSpecial = /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password);

    // Update requirement indicators
    updateRequirement(requirements.length, hasLength);
    updateRequirement(requirements.uppercase, hasUppercase);
    updateRequirement(requirements.number, hasNumber);
    updateRequirement(requirements.special, hasSpecial);

    // Calculate strength
    const metCount = [hasLength, hasUppercase, hasNumber, hasSpecial].filter(Boolean).length;
    let strength = 'weak';
    
    if (metCount === 4) {
        strength = 'strong';
    } else if (metCount >= 2) {
        strength = 'medium';
    }

    // Update strength bar
    strengthFill.className = 'password-strength-fill ' + strength;
}

function updateRequirement(element, met) {
    if (!element) return;
    
    const icon = element.querySelector('.password-requirement-icon i');
    if (met) {
        element.classList.add('met');
        if (icon) {
            icon.className = 'fas fa-check';
        }
    } else {
        element.classList.remove('met');
        if (icon) {
            icon.className = 'fas fa-times';
        }
    }
}

