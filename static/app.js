document.addEventListener('DOMContentLoaded', () => {

    // ─── SPA Navigation ───
    const navItems = document.querySelectorAll('.nav-item[data-view]');
    const views = document.querySelectorAll('.view');

    function switchView(viewName) {
        views.forEach(v => v.classList.remove('active'));
        navItems.forEach(n => n.classList.remove('active'));
        const targetView = document.getElementById('view-' + viewName);
        const targetNav = document.getElementById('nav-' + viewName);
        if (targetView) targetView.classList.add('active');
        if (targetNav) targetNav.classList.add('active');

        if (viewName === 'dashboard') { fetchMetrics(); fetchLogs(); }
        else if (viewName === 'processed') loadProcessed();
        else if (viewName === 'reports') { showReportList(); loadReports(); }
        else if (viewName === 'config') loadConfig();
    }

    navItems.forEach(item => {
        item.addEventListener('click', (e) => { e.preventDefault(); switchView(item.dataset.view); });
    });

    document.querySelectorAll('.metric-card[data-view-link]').forEach(card => {
        card.style.cursor = 'pointer';
        card.addEventListener('click', () => switchView(card.dataset.viewLink));
    });

    // ─── Drop Area Setup ───
    function setupDropArea(areaId, inputId, textId) {
        const dropArea = document.getElementById(areaId);
        const input = document.getElementById(inputId);
        const textDisplay = document.getElementById(textId);
        dropArea.addEventListener('click', () => input.click());
        dropArea.addEventListener('dragover', (e) => { e.preventDefault(); dropArea.classList.add('dragover'); });
        dropArea.addEventListener('dragleave', () => dropArea.classList.remove('dragover'));
        dropArea.addEventListener('drop', (e) => {
            e.preventDefault(); dropArea.classList.remove('dragover');
            if (e.dataTransfer.files.length) { input.files = e.dataTransfer.files; input.dispatchEvent(new Event('change')); }
        });
        input.addEventListener('change', () => {
            if (input.files.length > 0) { textDisplay.textContent = '📄 ' + input.files[0].name; checkSubmitStatus(); }
        });
    }
    setupDropArea('main-drop-area', 'main-file', 'main-file-name');
    setupDropArea('ref-drop-area', 'ref-file', 'ref-file-name');

    const mainFile = document.getElementById('main-file');
    const submitBtn = document.getElementById('submit-btn');
    function checkSubmitStatus() { submitBtn.disabled = !(mainFile.files.length > 0); }

    // ─── Upload Form ───
    document.getElementById('upload-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData();
        formData.append('file', mainFile.files[0]);
        const refFile = document.getElementById('ref-file');
        if (refFile.files.length > 0) formData.append('excel_ref', refFile.files[0]);

        document.getElementById('results-panel').classList.remove('hidden');
        document.getElementById('loader').classList.remove('hidden');
        document.getElementById('results-content').classList.add('hidden');
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<div class="spinner-sm"></div> <span>Processing...</span>';

        try {
            const response = await fetch('/api/upload', { method: 'POST', body: formData });
            const data = await response.json();
            if (data.success) { renderResults(data.data); fetchMetrics(); fetchLogs(); }
            else showToast('Pipeline failed: ' + data.error, 'error');
        } catch (error) { showToast('Request failed: ' + error, 'error'); }
        finally {
            document.getElementById('loader').classList.add('hidden');
            document.getElementById('results-content').classList.remove('hidden');
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<span>Start QC Pipeline</span><i class="ph ph-arrow-right"></i>';
            checkSubmitStatus();
        }
    });

    // ─── Metrics ───
    async function fetchMetrics() {
        try {
            const res = await fetch('/api/metrics');
            const data = await res.json();
            animateCount('metric-processed', data.processed);
            animateCount('metric-reports', data.reports);
            animateCount('metric-pending', data.pending);
        } catch (e) { console.error(e); }
    }
    function animateCount(id, target) {
        const el = document.getElementById(id);
        if (!el) return;
        const current = parseInt(el.textContent) || 0;
        if (current === target) return;
        const step = target > current ? 1 : -1;
        const delay = Math.max(20, 300 / Math.abs(target - current));
        let val = current;
        const timer = setInterval(() => { val += step; el.textContent = val; if (val === target) clearInterval(timer); }, delay);
    }

    // ─── Logs ───
    async function fetchLogs() {
        try {
            const res = await fetch('/api/logs');
            const data = await res.json();
            document.getElementById('system-logs').textContent = data.logs;
        } catch (e) { console.error(e); }
    }

    // ─── File Listing ───
    function renderFileList(containerId, files, opts = {}) {
        const container = document.getElementById(containerId);
        if (!files || files.length === 0) {
            container.innerHTML = '<div class="empty-state"><i class="ph ph-folder-dashed"></i><p>No files found</p></div>';
            return;
        }
        container.innerHTML = files.map((f, i) => `
            <div class="file-row" style="animation-delay: ${i * 0.03}s">
                <span class="fr-icon"><i class="ph ph-file-${getFileIcon(f.extension)}"></i></span>
                <span class="fr-name">${f.name}</span>
                <span class="fr-size">${f.size_display}</span>
                <span class="fr-date">${f.modified}</span>
                ${opts.showActions ? `
                    <span class="fr-actions">
                        <button class="btn-icon btn-view-report" data-filename="${f.name}" title="View Graphs"><i class="ph ph-chart-line-up"></i></button>
                        <a href="/api/reports/download/${encodeURIComponent(f.name)}" class="btn-icon" title="Download"><i class="ph ph-download-simple"></i></a>
                    </span>` : ''}
            </div>
        `).join('');

        if (opts.showActions) {
            container.querySelectorAll('.btn-view-report').forEach(btn => {
                btn.addEventListener('click', () => openReportDetail(btn.dataset.filename));
            });
        }
    }
    function getFileIcon(ext) {
        if (['.xlsx', '.xls'].includes(ext)) return 'xls';
        if (['.png', '.jpg', '.jpeg'].includes(ext)) return 'image';
        return 'text';
    }

    // ─── Load Pages ───
    window.loadProcessed = async function() {
        const c = document.getElementById('processed-list');
        c.innerHTML = '<div class="loading-row"><div class="spinner-sm"></div> Loading...</div>';
        try { const r = await fetch('/api/processed'); const d = await r.json(); renderFileList('processed-list', d.files); }
        catch (e) { c.innerHTML = '<div class="empty-state"><p>Failed to load</p></div>'; }
    };

    window.loadReports = async function() {
        const c = document.getElementById('reports-list');
        c.innerHTML = '<div class="loading-row"><div class="spinner-sm"></div> Loading...</div>';
        try { const r = await fetch('/api/reports'); const d = await r.json(); renderFileList('reports-list', d.files, { showActions: true }); }
        catch (e) { c.innerHTML = '<div class="empty-state"><p>Failed to load</p></div>'; }
    };

    // ═══════════════════════════════════════════════════════════
    //                   REPORT DETAIL + GRAPHS
    // ═══════════════════════════════════════════════════════════
    let activeCharts = [];

    function showReportList() {
        document.getElementById('reports-list-panel').classList.remove('hidden');
        document.getElementById('report-detail-panel').classList.add('hidden');
    }

    document.getElementById('btn-back-reports').addEventListener('click', () => {
        showReportList();
        destroyCharts();
    });

    async function openReportDetail(filename) {
        document.getElementById('reports-list-panel').classList.add('hidden');
        const panel = document.getElementById('report-detail-panel');
        panel.classList.remove('hidden');
        panel.innerHTML = '<div class="loading-row" style="min-height:300px"><div class="spinner"></div> Loading report data...</div>';

        try {
            const res = await fetch(`/api/reports/detail/${encodeURIComponent(filename)}`);
            const data = await res.json();
            if (data.error) { panel.innerHTML = `<div class="empty-state"><p>${data.error}</p></div>`; return; }
            renderReportDetail(filename, data);
        } catch (e) { panel.innerHTML = `<div class="empty-state"><p>Failed to load report</p></div>`; }
    }

    function renderReportDetail(filename, data) {
        const panel = document.getElementById('report-detail-panel');
        const decisionClass = data.decision === 'APPROVED' ? 'pass' : data.decision === 'REJECTED' ? 'fail' : 'warn';

        panel.innerHTML = `
            <div class="report-detail-header">
                <button class="btn-back" id="btn-back-reports-inner"><i class="ph ph-arrow-left"></i> Back to Reports</button>
                <div>
                    <h2>${data.batch_id || filename}</h2>
                    <span class="decision-pill decision-pill-${decisionClass}">${data.decision}</span>
                </div>
                <div class="report-detail-actions">
                    <button class="btn-secondary" id="btn-dl-charts-inner"><i class="ph ph-image"></i> Download Charts</button>
                    <a href="/api/reports/download/${encodeURIComponent(filename)}" class="btn-secondary"><i class="ph ph-file-xls"></i> Download Excel</a>
                </div>
            </div>
            <div class="report-stats-row">
                <div class="stat-card"><span class="stat-label">Total Points</span><span class="stat-val">${data.stats.total_points}</span></div>
                <div class="stat-card"><span class="stat-label">Mean</span><span class="stat-val">${data.stats.mean}</span></div>
                <div class="stat-card"><span class="stat-label">Min</span><span class="stat-val">${data.stats.min}</span></div>
                <div class="stat-card"><span class="stat-label">Max</span><span class="stat-val">${data.stats.max}</span></div>
            </div>
            <div class="charts-grid">
                <div class="chart-card"><h3>Average Solder Force per Bus Bar</h3><canvas id="chart-bar-avg"></canvas></div>
                <div class="chart-card"><h3>Value Distribution (Quality Zones)</h3><canvas id="chart-distribution"></canvas></div>
                <div class="chart-card"><h3>Average Force per Point Position</h3><canvas id="chart-point-avg"></canvas></div>
                <div class="chart-card"><h3>Heatmap — All Solder Points</h3><div class="heatmap-container" id="heatmap-container"></div></div>
            </div>
        `;

        document.getElementById('btn-back-reports-inner').addEventListener('click', () => { showReportList(); destroyCharts(); });
        document.getElementById('btn-dl-charts-inner').addEventListener('click', () => downloadAllCharts(data.batch_id || filename));

        destroyCharts();
        createBarAvgChart(data);
        createDistributionChart(data);
        createPointAvgChart(data);
        createHeatmap(data);
    }

    function destroyCharts() { activeCharts.forEach(c => c.destroy()); activeCharts = []; }

    const chartFont = { family: "'Inter', sans-serif" };
    const chartColors = {
        green: 'rgba(40, 167, 69, 0.8)',
        red: 'rgba(220, 53, 69, 0.8)',
        amber: 'rgba(255, 193, 7, 0.8)',
        blue: 'rgba(0, 123, 255, 0.8)',
        purple: 'rgba(108, 92, 231, 0.8)',
    };

    function createBarAvgChart(data) {
        const ctx = document.getElementById('chart-bar-avg');
        if (!ctx) return;
        const colors = data.bar_averages.map(v => v > 0.8 ? chartColors.green : v > 0.35 ? chartColors.amber : chartColors.red);
        const chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.bar_labels,
                datasets: [{ label: 'Avg Force (N)', data: data.bar_averages.map(v => +v.toFixed(4)), backgroundColor: colors, borderRadius: 6, barPercentage: 0.6 }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: false }, tooltip: { callbacks: { label: ctx => ctx.parsed.y + ' N' } } },
                scales: {
                    y: { beginAtZero: true, title: { display: true, text: 'Force (N)', font: chartFont }, grid: { color: '#f0f2f5' } },
                    x: { grid: { display: false } }
                }
            }
        });
        activeCharts.push(chart);
    }

    function createDistributionChart(data) {
        const ctx = document.getElementById('chart-distribution');
        if (!ctx) return;
        const d = data.distribution;
        const chart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['≤0.1 (Fail C)', '0.1–0.35 (Fail B)', '0.35–0.8 (Mid)', '>0.8 (Pass A)'],
                datasets: [{ data: [d['<0.1'], d['0.1-0.35'], d['0.35-0.8'], d['>0.8']],
                    backgroundColor: [chartColors.red, chartColors.amber, chartColors.blue, chartColors.green], borderWidth: 2, borderColor: '#fff' }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { position: 'bottom', labels: { font: chartFont, padding: 16 } } },
                cutout: '55%'
            }
        });
        activeCharts.push(chart);
    }

    function createPointAvgChart(data) {
        const ctx = document.getElementById('chart-point-avg');
        if (!ctx) return;
        const labels = data.point_averages.map((_, i) => `P${i + 1}`);
        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels,
                datasets: [{
                    label: 'Avg Force (N)', data: data.point_averages.map(v => +v.toFixed(4)),
                    borderColor: chartColors.purple, backgroundColor: 'rgba(108, 92, 231, 0.1)',
                    fill: true, tension: 0.4, pointRadius: 5, pointBackgroundColor: chartColors.purple, borderWidth: 2.5
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, title: { display: true, text: 'Force (N)', font: chartFont }, grid: { color: '#f0f2f5' } },
                    x: { grid: { display: false } }
                }
            }
        });
        activeCharts.push(chart);
    }

    function createHeatmap(data) {
        const container = document.getElementById('heatmap-container');
        if (!container || !data.matrix || data.matrix.length === 0) return;

        const allVals = data.matrix.flat().filter(v => v >= 0);
        const maxVal = Math.max(...allVals, 1);

        let html = '<table class="heatmap-table"><thead><tr><th></th>';
        for (let i = 0; i < data.matrix[0].length; i++) html += `<th>P${i + 1}</th>`;
        html += '</tr></thead><tbody>';

        data.matrix.forEach((row, rIdx) => {
            html += `<tr><td class="hm-label">${data.bar_labels[rIdx] || 'Bar ' + (rIdx + 1)}</td>`;
            row.forEach(val => {
                const pct = Math.min(val / maxVal, 1);
                let bg, color;
                if (val <= 0.1) { bg = 'rgba(220,53,69,0.75)'; color = '#fff'; }
                else if (val <= 0.35) { bg = `rgba(255,193,7,${0.4 + pct * 0.4})`; color = '#333'; }
                else if (val > 0.8) { bg = `rgba(40,167,69,${0.4 + pct * 0.5})`; color = '#fff'; }
                else { bg = `rgba(0,123,255,${0.15 + pct * 0.35})`; color = '#333'; }
                html += `<td style="background:${bg};color:${color}" title="${val.toFixed(3)} N">${val.toFixed(2)}</td>`;
            });
            html += '</tr>';
        });
        html += '</tbody></table>';
        container.innerHTML = html;
    }

    function downloadAllCharts(title) {
        const canvases = document.querySelectorAll('.charts-grid canvas');
        canvases.forEach((c, i) => {
            const link = document.createElement('a');
            link.download = `${title}_chart_${i + 1}.png`;
            link.href = c.toDataURL('image/png');
            link.click();
        });
        showToast(`${canvases.length} charts downloaded`, 'success');
    }

    // ═══════════════════════════════════════════════════════════
    //                  EDITABLE CONFIGURATION
    // ═══════════════════════════════════════════════════════════
    let originalConfig = null;
    const saveBtn = document.getElementById('btn-save-config');

    async function loadConfig() {
        const container = document.getElementById('config-container');
        container.innerHTML = '<div class="panel config-loading"><div class="spinner-sm"></div> Loading configuration...</div>';
        try {
            const res = await fetch('/api/config');
            originalConfig = await res.json();
            container.innerHTML = renderEditableConfig(originalConfig);
            attachConfigListeners();
            saveBtn.disabled = true;
        } catch (e) { container.innerHTML = '<div class="panel"><p>Failed to load configuration</p></div>'; }
    }

    function renderEditableConfig(cfg) {
        return `
            <div class="panel config-card">
                <h3><i class="ph ph-grid-four"></i> Data Structure</h3>
                <div class="config-items">
                    ${editRow('structure', 'bus_bars', 'Bus Bars', cfg.structure.bus_bars, 'number')}
                    ${editRow('structure', 'points_per_bar', 'Points / Bar', cfg.structure.points_per_bar, 'number')}
                    <div class="config-row"><span class="cr-label">Total Points <span class="cr-auto">(auto)</span></span><span class="cr-value" id="cfg-total-points">${cfg.structure.total_points}</span></div>
                </div>
            </div>
            <div class="panel config-card">
                <h3><i class="ph ph-funnel"></i> Quality Thresholds</h3>
                <div class="config-items">
                    ${editRow('thresholds', 'rule_a_threshold', 'Rule A (>N)', cfg.thresholds.rule_a_threshold, 'number', '0.01')}
                    ${editRow('thresholds', 'rule_a_percentage', 'Rule A min %', cfg.thresholds.rule_a_percentage, 'number', '0.01')}
                    <div class="config-row"><span class="cr-label">Rule A min points <span class="cr-auto">(auto)</span></span><span class="cr-value" id="cfg-min-points">${cfg.thresholds.min_points_rule_a}</span></div>
                    ${editRow('thresholds', 'rule_b_threshold', 'Rule B (≤N)', cfg.thresholds.rule_b_threshold, 'number', '0.01')}
                    ${editRow('thresholds', 'max_rule_b_per_bar', 'Rule B max/bar', cfg.thresholds.max_rule_b_per_bar, 'number')}
                    ${editRow('thresholds', 'rule_c_threshold', 'Rule C (≤N)', cfg.thresholds.rule_c_threshold, 'number', '0.01')}
                    ${editRow('thresholds', 'max_rule_c_total', 'Rule C max total', cfg.thresholds.max_rule_c_total, 'number')}
                    ${editRow('thresholds', 'max_rule_c_per_bar', 'Rule C max/bar', cfg.thresholds.max_rule_c_per_bar, 'number')}
                </div>
            </div>
            <div class="panel config-card">
                <h3><i class="ph ph-text-aa"></i> OCR Settings</h3>
                <div class="config-items">
                    ${editRow('ocr', 'min_confidence', 'Min Confidence', cfg.ocr.min_confidence, 'number', '0.01')}
                    ${editRow('ocr', 'data_value_min', 'Value Min (N)', cfg.ocr.data_value_min, 'number', '0.1')}
                    ${editRow('ocr', 'data_value_max', 'Value Max (N)', cfg.ocr.data_value_max, 'number', '0.1')}
                </div>
            </div>
            <div class="panel config-card">
                <h3><i class="ph ph-git-diff"></i> Verification</h3>
                <div class="config-items">
                    ${editRow('verification', 'tolerance', 'Tolerance (±)', cfg.verification.tolerance, 'number', '0.001')}
                    ${editRow('verification', 'match_threshold', 'Match Threshold', cfg.verification.match_threshold, 'number', '0.01')}
                </div>
            </div>
        `;
    }

    function editRow(section, key, label, value, type, step) {
        const stepAttr = step ? `step="${step}"` : '';
        return `<div class="config-row">
            <span class="cr-label">${label}</span>
            <input type="${type}" class="config-input" data-section="${section}" data-key="${key}" value="${value}" ${stepAttr}>
        </div>`;
    }

    function attachConfigListeners() {
        document.querySelectorAll('.config-input').forEach(input => {
            input.addEventListener('input', () => {
                saveBtn.disabled = false;
                saveBtn.classList.add('btn-unsaved');
                // Auto-compute derived
                const bars = document.querySelector('[data-section="structure"][data-key="bus_bars"]');
                const ppb = document.querySelector('[data-section="structure"][data-key="points_per_bar"]');
                const pct = document.querySelector('[data-section="thresholds"][data-key="rule_a_percentage"]');
                if (bars && ppb) {
                    const total = (parseInt(bars.value) || 0) * (parseInt(ppb.value) || 0);
                    const el = document.getElementById('cfg-total-points');
                    if (el) el.textContent = total;
                    const mp = document.getElementById('cfg-min-points');
                    if (mp && pct) mp.textContent = Math.floor(total * (parseFloat(pct.value) || 0));
                }
            });
        });
    }

    saveBtn.addEventListener('click', async () => {
        const payload = {};
        document.querySelectorAll('.config-input').forEach(input => {
            const sec = input.dataset.section;
            const key = input.dataset.key;
            if (!payload[sec]) payload[sec] = {};
            payload[sec][key] = input.type === 'number' ? parseFloat(input.value) : input.value;
        });

        saveBtn.disabled = true;
        saveBtn.innerHTML = '<div class="spinner-sm"></div> Saving...';
        try {
            const res = await fetch('/api/config', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
            const data = await res.json();
            if (data.success) {
                showToast('Configuration saved (' + data.updated.length + ' fields)', 'success');
                saveBtn.classList.remove('btn-unsaved');
            } else showToast('Save failed: ' + data.error, 'error');
        } catch (e) { showToast('Save failed: ' + e, 'error'); }
        finally { saveBtn.innerHTML = '<i class="ph ph-floppy-disk"></i> Save Changes'; saveBtn.disabled = true; }
    });

    // ─── Refresh All ───
    window.refreshAll = function() { fetchMetrics(); fetchLogs(); showToast('Dashboard refreshed', 'success'); };

    // ─── Toast ───
    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `<i class="ph ph-${type === 'success' ? 'check-circle' : type === 'error' ? 'x-circle' : 'info'}"></i> ${message}`;
        document.body.appendChild(toast);
        requestAnimationFrame(() => toast.classList.add('show'));
        setTimeout(() => { toast.classList.remove('show'); setTimeout(() => toast.remove(), 300); }, 3000);
    }
    window.showToast = showToast;

    // ─── Results Renderer ───
    function renderResults(result) {
        const decision = result.decision || 'UNKNOWN';
        const banner = document.getElementById('decision-banner');
        banner.className = `decision-banner decision-${decision}`;
        let iconClass = 'warning-circle';
        if (decision === 'APPROVED') iconClass = 'check-circle';
        else if (decision === 'REJECTED') iconClass = 'x-circle';
        else if (decision === 'REVIEW') iconClass = 'magnifying-glass';
        banner.innerHTML = `<i class="ph ph-${iconClass}"></i> <span>${decision}</span>`;

        document.getElementById('matrix-source').textContent = `Data Source: ${result.matrix_source || 'N/A'}`;

        const vr = result.verification_report;
        const vSec = document.getElementById('verification-section');
        if (vr) {
            vSec.classList.remove('hidden');
            document.getElementById('v-match').textContent = vr.match_percentage + '%';
            document.getElementById('v-match').style.color = vr.passed ? 'var(--green)' : 'var(--red)';
            document.getElementById('v-cells').textContent = `${vr.matched_cells}/${vr.total_cells}`;
            document.getElementById('v-mismatch').textContent = vr.mismatch_count;
            document.getElementById('v-mismatch').style.color = vr.mismatch_count === 0 ? 'var(--green)' : 'var(--red)';
        } else { vSec.classList.add('hidden'); }

        const stepsCont = document.getElementById('steps-container');
        stepsCont.innerHTML = '';
        (result.steps || []).forEach((step, i) => {
            const raw = step.status.toUpperCase();
            let cls = 'info';
            if (raw.includes('PASS') || raw.includes('DONE')) cls = 'pass';
            else if (raw.includes('FAIL')) cls = 'fail';
            else if (raw.includes('WARN') || raw.includes('OVERRIDE') || raw.includes('MOVED')) cls = 'warn';
            stepsCont.innerHTML += `
                <div class="step-row ${cls}" style="animation: fadeInUp 0.3s ease ${i * 0.05}s backwards">
                    <span class="step-name">${step.name}</span>
                    <span class="step-status">${step.status}</span>
                    <span class="step-detail">${step.detail}</span>
                    <span class="step-time">${step.time}</span>
                </div>`;
        });

        const matrixObj = result.matrix;
        const table = document.getElementById('matrix-table');
        table.innerHTML = '';
        if (matrixObj && matrixObj.length > 0) {
            let header = '<thead><tr><th>Bar / Point</th>';
            for (let i = 0; i < matrixObj[0].length; i++) header += `<th>P${i + 1}</th>`;
            header += '</tr></thead>';
            table.innerHTML += header;
            let body = '<tbody>';
            matrixObj.forEach((row, rIdx) => {
                let tr = `<tr><td>Bar ${rIdx + 1}</td>`;
                row.forEach(val => {
                    let cls = 'cell-mid', txt = val.toFixed(3);
                    if (val < 0) { cls = 'cell-error'; txt = '❌ ERR'; }
                    else if (val <= 0.1) cls = 'cell-c';
                    else if (val <= 0.35) cls = 'cell-b';
                    else if (val > 0.8) cls = 'cell-a';
                    tr += `<td class="${cls}">${txt}</td>`;
                });
                body += tr + '</tr>';
            });
            table.innerHTML += body + '</tbody>';
        }

        const report = result.eval_report;
        const rTable = document.getElementById('rule-table');
        rTable.innerHTML = '<tr><th>Rule</th><th>Passed</th><th>Detail</th></tr>';
        if (report && report.metrics) {
            const m = report.metrics;
            rTable.innerHTML += `<tr><td>Rule A (>0.8)</td><td>${m.rule_A.passed ? '✅ Yes' : '❌ No'}</td><td>${m.rule_A.points_gt_08} / ${m.rule_A.required} req.</td></tr>`;
            const maxB = Math.max(...Object.values(m.rule_B.failures_per_bar).concat([0]));
            rTable.innerHTML += `<tr><td>Rule B (≤0.35/bar)</td><td>${m.rule_B.passed ? '✅ Yes' : '❌ No'}</td><td>Max per bar: ${maxB} (limit: 2)</td></tr>`;
            const maxC = Math.max(...Object.values(m.rule_C.failures_per_bar).concat([0]));
            rTable.innerHTML += `<tr><td>Rule C (≤0.1 total)</td><td>${m.rule_C.passed ? '✅ Yes' : '❌ No'}</td><td>Total: ${m.rule_C.total_failures} (limit: 3), Max/bar: ${maxC} (limit: 1)</td></tr>`;
        }
    }

    // ─── Init ───
    fetchMetrics();
    fetchLogs();
    setInterval(fetchLogs, 5000);
    setInterval(fetchMetrics, 10000);
});
