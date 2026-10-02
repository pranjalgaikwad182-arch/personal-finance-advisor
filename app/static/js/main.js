/**
 * Main application JavaScript for Personal Finance Advisor
 */

document.addEventListener("DOMContentLoaded", () => {
    // 1. Auto-dismiss flash alerts after 6 seconds
    const alerts = document.querySelectorAll(".alert-dismissible");
    alerts.forEach((alert) => {
        setTimeout(() => {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) {
                bsAlert.close();
            }
        }, 6000);
    });

    // 2. Initialize all Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(
        document.querySelectorAll('[data-bs-toggle="tooltip"]')
    );
    tooltipTriggerList.map((tooltipTriggerEl) => new bootstrap.Tooltip(tooltipTriggerEl));

    // 3. Dynamic modal pre-population for Editing Income
    const editIncomeModal = document.getElementById("editIncomeModal");
    if (editIncomeModal) {
        editIncomeModal.addEventListener("show.bs.modal", (event) => {
            const button = event.relatedTarget;
            const id = button.getAttribute("data-id");
            const amount = button.getAttribute("data-amount");
            const source = button.getAttribute("data-source");
            const description = button.getAttribute("data-description");
            const date = button.getAttribute("data-date");

            const form = editIncomeModal.querySelector("#editIncomeForm");
            form.action = `/income/edit/${id}`;
            editIncomeModal.querySelector("#edit_income_amount").value = amount;
            editIncomeModal.querySelector("#edit_income_source").value = source;
            editIncomeModal.querySelector("#edit_income_description").value = description || "";
            editIncomeModal.querySelector("#edit_income_date").value = date;
        });
    }

    // 4. Dynamic modal pre-population for Editing Expense
    const editExpenseModal = document.getElementById("editExpenseModal");
    if (editExpenseModal) {
        editExpenseModal.addEventListener("show.bs.modal", (event) => {
            const button = event.relatedTarget;
            const id = button.getAttribute("data-id");
            const amount = button.getAttribute("data-amount");
            const category = button.getAttribute("data-category");
            const description = button.getAttribute("data-description");
            const date = button.getAttribute("data-date");

            const form = editExpenseModal.querySelector("#editExpenseForm");
            form.action = `/expenses/edit/${id}`;
            editExpenseModal.querySelector("#edit_expense_amount").value = amount;
            editExpenseModal.querySelector("#edit_expense_category").value = category;
            editExpenseModal.querySelector("#edit_expense_description").value = description || "";
            editExpenseModal.querySelector("#edit_expense_date").value = date;
        });
    }

    // 5. Dynamic modal pre-population for Savings Goal Contribution
    const contributeGoalModal = document.getElementById("contributeGoalModal");
    if (contributeGoalModal) {
        contributeGoalModal.addEventListener("show.bs.modal", (event) => {
            const button = event.relatedTarget;
            const id = button.getAttribute("data-id");
            const name = button.getAttribute("data-name");
            const remaining = button.getAttribute("data-remaining");

            const form = contributeGoalModal.querySelector("#contributeGoalForm");
            form.action = `/savings/${id}/contribute`;
            contributeGoalModal.querySelector("#contribute_goal_name").textContent = name;
            contributeGoalModal.querySelector("#contribute_goal_remaining").textContent = remaining;
            contributeGoalModal.querySelector("#contribute_amount").value = "";
        });
    }

    // 6. Dynamic modal pre-population for Editing Savings Goal
    const editGoalModal = document.getElementById("editGoalModal");
    if (editGoalModal) {
        editGoalModal.addEventListener("show.bs.modal", (event) => {
            const button = event.relatedTarget;
            const id = button.getAttribute("data-id");
            const name = button.getAttribute("data-name");
            const targetAmount = button.getAttribute("data-target");
            const targetDate = button.getAttribute("data-date");
            const description = button.getAttribute("data-description");

            const form = editGoalModal.querySelector("#editGoalForm");
            form.action = `/savings/edit/${id}`;
            editGoalModal.querySelector("#edit_goal_name").value = name;
            editGoalModal.querySelector("#edit_goal_target").value = targetAmount;
            editGoalModal.querySelector("#edit_goal_date").value = targetDate;
            editGoalModal.querySelector("#edit_goal_desc").value = description || "";
        });
    }

    // ==========================================================================
    // Epic 4 Story 2: Single-Page AI Financial Advisor Asynchronous Form & Render
    // ==========================================================================
    const financeForm = document.getElementById("financeForm");
    const resultsSection = document.getElementById("resultsSection");
    const submitBtn = document.getElementById("submitAnalyzeBtn");
    const addExpenseBtn = document.getElementById("addExpenseRowBtn");
    const dynamicExpensesContainer = document.getElementById("dynamicExpensesContainer");

    // Currency Formatter Utility
    function formatRupees(amount) {
        const val = Math.round(Number(amount) || 0);
        return "₹" + val.toLocaleString("en-IN");
    }

    // Category Icon Mapper
    function getCategoryIcon(catName) {
        const key = String(catName).toLowerCase();
        if (key.includes("rent") || key.includes("housing")) return '<i class="fa-solid fa-house text-primary"></i>';
        if (key.includes("food") || key.includes("groceries") || key.includes("dining")) return '<i class="fa-solid fa-utensils text-warning"></i>';
        if (key.includes("transport") || key.includes("travel") || key.includes("commute")) return '<i class="fa-solid fa-car-side text-info"></i>';
        if (key.includes("entertainment") || key.includes("fun") || key.includes("leisure")) return '<i class="fa-solid fa-film text-danger"></i>';
        if (key.includes("util") || key.includes("bill") || key.includes("electricity")) return '<i class="fa-solid fa-bolt text-warning"></i>';
        if (key.includes("health") || key.includes("medical")) return '<i class="fa-solid fa-heart-pulse text-danger"></i>';
        if (key.includes("shop") || key.includes("cloth")) return '<i class="fa-solid fa-bag-shopping text-primary"></i>';
        if (key.includes("saving") || key.includes("invest")) return '<i class="fa-solid fa-piggy-bank text-success"></i>';
        return '<i class="fa-solid fa-receipt text-secondary"></i>';
    }

    // Add Custom Expense Row
    if (addExpenseBtn && dynamicExpensesContainer) {
        addExpenseBtn.addEventListener("click", () => {
            const rowId = "expense_row_" + Date.now();
            const rowDiv = document.createElement("div");
            rowDiv.className = "row g-2 align-items-center mb-2 dynamic-expense-row";
            rowDiv.id = rowId;
            rowDiv.innerHTML = `
                <div class="col-6">
                    <input type="text" class="form-control expense-cat-name" placeholder="Category Name (e.g. Healthcare)" required>
                </div>
                <div class="col-5">
                    <div class="input-group">
                        <span class="input-group-text">₹</span>
                        <input type="number" class="form-control expense-cat-amount" placeholder="0" min="0" step="1" required>
                    </div>
                </div>
                <div class="col-1 text-end">
                    <button type="button" class="btn btn-outline-danger btn-sm rounded-circle" title="Remove" onclick="document.getElementById('${rowId}').remove()">
                        <i class="fa-solid fa-times"></i>
                    </button>
                </div>
            `;
            dynamicExpensesContainer.appendChild(rowDiv);
        });
    }

    // Scenario Quick-Fill Handlers
    const scenarioPresets = {
        salaried: {
            income: 50000,
            goal: "emergency_fund",
            expenses: {
                rent: 15000,
                food: 7000,
                transport: 3500,
                utilities: 2500,
                entertainment: 3000,
            }
        },
        student: {
            income: 12000,
            goal: "gadget_purchase",
            expenses: {
                food: 4500,
                transport: 1800,
                entertainment: 1500,
                other: 1200,
            }
        },
        freelancer: {
            income: 65000,
            goal: "emergency_fund",
            expenses: {
                rent: 18000,
                food: 8500,
                transport: 4000,
                healthcare: 3000,
                shopping: 5000,
            }
        },
        household: {
            income: 85000,
            goal: "vacation",
            expenses: {
                rent: 22000,
                food: 14000,
                utilities: 6000,
                healthcare: 5000,
                transport: 4500,
                shopping: 6000,
            }
        }
    };

    document.querySelectorAll(".scenario-preset-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
            const key = btn.getAttribute("data-scenario");
            const data = scenarioPresets[key];
            if (!data) return;

            const incomeInput = document.getElementById("monthlyIncome");
            const goalSelect = document.getElementById("financialGoal");
            if (incomeInput) incomeInput.value = data.income;
            if (goalSelect) goalSelect.value = data.goal;

            // Clear custom dynamic rows
            if (dynamicExpensesContainer) dynamicExpensesContainer.innerHTML = "";

            // Populate standard inputs
            const standardCats = ["rent", "food", "transport", "entertainment", "utilities", "healthcare", "shopping", "other"];
            standardCats.forEach((cat) => {
                const el = document.getElementById("expense_" + cat);
                if (el) {
                    el.value = data.expenses[cat] || "";
                }
            });
        });
    });

    // Dynamic Render Results Function
    window.renderResults = function(data) {
        if (!resultsSection) return;

        // 1. Financial Overview / Summary Card
        const summaryTextEl = document.getElementById("summaryText");
        const totalIncomeEl = document.getElementById("summaryIncome");
        const totalExpensesEl = document.getElementById("summaryExpenses");
        const netSavingsEl = document.getElementById("summarySavings");
        const savingsRateEl = document.getElementById("summarySavingsRate");

        let totalExp = 0;
        let totalInc = Number(document.getElementById("monthlyIncome").value) || 0;

        if (data.budget) {
            Object.values(data.budget).forEach((b) => {
                totalExp += Number(b.actual_amount) || 0;
            });
        }
        const netSav = Math.max(0, totalInc - totalExp);
        const savRate = totalInc > 0 ? ((netSav / totalInc) * 100).toFixed(1) : 0;

        if (totalIncomeEl) totalIncomeEl.textContent = formatRupees(totalInc);
        if (totalExpensesEl) totalExpensesEl.textContent = formatRupees(totalExp);
        if (netSavingsEl) netSavingsEl.textContent = formatRupees(netSav);
        if (savingsRateEl) savingsRateEl.textContent = savRate + "%";
        if (summaryTextEl) summaryTextEl.textContent = data.summary || "Your monthly financial plan has been calculated and optimized.";

        // 2. Budget Cards Container (Left Column)
        const budgetContainer = document.getElementById("budgetCardsContainer");
        if (budgetContainer && data.budget) {
            budgetContainer.innerHTML = "";
            Object.entries(data.budget).forEach(([category, info]) => {
                const actual = Number(info.actual_amount) || 0;
                const recommended = Number(info.recommended_amount) || 0;
                const pct = Number(info.percentage_of_income) || 0;
                const isExceeded = info.status === "exceeded" || actual > recommended;
                
                // Progress bar percentage (capped at 100% for display)
                const usageRatio = recommended > 0 ? Math.min(100, Math.round((actual / recommended) * 100)) : 100;
                const barColor = isExceeded ? "#ef4444" : (usageRatio > 80 ? "#f59e0b" : "#10b981");

                const card = document.createElement("div");
                card.className = "budget-card";
                card.innerHTML = `
                    <div class="d-flex align-items-center justify-content-between mb-2">
                        <div class="d-flex align-items-center gap-2">
                            <div class="category-icon bg-light">
                                ${getCategoryIcon(category)}
                            </div>
                            <div>
                                <h6 class="fw-bold mb-0 text-capitalize">${category}</h6>
                                <small class="text-muted">${pct}% of income</small>
                            </div>
                        </div>
                        <div class="text-end">
                            <span class="badge ${isExceeded ? 'bg-danger-subtle text-danger' : 'bg-success-subtle text-success'} rounded-pill px-2 py-1 small fw-semibold">
                                ${isExceeded ? '<i class="fa-solid fa-triangle-exclamation me-1"></i>Over Budget' : '<i class="fa-solid fa-check me-1"></i>Within Budget'}
                            </span>
                        </div>
                    </div>
                    <div class="d-flex justify-content-between small text-muted mt-2">
                        <span>Actual: <strong class="text-dark">${formatRupees(actual)}</strong></span>
                        <span>Recommended: <strong class="text-dark">${formatRupees(recommended)}</strong></span>
                    </div>
                    <div class="budget-progress-bar">
                        <div class="budget-progress-fill" style="width: ${usageRatio}%; background-color: ${barColor};"></div>
                    </div>
                `;
                budgetContainer.appendChild(card);
            });
        }

        // 3. Spending Analysis Chips (Right Column)
        const analysisContainer = document.getElementById("analysisChipsContainer");
        if (analysisContainer && Array.isArray(data.analysis)) {
            analysisContainer.innerHTML = "";
            data.analysis.forEach((item) => {
                const isOver = String(item.status).toLowerCase().includes("over");
                const chip = document.createElement("div");
                chip.className = `analysis-chip ${isOver ? 'status-overspending' : 'status-on-track'}`;
                chip.innerHTML = `
                    <div class="d-flex align-items-center justify-content-between">
                        <strong class="text-capitalize">${item.category} (${item.percentage}%)</strong>
                        <span class="chip-badge ${isOver ? 'badge-overspending' : 'badge-on-track'}">
                            ${isOver ? '<i class="fa-solid fa-circle-exclamation"></i> Overspending' : '<i class="fa-solid fa-circle-check"></i> On Track'}
                        </span>
                    </div>
                    <p class="small mb-0 text-dark opacity-90">${item.message}</p>
                `;
                analysisContainer.appendChild(chip);
            });
        }

        // 4. Saving Suggestions List (Right Column)
        const suggestionsContainer = document.getElementById("suggestionsListContainer");
        if (suggestionsContainer && Array.isArray(data.suggestions)) {
            suggestionsContainer.innerHTML = "";
            data.suggestions.forEach((tip) => {
                const li = document.createElement("li");
                li.innerHTML = tip.replace(/(₹[\d,]+)/g, '<strong class="text-success">$1</strong>');
                suggestionsContainer.appendChild(li);
            });
        }

        // Show results section
        resultsSection.classList.remove("d-none");
    };

    // Asynchronous Form Submission Handler
    if (financeForm) {
        financeForm.addEventListener("submit", async (e) => {
            e.preventDefault();

            const incomeVal = Number(document.getElementById("monthlyIncome").value);
            if (!incomeVal || incomeVal <= 0) {
                alert("Please enter a valid monthly income greater than 0.");
                return;
            }

            // Gather standard expenses
            const expenses = {};
            const standardCats = ["rent", "food", "transport", "entertainment", "utilities", "healthcare", "shopping", "other"];
            standardCats.forEach((cat) => {
                const el = document.getElementById("expense_" + cat);
                if (el && el.value && Number(el.value) > 0) {
                    expenses[cat] = Number(el.value);
                }
            });

            // Gather dynamic custom category expenses
            document.querySelectorAll(".dynamic-expense-row").forEach((row) => {
                const nameInput = row.querySelector(".expense-cat-name");
                const amountInput = row.querySelector(".expense-cat-amount");
                if (nameInput && amountInput && nameInput.value.trim() && Number(amountInput.value) > 0) {
                    expenses[nameInput.value.trim().toLowerCase()] = Number(amountInput.value);
                }
            });

            if (Object.keys(expenses).length === 0) {
                alert("Please enter at least one expense category amount greater than 0.");
                return;
            }

            const goalSelect = document.getElementById("financialGoal");
            const goal = goalSelect ? goalSelect.value : "emergency_fund";

            // Save original button state and set animated loading state
            const origBtnHtml = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = `<span class="btn-loader"></span> Analyzing Finances with Gemini AI...`;

            try {
                const response = await fetch("/analyse", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    body: JSON.stringify({
                        income: incomeVal,
                        expenses: expenses,
                        goal: goal,
                    }),
                });

                const resultData = await response.json();

                if (!response.ok || !resultData.success) {
                    throw new Error(resultData.error || "Failed to generate financial analysis.");
                }

                // Render Results dynamically
                renderResults(resultData);

                // Smooth scroll to the results section
                if (resultsSection) {
                    resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
                }
            } catch (err) {
                console.error("Analysis Error:", err);
                alert("Unable to complete financial analysis: " + err.message);
            } finally {
                // Restore button state
                submitBtn.disabled = false;
                submitBtn.innerHTML = origBtnHtml;
            }
        });
    }
});

