/**
 * expenses.js - Client-side validation and interactive utilities for Expense Management
 */

document.addEventListener("DOMContentLoaded", () => {
    // Client-side validation for expense forms
    const expenseForms = document.querySelectorAll("form[action*='/expenses/add'], form[action*='/expenses/edit']");
    
    expenseForms.forEach(form => {
        form.addEventListener("submit", (e) => {
            const amountInput = form.querySelector("input[name='amount']");
            const categoryInput = form.querySelector("select[name='category']");
            const dateInput = form.querySelector("input[name='expense_date']");

            if (amountInput) {
                const val = parseFloat(amountInput.value);
                if (isNaN(val) || val <= 0) {
                    e.preventDefault();
                    alert("Please enter a valid expense amount greater than 0.");
                    amountInput.focus();
                    return false;
                }
            }

            if (categoryInput && !categoryInput.value.trim()) {
                e.preventDefault();
                alert("Please select a category.");
                categoryInput.focus();
                return false;
            }

            if (dateInput && !dateInput.value) {
                e.preventDefault();
                alert("Please select a valid date.");
                dateInput.focus();
                return false;
            }
        });
    });

    // Real-time table filter highlight if search input is used
    const searchInput = document.querySelector("input[name='search']");
    if (searchInput && searchInput.value.trim()) {
        const query = searchInput.value.trim().toLowerCase();
        const rows = document.querySelectorAll("table tbody tr");
        rows.forEach(row => {
            const descCell = row.children[2];
            if (descCell && descCell.textContent.toLowerCase().includes(query)) {
                row.classList.add("table-warning");
            }
        });
    }
});
