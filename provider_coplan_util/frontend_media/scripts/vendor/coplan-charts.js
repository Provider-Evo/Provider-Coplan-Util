/**
 * Coplan Chart.js wrapper: draws charts using current theme variables.
 */
(function () {
  function cssVar(name, fallback) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
  }

  function themeColors() {
    return {
      grid: cssVar('--border', '#e8e8e8'),
      tick: cssVar('--text-muted', '#999'),
      line: cssVar('--chart-line', '#2563eb'),
      fill: cssVar('--chart-fill', 'rgba(37, 99, 235, 0.08)'),
    };
  }

  function createUsageLineChart(canvas, labels, values, prevInstance, label) {
    if (prevInstance) prevInstance.destroy();
    if (!canvas || typeof Chart === 'undefined') return null;
    var colors = themeColors();
    return new Chart(canvas, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          label: label || '',
          data: values,
          borderColor: colors.line,
          backgroundColor: colors.fill,
          fill: true,
          tension: 0.3,
          pointRadius: 3,
          pointHoverRadius: 5,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: {
            grid: { display: false },
            ticks: { font: { size: 11 }, color: colors.tick },
          },
          y: {
            beginAtZero: true,
            grid: { color: colors.grid },
            ticks: { font: { size: 11 }, color: colors.tick },
          },
        },
      },
    });
  }

  window.CoplanCharts = { createUsageLineChart: createUsageLineChart };
})();
