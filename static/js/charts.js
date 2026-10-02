/**
 * charts.js - Chart.js Helper Utilities for Financial Dashboards
 * Provides reusable configurations for financial charts with INR formatting.
 */

window.FinanceCharts = {
    formatCurrency: function(value) {
        return "₹" + Number(value).toLocaleString("en-IN");
    },

    createBarChart: function(canvasId, labels, data, colors, options = {}) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;
        return new Chart(ctx, {
            type: "bar",
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: colors,
                    borderRadius: 6,
                }]
            },
            options: Object.assign({
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => " " + FinanceCharts.formatCurrency(ctx.raw)
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: (val) => FinanceCharts.formatCurrency(val)
                        }
                    }
                }
            }, options)
        });
    },

    createDoughnutChart: function(canvasId, labels, data, colors, options = {}) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;
        return new Chart(ctx, {
            type: "doughnut",
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: colors,
                    borderWidth: 2,
                    borderColor: "#ffffff"
                }]
            },
            options: Object.assign({
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: "right" },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => ` ${ctx.label}: ` + FinanceCharts.formatCurrency(ctx.raw)
                        }
                    }
                }
            }, options)
        });
    }
};
