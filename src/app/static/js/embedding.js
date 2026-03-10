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

  // Export panel elements
  var exportPanel       = document.getElementById("export-panel");
  var exportToggle      = document.getElementById("export-toggle");
  var exportBody        = document.getElementById("export-body");
  var exportTableSelect = document.getElementById("export-table-select");
  var exportRowLimit    = document.getElementById("export-row-limit");
  var exportDownloadBtn = document.getElementById("export-download-btn");
  var exportCustomToggle  = document.getElementById("export-custom-toggle");
  var exportCustomDax     = document.getElementById("export-custom-dax");
  var exportDaxInput      = document.getElementById("export-dax-input");
  var exportCustomDownload = document.getElementById("export-custom-download");
  var exportStatus        = document.getElementById("export-status");

  // Track the current report ID for export
  var currentReportId = "";

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

  // ── Export panel helpers ─────────────────────────────────────────────────

  function showExportPanel(reportId) {
    currentReportId = reportId;
    if (exportPanel) {
      exportPanel.classList.remove("d-none");
      loadDatasetTables(reportId);
    }
  }

  function hideExportPanel() {
    if (exportPanel) {
      exportPanel.classList.add("d-none");
      exportBody.classList.add("d-none");
      exportToggle.querySelector(".ch-export-chevron").classList.remove("open");
    }
    currentReportId = "";
  }

  function setExportStatus(msg, isError) {
    if (!exportStatus) return;
    exportStatus.classList.remove("d-none");
    exportStatus.className = "mt-2 " + (isError ? "text-danger" : "text-muted");
    exportStatus.style.fontSize = ".82rem";
    exportStatus.textContent = msg;
  }

  function clearExportStatus() {
    if (exportStatus) {
      exportStatus.classList.add("d-none");
      exportStatus.textContent = "";
    }
  }

  function loadDatasetTables(reportId) {
    if (!exportTableSelect) return;
    exportTableSelect.innerHTML = '<option value="">Loading tables…</option>';
    if (exportDownloadBtn) exportDownloadBtn.disabled = true;

    fetch("/api/dataset-tables?report_id=" + encodeURIComponent(reportId))
      .then(function (r) {
        if (!r.ok) return r.json().then(function (e) { throw new Error(e.errorMsg || "Failed to fetch tables"); });
        return r.json();
      })
      .then(function (data) {
        var tables = data.tables || [];
        exportTableSelect.innerHTML = "";
        if (tables.length === 0) {
          exportTableSelect.innerHTML = '<option value="">No tables found</option>';
          return;
        }
        tables.forEach(function (t) {
          var opt = document.createElement("option");
          opt.value = t;
          opt.textContent = t;
          exportTableSelect.appendChild(opt);
        });
        if (exportDownloadBtn) exportDownloadBtn.disabled = false;
      })
      .catch(function (err) {
        exportTableSelect.innerHTML = '<option value="">Error loading tables</option>';
        setExportStatus(err.message, true);
      });
  }

  function triggerExport(daxQuery) {
    clearExportStatus();
    setExportStatus("Exporting…", false);
    if (exportDownloadBtn) exportDownloadBtn.disabled = true;

    fetch("/api/export-data", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ report_id: currentReportId, dax_query: daxQuery }),
    })
      .then(function (r) {
        // Check if the response is CSV or an error JSON
        var ct = r.headers.get("content-type") || "";
        if (ct.indexOf("text/csv") !== -1) {
          return r.blob().then(function (blob) {
            // Trigger file download
            var url = URL.createObjectURL(blob);
            var a = document.createElement("a");
            a.href = url;
            a.download = "export.csv";
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            setExportStatus("Download complete.", false);
          });
        } else {
          return r.json().then(function (data) {
            throw new Error(data.errorMsg || "Export failed.");
          });
        }
      })
      .catch(function (err) {
        setExportStatus(err.message, true);
      })
      .finally(function () {
        if (exportDownloadBtn) exportDownloadBtn.disabled = false;
      });
  }

  // ── Export panel event listeners ────────────────────────────────────────

  if (exportToggle) {
    exportToggle.addEventListener("click", function () {
      var isOpen = !exportBody.classList.contains("d-none");
      exportBody.classList.toggle("d-none", isOpen);
      exportToggle.querySelector(".ch-export-chevron").classList.toggle("open", !isOpen);
    });
  }

  if (exportDownloadBtn) {
    exportDownloadBtn.addEventListener("click", function () {
      var table = exportTableSelect ? exportTableSelect.value : "";
      var limit = exportRowLimit ? parseInt(exportRowLimit.value, 10) || 1000 : 1000;
      if (!table) { setExportStatus("Please select a table.", true); return; }
      var dax = "EVALUATE TOPN(" + limit + ", '" + table + "')";
      triggerExport(dax);
    });
  }

  if (exportCustomToggle) {
    exportCustomToggle.addEventListener("click", function () {
      exportCustomDax.classList.toggle("d-none");
    });
  }

  if (exportCustomDownload) {
    exportCustomDownload.addEventListener("click", function () {
      var dax = exportDaxInput ? exportDaxInput.value.trim() : "";
      if (!dax) { setExportStatus("Enter a DAX query.", true); return; }
      triggerExport(dax);
    });
  }

  // Back button returns to picker
  if (backBtn) {
    backBtn.addEventListener("click", function () {
      // Reset the embed container
      if (window.powerbi) window.powerbi.reset(reportContainer);
      if (loadingSpinner) loadingSpinner.classList.remove("d-none");
      hideExportPanel();
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
          showExportPanel(reportId);
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
