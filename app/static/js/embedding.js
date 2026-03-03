// ── Power BI report embedding logic ──────────────────────────────────────
// This script runs on the Reports page and uses the Power BI JS SDK to embed
// the report returned by the /getembedinfo endpoint.

document.addEventListener("DOMContentLoaded", function () {
  const reportContainer = document.getElementById("report-container");
  const errorContainer  = document.getElementById("error-container");
  const loadingSpinner  = document.getElementById("loading-spinner");

  if (!reportContainer) return;

  // ── Helper to display an error on the page ──────────────────────────────
  function showError(message) {
    if (loadingSpinner) loadingSpinner.classList.add("d-none");
    reportContainer.style.display = "none";
    errorContainer.classList.remove("d-none");
    errorContainer.innerHTML =
      "<strong>Error:</strong> " + message.replace(/\n/g, "<br>");
  }

  // ── Verify the Power BI JS SDK loaded ───────────────────────────────────
  if (!window.powerbi || !window["powerbi-client"]) {
    showError(
      "The Power BI JavaScript SDK failed to load. " +
      "Check your network connection or browser console for details."
    );
    return;
  }

  const powerbiClient = window.powerbi;
  const models        = window["powerbi-client"].models;

  // Bootstrap an empty iframe so the user sees a placeholder immediately
  powerbiClient.bootstrap(reportContainer, { type: "report" });

  // Fetch embed configuration from the Flask backend
  fetch("/getembedinfo")
    .then(function (response) {
      if (!response.ok) {
        return response.json().then(function (err) {
          throw new Error(err.errorMsg || "Unknown error");
        });
      }
      return response.json();
    })
    .then(function (data) {
      // Build the embed configuration
      const reportLoadConfig = {
        type: "report",
        tokenType: models.TokenType.Embed,
        accessToken: data.accessToken,
        embedUrl: data.reportConfig[0].embedUrl,
        settings: {
          panes: {
            filters: { expanded: false, visible: true },
            pageNavigation: { visible: true },
          },
          background: models.BackgroundType.Transparent,
        },
      };

      // Embed the report
      const report = powerbiClient.embed(reportContainer, reportLoadConfig);

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
});
