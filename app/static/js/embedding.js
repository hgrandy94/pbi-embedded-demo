// ── Power BI report embedding logic ──────────────────────────────────────
// This script runs on the Reports page. It shows a report picker when no
// report_id is in the URL, or embeds the requested report directly.

document.addEventListener("DOMContentLoaded", function () {
  var reportContainer = document.getElementById("report-container");
  var errorContainer  = document.getElementById("error-container");
  var loadingSpinner  = document.getElementById("loading-spinner");
  var reportPicker    = document.getElementById("report-picker");
  var pickerLoading   = document.getElementById("picker-loading");
  var reportViewer    = document.getElementById("report-viewer");
  var viewerTitle     = document.getElementById("report-viewer-title");
  var backBtn         = document.getElementById("back-to-picker");

  if (!reportContainer) return;

  // ── Helpers ──────────────────────────────────────────────────────────────

  function showError(message) {
    if (loadingSpinner) loadingSpinner.classList.add("d-none");
    if (reportViewer) reportViewer.classList.add("d-none");
    if (reportPicker) reportPicker.classList.add("d-none");
    errorContainer.classList.remove("d-none");
    errorContainer.innerHTML =
      "<strong>Error:</strong> " + message.replace(/\n/g, "<br>");
  }

  function showPicker() {
    reportPicker.classList.remove("d-none");
    reportViewer.classList.add("d-none");
    errorContainer.classList.add("d-none");
  }

  function showViewer(name) {
    reportPicker.classList.add("d-none");
    reportViewer.classList.remove("d-none");
    errorContainer.classList.add("d-none");
    if (viewerTitle) viewerTitle.textContent = name || "Report";
  }

  // Back button returns to picker
  if (backBtn) {
    backBtn.addEventListener("click", function () {
      // Reset the embed container
      if (window.powerbi) window.powerbi.reset(reportContainer);
      if (loadingSpinner) loadingSpinner.classList.remove("d-none");
      // Remove report_id from the URL without reload
      history.pushState(null, "", "/reports");
      showPicker();
    });
  }

  // ── Determine if a report_id was requested ──────────────────────────────
  var params = new URLSearchParams(window.location.search);
  var requestedReportId = params.get("report_id") || "";

  if (requestedReportId) {
    embedReport(requestedReportId);
  } else {
    loadReportPicker();
  }

  // ── Report Picker ───────────────────────────────────────────────────────

  function loadReportPicker() {
    showPicker();
    fetch("/api/reports")
      .then(function (r) {
        if (!r.ok) return r.json().then(function (e) { throw new Error(e.errorMsg || "Unknown error"); });
        return r.json();
      })
      .then(function (data) {
        if (pickerLoading) pickerLoading.remove();

        var reports = data.reports || [];

        if (reports.length === 0) {
          reportPicker.innerHTML =
            '<div class="col-12 text-center py-5">' +
            '<i class="bi bi-file-earmark-x" style="font-size:3rem;color:var(--ch-muted);"></i>' +
            '<p class="mt-2" style="color:var(--ch-muted);">No reports are available for your account.</p>' +
            "</div>";
          return;
        }

        // If only one report, auto-embed it
        if (reports.length === 1) {
          history.replaceState(null, "", "/reports?report_id=" + encodeURIComponent(reports[0].id));
          embedReport(reports[0].id, reports[0].name);
          return;
        }

        // Build card grid
        reports.forEach(function (rpt) {
          var col = document.createElement("div");
          col.className = "col-sm-6 col-lg-4";
          col.innerHTML =
            '<a href="/reports?report_id=' + encodeURIComponent(rpt.id) + '" class="text-decoration-none">' +
            '  <div class="ch-card p-4 text-center h-100">' +
            '    <i class="bi bi-graph-up ch-card-icon"></i>' +
            '    <h6 class="fw-bold mt-3 mb-1" style="color:var(--ch-navy);">' + escapeHtml(rpt.name) + "</h6>" +
            '    <small style="color:var(--ch-muted);">Click to view report</small>' +
            "  </div>" +
            "</a>";
          reportPicker.appendChild(col);
        });
      })
      .catch(function (err) {
        showError(err.message);
      });
  }

  // ── Report Embedding ────────────────────────────────────────────────────

  function embedReport(reportId, reportName) {
    showViewer(reportName || "Loading…");

    // Verify the Power BI JS SDK loaded
    if (!window.powerbi || !window["powerbi-client"]) {
      showError(
        "The Power BI JavaScript SDK failed to load. " +
        "Check your network connection or browser console for details."
      );
      return;
    }

    var powerbiClient = window.powerbi;
    var models = window["powerbi-client"].models;

    // Bootstrap an empty iframe placeholder
    powerbiClient.bootstrap(reportContainer, { type: "report" });

    fetch("/getembedinfo?report_id=" + encodeURIComponent(reportId))
      .then(function (response) {
        if (!response.ok) {
          return response.json().then(function (err) {
            throw new Error(err.errorMsg || "Unknown error");
          });
        }
        return response.json();
      })
      .then(function (data) {
        var reportCfg = data.reportConfig[0];
        if (viewerTitle) viewerTitle.textContent = reportCfg.reportName || reportName || "Report";

        var reportLoadConfig = {
          type: "report",
          tokenType: models.TokenType.Embed,
          accessToken: data.accessToken,
          embedUrl: reportCfg.embedUrl,
          settings: {
            panes: {
              filters: { expanded: false, visible: true },
              pageNavigation: { visible: true },
            },
            background: models.BackgroundType.Transparent,
          },
        };

        var report = powerbiClient.embed(reportContainer, reportLoadConfig);

        report.on("loaded", function () {
          console.log("Report loaded successfully.");
          if (loadingSpinner) loadingSpinner.classList.add("d-none");
        });

        report.on("rendered", function () {
          console.log("Report rendered successfully.");
        });

        report.off("error");
        report.on("error", function (event) {
          console.error("Power BI error:", event.detail);
        });
      })
      .catch(function (err) {
        showError(err.message);
      });
  }

  // ── Utility ─────────────────────────────────────────────────────────────

  function escapeHtml(str) {
    var div = document.createElement("div");
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }
});
