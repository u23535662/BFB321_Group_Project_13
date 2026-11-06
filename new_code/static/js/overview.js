/**
 * ============================================================================
 * Course: BFB321 - Supply Chain Web Application
 * Script: new_code/static/js/overview.js
 * Description:
 *     Client-side interactivity and Chart.js dynamic controller for the
 *     Supply Chain Overview Dashboard.
 * 
 * JAVASCRIPT USAGE JUSTIFICATION (Per AGENTS.md & Course Guidelines):
 *     1. All business logic, EOQ equations, safety stock calculations, SQL queries,
 *        and simulation loops are strictly executed server-side in Python/Flask
 *        (models.py and app.py), honoring the Python-first architecture.
 *     2. JavaScript is strictly isolated to the browser presentation layer for:
 *        a) Real-time interactive switching between State A (Financial $) and
 *           State B (Unit Quantities) on Chart 1 without requiring full page reload.
 *        b) Real-time curve focusing, non-selected line de-emphasis (graying out),
 *           and Forecast vs. Actual data overlapping on Chart 2.
 *        c) Accessible modal display for "Analysis" and "Month End" dialogs.
 * ============================================================================
 */

(function () {
  "use strict";

  // Data injected safely from Flask via Jinja2 JSON serialization
  const dashboardData = window.OVERVIEW_SERVER_DATA || {};
  const products = dashboardData.products || [];
  const portfolio = dashboardData.portfolio || {};
  const dates = dashboardData.shared_dates || [];
  let currentSelectedId = dashboardData.selected_id || null;

  // Chart references
  let stackedBarChart = null;
  let eoqSimulationChart = null;

  // Color constants matching the Stanway aesthetic
  const COLOR_AVAILABLE = "#10b981"; // Emerald Green
  const COLOR_RESERVED = "#f97316";  // Orange
  const COLOR_SOLD = "#ef4444";      // Crimson Red
  const COLOR_ROP = "#3b82f6";       // Royal Blue
  const COLOR_SS = "#dc2626";        // Bright Red
  const COLOR_ACTUAL = "#f59e0b";    // Amber Gold

  /**
   * Helper: Format number as currency string ($X,XXX.XX)
   */
  function formatMoney(num) {
    return "$" + Number(num || 0).toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }

  /**
   * Helper: Format integer with thousands commas
   */
  function formatUnits(num) {
    return Number(num || 0).toLocaleString("en-US") + " units";
  }

  // ==========================================================================
  // CHART 1: STACKED BAR CHART CONTROLLER
  // ==========================================================================
  function initStackedBarChart() {
    const ctx = document.getElementById("stackedBarCanvas");
    if (!ctx) return;

    stackedBarChart = new Chart(ctx, {
      type: "bar",
      data: getStackedBarChartData(currentSelectedId),
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: "index",
          intersect: false,
        },
        scales: {
          x: {
            stacked: true,
            ticks: {
              color: "#152d2f",
              font: { weight: "600", size: 12 },
            },
            grid: {
              display: false,
            },
          },
          y: {
            stacked: true,
            ticks: {
              color: "#152d2f",
              font: { weight: "600", size: 11 },
              callback: function (value) {
                // State A: Format as $ | State B: Format as units
                return currentSelectedId ? value + " u" : "$" + (value / 1000) + "k";
              },
            },
            grid: {
              color: "rgba(21, 45, 47, 0.15)",
            },
          },
        },
        plugins: {
          legend: {
            position: "top",
            labels: {
              color: "#152d2f",
              font: { weight: "700" },
              usePointStyle: true,
              padding: 15,
            },
          },
          tooltip: {
            callbacks: {
              label: function (context) {
                const raw = context.raw || 0;
                const label = context.dataset.label || "";
                if (currentSelectedId) {
                  return `${label}: ${formatUnits(raw)}`;
                } else {
                  return `${label}: ${formatMoney(raw)}`;
                }
              },
            },
          },
        },
      },
    });

    updateChart1Header(currentSelectedId);
  }

  /**
   * Generates datasets for Chart 1 based on selection state:
   * State A: Financial/Money format ($) across all products
   * State B: Actual quantity / stock units for selected product
   */
  function getStackedBarChartData(selectedId) {
    if (!selectedId) {
      // STATE A: DEFAULT - ALL PRODUCTS IN FINANCIAL/MONEY FORMAT ($)
      const labels = products.map((p) => p.name.split(" ")[0] + " " + (p.name.split(" ")[1] || ""));
      labels.push("Total Portfolio");

      const availableValues = products.map((p) => p.available_val);
      availableValues.push(portfolio.total_available_val);

      const reservedValues = products.map((p) => p.reserved_val);
      reservedValues.push(portfolio.total_reserved_val);

      const soldValues = products.map((p) => p.sold_val);
      soldValues.push(portfolio.total_sold_val);

      return {
        labels: labels,
        datasets: [
          {
            label: "Stock Available ($)",
            data: availableValues,
            backgroundColor: COLOR_AVAILABLE,
            borderRadius: 6,
          },
          {
            label: "Reserved Stock ($)",
            data: reservedValues,
            backgroundColor: COLOR_RESERVED,
            borderRadius: 6,
          },
          {
            label: "Sold Stock ($)",
            data: soldValues,
            backgroundColor: COLOR_SOLD,
            borderRadius: 6,
          },
        ],
      };
    } else {
      // STATE B: SINGLE PRODUCT SELECTED - ACTUAL QUANTITY / STOCK UNITS
      const target = products.find((p) => String(p.product_id) === String(selectedId));
      if (!target) return { labels: [], datasets: [] };

      return {
        labels: [target.name],
        datasets: [
          {
            label: "Stock Available (Units)",
            data: [target.available_qty],
            backgroundColor: COLOR_AVAILABLE,
            borderRadius: 8,
            barThickness: 50,
          },
          {
            label: "Reserved Stock (Units)",
            data: [target.reserved_qty],
            backgroundColor: COLOR_RESERVED,
            borderRadius: 8,
            barThickness: 50,
          },
          {
            label: "Sold Stock (Units)",
            data: [target.sold_qty],
            backgroundColor: COLOR_SOLD,
            borderRadius: 8,
            barThickness: 50,
          },
        ],
      };
    }
  }

  function updateChart1Header(selectedId) {
    const pill = document.getElementById("chart1ModePill");
    const metric1 = document.getElementById("c1MetricAvailable");
    const metric2 = document.getElementById("c1MetricReserved");
    const metric3 = document.getElementById("c1MetricSold");

    if (!selectedId) {
      if (pill) pill.innerHTML = '<i class="fa-solid fa-dollar-sign"></i> State A: Financial Valuation ($)';
      if (metric1) metric1.textContent = formatMoney(portfolio.total_available_val);
      if (metric2) metric2.textContent = formatMoney(portfolio.total_reserved_val);
      if (metric3) metric3.textContent = formatMoney(portfolio.total_sold_val);
    } else {
      const p = products.find((x) => String(x.product_id) === String(selectedId));
      if (p) {
        if (pill) pill.innerHTML = '<i class="fa-solid fa-cubes"></i> State B: Unit Quantities';
        if (metric1) metric1.textContent = formatUnits(p.available_qty);
        if (metric2) metric2.textContent = formatUnits(p.reserved_qty);
        if (metric3) metric3.textContent = formatUnits(p.sold_qty);
      }
    }
  }

  // ==========================================================================
  // CHART 2: REAL-TIME EOQ SIMULATION CHART CONTROLLER
  // ==========================================================================
  function initEoqSimulationChart() {
    const ctx = document.getElementById("eoqSimulationCanvas");
    if (!ctx) return;

    eoqSimulationChart = new Chart(ctx, {
      type: "line",
      data: getEoqSimulationChartData(currentSelectedId),
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: "index",
          intersect: false,
        },
        scales: {
          x: {
            ticks: {
              color: "#152d2f",
              font: { weight: "600", size: 10 },
              maxTicksLimit: 12,
            },
            grid: {
              display: false,
            },
          },
          y: {
            title: {
              display: true,
              text: "Inventory Units",
              color: "#152d2f",
              font: { weight: "700" },
            },
            ticks: {
              color: "#152d2f",
              font: { weight: "600", size: 11 },
            },
            grid: {
              color: "rgba(21, 45, 47, 0.15)",
            },
          },
        },
        plugins: {
          legend: {
            position: "top",
            labels: {
              color: "#152d2f",
              font: { weight: "700" },
              usePointStyle: true,
              padding: 12,
            },
          },
          tooltip: {
            callbacks: {
              label: function (context) {
                return `${context.dataset.label}: ${context.raw} units`;
              },
            },
          },
        },
      },
    });

    updateChart2Header(currentSelectedId);
  }

  /**
   * Generates datasets for Chart 2 based on selection state:
   * State A: All products rendered simultaneously
   * State B: Selected product isolated, non-selected grayed out,
   *          overlapping Forecast Simulation with Actual Inventory,
   *          plus ROP and Safety Stock lines.
   */
  function getEoqSimulationChartData(selectedId) {
    if (!selectedId) {
      // STATE A: ALL PRODUCTS SIMULTANEOUSLY
      const datasets = products.map((p) => ({
        label: p.name,
        data: p.sim_curve,
        borderColor: p.color,
        backgroundColor: p.color,
        borderWidth: 2,
        pointRadius: 0,
        tension: 0.15,
      }));

      return {
        labels: dates,
        datasets: datasets,
      };
    } else {
      // STATE B: SINGLE PRODUCT SELECTED - FOCUS + OVERLAPPING FORECAST & ACTUAL
      const target = products.find((p) => String(p.product_id) === String(selectedId));
      if (!target) return { labels: dates, datasets: [] };

      const datasets = [];

      // 1. Grayed-out lines for non-selected products
      products.forEach((p) => {
        if (String(p.product_id) !== String(selectedId)) {
          datasets.push({
            label: `${p.name} (Background)`,
            data: p.sim_curve,
            borderColor: "rgba(180, 195, 190, 0.35)",
            borderWidth: 1,
            pointRadius: 0,
            borderDash: [2, 2],
            tension: 0.1,
          });
        }
      });

      // 2. Forecasted Data (from simulation_eoq)
      datasets.push({
        label: `Forecasted Simulation: ${target.name}`,
        data: target.sim_curve,
        borderColor: COLOR_AVAILABLE,
        backgroundColor: "rgba(16, 185, 129, 0.1)",
        borderWidth: 3,
        pointRadius: 0,
        tension: 0.1,
      });

      // 3. Actual Data (recorded historical progression)
      datasets.push({
        label: `Actual Inventory Curve: ${target.name}`,
        data: target.actual_curve,
        borderColor: COLOR_ACTUAL,
        borderWidth: 2.5,
        borderDash: [5, 4],
        pointRadius: 0,
        tension: 0.15,
      });

      // 4. Horizontal threshold: Reorder Point (ROP)
      datasets.push({
        label: `Reorder Point (ROP = ${target.rop})`,
        data: new Array(dates.length).fill(target.rop),
        borderColor: COLOR_ROP,
        borderWidth: 2,
        borderDash: [6, 4],
        pointRadius: 0,
        fill: false,
      });

      // 5. Horizontal threshold: Safety Stock (SS)
      datasets.push({
        label: `Safety Stock (SS = ${target.ss})`,
        data: new Array(dates.length).fill(target.ss),
        borderColor: COLOR_SS,
        borderWidth: 2,
        borderDash: [4, 4],
        pointRadius: 0,
        fill: false,
      });

      return {
        labels: dates,
        datasets: datasets,
      };
    }
  }

  function updateChart2Header(selectedId) {
    const pill = document.getElementById("chart2ModePill");
    const statEoq = document.getElementById("c2StatEoq");
    const statRop = document.getElementById("c2StatRop");
    const statSs = document.getElementById("c2StatSs");

    if (!selectedId) {
      if (pill) pill.innerHTML = '<i class="fa-solid fa-chart-line"></i> State A: All Products Trajectory';
      if (statEoq) statEoq.textContent = "Multi-Item";
      if (statRop) statRop.textContent = "Dynamic";
      if (statSs) statSs.textContent = "Active";
    } else {
      const p = products.find((x) => String(x.product_id) === String(selectedId));
      if (p) {
        if (pill) pill.innerHTML = `<i class="fa-solid fa-crosshairs"></i> State B: ${p.name.split(" ")[0]} Overlap`;
        if (statEoq) statEoq.textContent = p.eoq + " u";
        if (statRop) statRop.textContent = p.rop + " u";
        if (statSs) statSs.textContent = p.ss + " u";
      }
    }
  }

  // ==========================================================================
  // PRODUCT SELECTION & FILTERING HANDLER
  // ==========================================================================
  function selectProduct(productId) {
    currentSelectedId = productId ? String(productId) : null;

    // 1. Update active highlight on sidebar cards
    const cards = document.querySelectorAll(".product-item-card");
    cards.forEach((card) => {
      const cardId = card.getAttribute("data-product-id");
      if (currentSelectedId) {
        if (cardId === currentSelectedId) {
          card.classList.add("selected");
        } else {
          card.classList.remove("selected");
        }
      } else {
        if (!cardId) {
          card.classList.add("selected");
        } else {
          card.classList.remove("selected");
        }
      }
    });

    // 2. Refresh Chart 1 data and scale formatting
    if (stackedBarChart) {
      stackedBarChart.data = getStackedBarChartData(currentSelectedId);
      stackedBarChart.update();
      updateChart1Header(currentSelectedId);
    }

    // 3. Refresh Chart 2 data (gray out others, overlay forecast & actual)
    if (eoqSimulationChart) {
      eoqSimulationChart.data = getEoqSimulationChartData(currentSelectedId);
      eoqSimulationChart.update();
      updateChart2Header(currentSelectedId);
    }

    // 4. Keep browser URL in sync (clean GET state)
    if (window.history && window.history.pushState) {
      const newUrl = currentSelectedId
        ? `?product_id=${encodeURIComponent(currentSelectedId)}`
        : window.location.pathname;
      window.history.pushState({ productId: currentSelectedId }, "", newUrl);
    }
  }

  // ==========================================================================
  // MODALS (ANALYSIS & MONTH END)
  // ==========================================================================
  function setupModals() {
    const btnAnalysis = document.getElementById("btnAnalysis");
    const btnMonthEnd = document.getElementById("btnMonthEnd");

    const modalAnalysis = document.getElementById("modalAnalysis");
    const modalMonthEnd = document.getElementById("modalMonthEnd");

    const closeAnalysis = document.getElementById("closeAnalysis");
    const closeMonthEnd = document.getElementById("closeMonthEnd");

    if (btnAnalysis && modalAnalysis) {
      btnAnalysis.addEventListener("click", () => {
        modalAnalysis.style.display = "flex";
      });
    }

    if (btnMonthEnd && modalMonthEnd) {
      btnMonthEnd.addEventListener("click", () => {
        modalMonthEnd.style.display = "flex";
      });
    }

    if (closeAnalysis && modalAnalysis) {
      closeAnalysis.addEventListener("click", () => {
        modalAnalysis.style.display = "none";
      });
    }

    if (closeMonthEnd && modalMonthEnd) {
      closeMonthEnd.addEventListener("click", () => {
        modalMonthEnd.style.display = "none";
      });
    }

    // Close on backdrop click
    window.addEventListener("click", (event) => {
      if (modalAnalysis && event.target === modalAnalysis) {
        modalAnalysis.style.display = "none";
      }
      if (modalMonthEnd && event.target === modalMonthEnd) {
        modalMonthEnd.style.display = "none";
      }
    });
  }

  // ==========================================================================
  // INITIALIZATION ON DOM READY
  // ==========================================================================
  document.addEventListener("DOMContentLoaded", function () {
    // Attach click listeners to all product cards in the sidebar
    const cards = document.querySelectorAll(".product-item-card");
    cards.forEach((card) => {
      card.addEventListener("click", function () {
        const pId = this.getAttribute("data-product-id");
        selectProduct(pId);
      });
    });

    // Initialize both dynamic charts
    initStackedBarChart();
    initEoqSimulationChart();

    // Setup action button modals
    setupModals();

    // Initialize Lucide icons if available
    if (window.lucide && typeof window.lucide.createIcons === "function") {
      window.lucide.createIcons();
    }
  });
})();

