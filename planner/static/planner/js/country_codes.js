/**
 * Country Code Picker for Phone Number Input
 * Provides searchable dropdown with country flags and codes
 */

const COUNTRY_CODES = [
    { code: '+1', flag: '🇺🇸', name: 'United States' },
    { code: '+44', flag: '🇬🇧', name: 'United Kingdom' },
    { code: '+1', flag: '🇨🇦', name: 'Canada' },
    { code: '+61', flag: '🇦🇺', name: 'Australia' },
    { code: '+33', flag: '🇫🇷', name: 'France' },
    { code: '+49', flag: '🇩🇪', name: 'Germany' },
    { code: '+39', flag: '🇮🇹', name: 'Italy' },
    { code: '+34', flag: '🇪🇸', name: 'Spain' },
    { code: '+31', flag: '🇳🇱', name: 'Netherlands' },
    { code: '+32', flag: '🇧🇪', name: 'Belgium' },
    { code: '+41', flag: '🇨🇭', name: 'Switzerland' },
    { code: '+46', flag: '🇸🇪', name: 'Sweden' },
    { code: '+47', flag: '🇳🇴', name: 'Norway' },
    { code: '+45', flag: '🇩🇰', name: 'Denmark' },
    { code: '+358', flag: '🇫🇮', name: 'Finland' },
    { code: '+353', flag: '🇮🇪', name: 'Ireland' },
    { code: '+351', flag: '🇵🇹', name: 'Portugal' },
    { code: '+30', flag: '🇬🇷', name: 'Greece' },
    { code: '+43', flag: '🇦🇹', name: 'Austria' },
    { code: '+48', flag: '🇵🇱', name: 'Poland' },
    { code: '+420', flag: '🇨🇿', name: 'Czech Republic' },
    { code: '+36', flag: '🇭🇺', name: 'Hungary' },
    { code: '+40', flag: '🇷🇴', name: 'Romania' },
    { code: '+7', flag: '🇷🇺', name: 'Russia' },
    { code: '+81', flag: '🇯🇵', name: 'Japan' },
    { code: '+82', flag: '🇰🇷', name: 'South Korea' },
    { code: '+86', flag: '🇨🇳', name: 'China' },
    { code: '+91', flag: '🇮🇳', name: 'India' },
    { code: '+65', flag: '🇸🇬', name: 'Singapore' },
    { code: '+60', flag: '🇲🇾', name: 'Malaysia' },
    { code: '+66', flag: '🇹🇭', name: 'Thailand' },
    { code: '+84', flag: '🇻🇳', name: 'Vietnam' },
    { code: '+62', flag: '🇮🇩', name: 'Indonesia' },
    { code: '+63', flag: '🇵🇭', name: 'Philippines' },
    { code: '+64', flag: '🇳🇿', name: 'New Zealand' },
    { code: '+27', flag: '🇿🇦', name: 'South Africa' },
    { code: '+55', flag: '🇧🇷', name: 'Brazil' },
    { code: '+52', flag: '🇲🇽', name: 'Mexico' },
    { code: '+54', flag: '🇦🇷', name: 'Argentina' },
    { code: '+56', flag: '🇨🇱', name: 'Chile' },
];

function initCountryCodePicker() {
    const toggle = document.getElementById('countryCodeToggle');
    const dropdown = document.getElementById('countryCodeDropdown');
    const display = document.getElementById('countryCodeDisplay');
    const hiddenInput = document.querySelector('input[name="country_code"]');
    
    if (!toggle || !dropdown || !display) return;

    // Populate dropdown
    COUNTRY_CODES.forEach(country => {
        const option = document.createElement('div');
        option.className = 'country-option';
        option.innerHTML = `
            <span>${country.flag}</span>
            <span>${country.name}</span>
            <span style="margin-left: auto; color: var(--text-secondary);">${country.code}</span>
        `;
        option.addEventListener('click', function() {
            display.innerHTML = `${country.flag} ${country.code}`;
            if (hiddenInput) {
                hiddenInput.value = country.code;
            }
            dropdown.classList.remove('open');
        });
        dropdown.appendChild(option);
    });

    // Toggle dropdown
    toggle.addEventListener('click', function(e) {
        e.stopPropagation();
        dropdown.classList.toggle('open');
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', function(e) {
        if (!toggle.contains(e.target) && !dropdown.contains(e.target)) {
            dropdown.classList.remove('open');
        }
    });

    // Set default
    if (hiddenInput && !hiddenInput.value) {
        hiddenInput.value = '+1';
    }
}

