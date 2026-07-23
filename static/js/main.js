// --- MEDICARE HOSPITAL MANAGEMENT SYSTEM - INTERACTIVE FRONTEND JS ---

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initGlobalSearch();
    initDynamicBilling();
    initAnalyticsCharts();
});

/* --- THEME TOGGLE & PERSISTENCE --- */
function initTheme() {
    const savedTheme = localStorage.getItem('medicare_theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme);

    const themeToggleBtn = document.getElementById('themeToggleBtn');
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', () => {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('medicare_theme', newTheme);
            updateThemeIcon(newTheme);
        });
    }
}

function updateThemeIcon(theme) {
    const themeIcon = document.getElementById('themeIcon');
    if (themeIcon) {
        themeIcon.className = theme === 'dark' ? 'ri-sun-fill' : 'ri-moon-fill';
    }
}

/* --- GLOBAL SEARCH FUNCTIONALITY --- */
function initGlobalSearch() {
    const searchInput = document.getElementById('globalSearchInput');
    const searchResults = document.getElementById('globalSearchResults');

    if (!searchInput || !searchResults) return;

    let debounceTimer;

    searchInput.addEventListener('input', (e) => {
        clearTimeout(debounceTimer);
        const query = e.target.value.trim();

        if (query.length < 2) {
            searchResults.classList.remove('active');
            searchResults.innerHTML = '';
            return;
        }

        debounceTimer = setTimeout(() => {
            fetch(`/api/search?q=${encodeURIComponent(query)}`)
                .then(res => res.json())
                .then(data => {
                    if (data.length === 0) {
                        searchResults.innerHTML = '<div style="padding: 1rem; color: var(--text-muted); font-size: 0.85rem;">No matching records found.</div>';
                    } else {
                        searchResults.innerHTML = data.map(item => `
                            <a href="${item.url}" class="search-result-item">
                                <div>
                                    <div style="font-weight: 700;">${item.title}</div>
                                    <div style="font-size: 0.78rem; color: var(--text-muted);">${item.subtitle}</div>
                                </div>
                                <span class="badge badge-info">${item.type}</span>
                            </a>
                        `).join('');
                    }
                    searchResults.classList.add('active');
                })
                .catch(err => console.error('Search API error:', err));
        }, 300);
    });

    document.addEventListener('click', (e) => {
        if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
            searchResults.classList.remove('active');
        }
    });
}

/* --- MODAL CONTROL HELPERS --- */
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.add('active');
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.remove('active');
}

/* --- DYNAMIC BILLING LINE ITEMS & TOTALS --- */
function initDynamicBilling() {
    const itemsContainer = document.getElementById('billingItemsContainer');
    const addItemBtn = document.getElementById('addBillItemBtn');

    if (!itemsContainer || !addItemBtn) return;

    addItemBtn.addEventListener('click', () => {
        const newRow = document.createElement('div');
        newRow.className = 'form-grid bill-item-row';
        newRow.style.marginBottom = '0.75rem';
        newRow.innerHTML = `
            <div style="grid-column: span 2;">
                <input type="text" name="item_desc[]" class="form-control" placeholder="Item / Service description (e.g. Lab Test)" required>
            </div>
            <div>
                <input type="number" step="0.01" name="item_amount[]" class="form-control bill-amount-input" placeholder="Amount ($)" required>
            </div>
            <div style="display: flex; align-items: center;">
                <button type="button" class="btn btn-danger btn-sm remove-item-btn"><i class="ri-delete-bin-line"></i></button>
            </div>
        `;
        itemsContainer.appendChild(newRow);
        attachBillingCalculators();
    });

    itemsContainer.addEventListener('click', (e) => {
        if (e.target.closest('.remove-item-btn')) {
            const row = e.target.closest('.bill-item-row');
            if (itemsContainer.querySelectorAll('.bill-item-row').length > 1) {
                row.remove();
                calculateInvoiceTotals();
            } else {
                alert('At least one line item is required.');
            }
        }
    });

    attachBillingCalculators();
}

