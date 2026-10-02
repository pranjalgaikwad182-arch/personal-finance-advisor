/**
 * Dashboard Chart.js Visualizations
 * Fetches dynamic data from the backend and initializes 4 responsive charts.
 */

document.addEventListener("DOMContentLoaded", () => {
    const dashboardMeta = document.getElementById("dashboard-meta");
    if (!dashboardMeta) return;

    const month = dashboardMeta.dataset.month;
    const year = dashboardMeta.dataset.year;

    fetch(`/api/dashboard-charts?month=${month}&year=${year}`)
        .then((response) => response.json())
        .then((data) => {
            initIncomeVsExpenseChart(data.income_vs_expense);
            initCategoryChart(data.category_chart);
            initTrendChart(data.trend_chart);
            initBudgetVsActualChart(data.budget_vs_actual);
        })
        .catch((error) => {
            console.error("Error loading dashboard chart data:", error);
        });
});

function initIncomeVsExpenseChart(chartData) {
    const ctx = document.getElementById("incomeVsExpenseChart");
    if (!ctx) return;

    new Chart(ctx, {
        type: "bar",
        data: chartData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (context) => ` Amount: ₹${context.raw.toLocaleString("en-IN")}`,
                    },
                },
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: (value) => `₹${value.toLocaleString("en-IN")}`,
                    },
                },
            },
        },
    });
}

function initCategoryChart(chartData) {
    const ctx = document.getElementById("categoryChart");
    if (!ctx) return;

    new Chart(ctx, {
        type: "doughnut",
        data: chartData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: "right",
                    labels: { boxWidth: 14, font: { size: 12 } },
                },
                tooltip: {
                    callbacks: {
                        label: (context) => ` ${context.label}: ₹${context.raw.toLocaleString("en-IN")}`,
                    },
                },
            },
        },
    });
}

function initTrendChart(chartData) {
    const ctx = document.getElementById("trendChart");
    if (!ctx) return;

    new Chart(ctx, {
        data: chartData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: "top" },
                tooltip: {
                    callbacks: {
                        label: (context) => ` ${context.dataset.label}: ₹${context.raw.toLocaleString("en-IN")}`,
                    },
                },
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: (value) => `₹${value.toLocaleString("en-IN")}`,
                    },
                },
            },
        },
    });
}

function initBudgetVsActualChart(chartData) {
    const ctx = document.getElementById("budgetVsActualChart");
    if (!ctx) return;

    new Chart(ctx, {
        type: "bar",
        data: chartData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: "top" },
                tooltip: {
                    callbacks: {
                        label: (context) => ` ${context.dataset.label}: ₹${context.raw.toLocaleString("en-IN")}`,
                    },
                },
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: (value) => `₹${value.toLocaleString("en-IN")}`,
                    },
                },
            },
        },
    });
}