function attachBillingCalculators() {
    const amountInputs = document.querySelectorAll('.bill-amount-input');
    const taxInput = document.getElementById('billTaxInput');
    const discountInput = document.getElementById('billDiscountInput');

    amountInputs.forEach(input => {
        input.removeEventListener('input', calculateInvoiceTotals);
        input.addEventListener('input', calculateInvoiceTotals);
    });

    if (taxInput) {
        taxInput.removeEventListener('input', calculateInvoiceTotals);
        taxInput.addEventListener('input', calculateInvoiceTotals);
    }

    if (discountInput) {
        discountInput.removeEventListener('input', calculateInvoiceTotals);
        discountInput.addEventListener('input', calculateInvoiceTotals);
    }

    calculateInvoiceTotals();
}

function calculateInvoiceTotals() {
    const amountInputs = document.querySelectorAll('.bill-amount-input');
    const taxInput = document.getElementById('billTaxInput');
    const discountInput = document.getElementById('billDiscountInput');

    let subtotal = 0;
    amountInputs.forEach(input => {
        const val = parseFloat(input.value) || 0;
        subtotal += val;
    });

    const taxRate = taxInput ? (parseFloat(taxInput.value) || 0) : 5.0;
    const discount = discountInput ? (parseFloat(discountInput.value) || 0) : 0.0;

    const taxAmount = (subtotal * taxRate) / 100.0;
    const grandTotal = Math.max(0, subtotal + taxAmount - discount);

    const subtotalEl = document.getElementById('calcSubtotal');
    const taxEl = document.getElementById('calcTax');
    const totalEl = document.getElementById('calcTotal');

    if (subtotalEl) subtotalEl.textContent = `$${subtotal.toFixed(2)}`;
    if (taxEl) taxEl.textContent = `$${taxAmount.toFixed(2)}`;
    if (totalEl) totalEl.textContent = `$${grandTotal.toFixed(2)}`;
}

/* --- PRESCRIPTION MEDICINES DYNAMIC ROW ADDITION --- */
function addMedicineRow() {
    const container = document.getElementById('medicinesContainer');
    if (!container) return;

    const newRow = document.createElement('div');
    newRow.className = 'form-grid medicine-item-row';
    newRow.style.marginBottom = '0.75rem';
    newRow.innerHTML = `
        <div>
            <input type="text" name="med_name[]" class="form-control" placeholder="Medicine Name" required>
        </div>
        <div>
            <input type="text" name="med_dosage[]" class="form-control" placeholder="Dosage (e.g. 500mg)">
        </div>
        <div>
            <input type="text" name="med_freq[]" class="form-control" placeholder="Frequency (e.g. 1-0-1)">
        </div>
        <div>
            <input type="text" name="med_duration[]" class="form-control" placeholder="Duration (e.g. 5 Days)">
        </div>
        <div style="display: flex; align-items: center;">
            <button type="button" class="btn btn-danger btn-sm" onclick="this.closest('.medicine-item-row').remove()"><i class="ri-delete-bin-line"></i></button>
        </div>
    `;
    container.appendChild(newRow);
}

/* --- DASHBOARD CHART.JS INITIALIZATION --- */
function initAnalyticsCharts() {
    const deptCanvas = document.getElementById('deptChart');
    const apptCanvas = document.getElementById('apptChart');

    if (!deptCanvas && !apptCanvas) return;

    fetch('/api/analytics')
        .then(res => res.json())
        .then(data => {
            if (deptCanvas && window.Chart) {
                new Chart(deptCanvas.getContext('2d'), {
                    type: 'doughnut',
                    data: {
                        labels: data.departments.labels,
                        datasets: [{
                            data: data.departments.counts,
                            backgroundColor: ['#0284c7', '#0d9488', '#6366f1', '#f59e0b', '#ec4899', '#8b5cf6']
                        }]
                    },
                    options: {
                        responsive: true,
                        plugins: {
                            legend: { position: 'bottom', labels: { boxWidth: 12 } }
                        }
                    }
                });
            }

            if (apptCanvas && window.Chart) {
                new Chart(apptCanvas.getContext('2d'), {
                    type: 'bar',
                    data: {
                        labels: data.appointments.labels,
                        datasets: [{
                            label: 'Appointments',
                            data: data.appointments.counts,
                            backgroundColor: '#0284c7',
                            borderRadius: 6
                        }]
                    },
                    options: {
                        responsive: true,
                        scales: {
                            y: { beginAtZero: true, ticks: { precision: 0 } }
                        },
                        plugins: {
                            legend: { display: false }
                        }
                    }
                });
            }
        })
        .catch(err => console.error('Analytics chart error:', err));
}
