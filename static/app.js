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

        // Load data for the view
        if (viewName === 'dashboard') { fetchMetrics(); fetchLogs(); }
        else if (viewName === 'processed') loadProcessed();
        else if (viewName === 'failed') loadFailed();
        else if (viewName === 'reports') loadReports();
        else if (viewName === 'config') loadConfig();
    }

    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            switchView(item.dataset.view);
        });
    });

    // Make metric cards clickable
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
            e.preventDefault();
            dropArea.classList.remove('dragover');
            if (e.dataTransfer.files.length) {
                input.files = e.dataTransfer.files;
                input.dispatchEvent(new Event('change'));
            }
        });
        input.addEventListener('change', () => {
            if (input.files.length > 0) {
                textDisplay.textContent = '📄 ' + input.files[0].name;
                checkSubmitStatus();
            }
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
            if (data.success) {
                renderResults(data.data);
                fetchMetrics();
                fetchLogs();
            } else {
                showToast('Pipeline failed: ' + data.error, 'error');
            }
        } catch (error) {
            showToast('Request failed: ' + error, 'error');
        } finally {
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
            animateCount('metric-failed', data.failed);
            animateCount('metric-reports', data.reports);
            animateCount('metric-pending', data.pending);
        } catch (e) { console.error(e); }
    }

    function animateCount(id, target) {
        const el = document.getElementById(id);
        const current = parseInt(el.textContent) || 0;
        if (current === target) return;
        const step = target > current ? 1 : -1;
        const delay = Math.max(20, 300 / Math.abs(target - current));
        let val = current;
        const timer = setInterval(() => {
            val += step;
            el.textContent = val;
            if (val === target) clearInterval(timer);
        }, delay);
    }

    // ─── Logs ───
    async function fetchLogs() {
        try {
            const res = await fetch('/api/logs');
            const data = await res.json();
            document.getElementById('system-logs').textContent = data.logs;
        } catch (e) { console.error(e); }
    }

    // ─── File Listing Helpers ───
    function renderFileList(containerId, files, showDownload = false) {
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
                ${showDownload ? `<a href="/api/reports/download/${encodeURIComponent(f.name)}" class="btn-download" title="Download"><i class="ph ph-download-simple"></i></a>` : ''}
            </div>
        `).join('');
    }

    function getFileIcon(ext) {
        if (['.xlsx', '.xls'].includes(ext)) return 'xls';
        if (['.png', '.jpg', '.jpeg'].includes(ext)) return 'image';
        if (ext === '.pdf') return 'pdf';
        return 'text';
    }

    // ─── Load Pages ───
    window.loadProcessed = async function() {
        const container = document.getElementById('processed-list');
        container.innerHTML = '<div class="loading-row"><div class="spinner-sm"></div> Loading...</div>';
        try {
            const res = await fetch('/api/processed');
            const data = await res.json();
            renderFileList('processed-list', data.files);
        } catch (e) { container.innerHTML = '<div class="empty-state"><p>Failed to load files</p></div>'; }
    };

    window.loadFailed = async function() {
        const container = document.getElementById('failed-list');
        container.innerHTML = '<div class="loading-row"><div class="spinner-sm"></div> Loading...</div>';
        try {
            const res = await fetch('/api/failed');
            const data = await res.json();
            renderFileList('failed-list', data.files);
        } catch (e) { container.innerHTML = '<div class="empty-state"><p>Failed to load files</p></div>'; }
    };

    window.loadReports = async function() {
        const container = document.getElementById('reports-list');
        container.innerHTML = '<div class="loading-row"><div class="spinner-sm"></div> Loading...</div>';
        try {
            const res = await fetch('/api/reports');
            const data = await res.json();
            renderFileList('reports-list', data.files, true);
        } catch (e) { container.innerHTML = '<div class="empty-state"><p>Failed to load reports</p></div>'; }
    };

    async function loadConfig() {
        const container = document.getElementById('config-container');
        container.innerHTML = '<div class="panel config-loading"><div class="spinner-sm"></div> Loading configuration...</div>';
        try {
            const res = await fetch('/api/config');
            const data = await res.json();
            container.innerHTML = renderConfig(data);
        } catch (e) { container.innerHTML = '<div class="panel"><p>Failed to load configuration</p></div>'; }
    }

    function renderConfig(cfg) {
        return `
            <div class="panel config-card">
                <h3><i class="ph ph-grid-four"></i> Data Structure</h3>
                <div class="config-items">
                    ${configRow('Bus Bars', cfg.structure.bus_bars)}
                    ${configRow('Points / Bar', cfg.structure.points_per_bar)}
                    ${configRow('Total Points', cfg.structure.total_points)}
                </div>
            </div>
            <div class="panel config-card">
                <h3><i class="ph ph-funnel"></i> Quality Thresholds</h3>
                <div class="config-items">
                    ${configRow('Rule A (>N)', cfg.thresholds.rule_a_threshold + ' N')}
                    ${configRow('Rule A min %', (cfg.thresholds.rule_a_percentage * 100) + '%')}
                    ${configRow('Rule A min points', cfg.thresholds.min_points_rule_a)}
                    ${configRow('Rule B (≤N)', cfg.thresholds.rule_b_threshold + ' N')}
                    ${configRow('Rule B max/bar', cfg.thresholds.max_rule_b_per_bar)}
                    ${configRow('Rule C (≤N)', cfg.thresholds.rule_c_threshold + ' N')}
                    ${configRow('Rule C max total', cfg.thresholds.max_rule_c_total)}
                    ${configRow('Rule C max/bar', cfg.thresholds.max_rule_c_per_bar)}
                </div>
            </div>
            <div class="panel config-card">
                <h3><i class="ph ph-text-aa"></i> OCR Settings</h3>
                <div class="config-items">
                    ${configRow('Min Confidence', cfg.ocr.min_confidence)}
                    ${configRow('Value Min', cfg.ocr.data_value_min + ' N')}
                    ${configRow('Value Max', cfg.ocr.data_value_max + ' N')}
                </div>
            </div>
            <div class="panel config-card">
                <h3><i class="ph ph-git-diff"></i> Verification</h3>
                <div class="config-items">
                    ${configRow('Tolerance', '±' + cfg.verification.tolerance)}
                    ${configRow('Match Threshold', (cfg.verification.match_threshold * 100) + '%')}
                </div>
            </div>
            <div class="panel config-card">
                <h3><i class="ph ph-hard-drives"></i> System Paths</h3>
                <div class="config-items">
                    ${configRow('Max File Size', cfg.system.max_file_size_mb + ' MB')}
                    ${configRow('Input Dir', cfg.system.input_dir)}
                    ${configRow('Processed Dir', cfg.system.processed_dir)}
                    ${configRow('Failed Dir', cfg.system.failed_dir)}
                    ${configRow('Output Dir', cfg.system.output_dir)}
                    ${configRow('Logs Dir', cfg.system.logs_dir)}
                </div>
            </div>
        `;
    }
    function configRow(label, value) {
        return `<div class="config-row"><span class="cr-label">${label}</span><span class="cr-value">${value}</span></div>`;
    }

    // ─── Refresh All ───
    window.refreshAll = function() {
        fetchMetrics();
        fetchLogs();
        showToast('Dashboard refreshed', 'success');
    };

    // ─── Toast Notifications ───
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
        const text = document.getElementById('decision-text');
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
                tr += '</tr>';
                body += tr;
            });
            body += '</tbody>';
            table.innerHTML += body;
        }

        const report = result.eval_report;
        const rTable = document.getElementById('rule-table');
        rTable.innerHTML = '<tr><th>Rule</th><th>Passed</th><th>Detail</th></tr>';
        if (report && report.metrics) {
            const m = report.metrics;
            const r1 = `<tr><td>Rule A (>0.8)</td><td>${m.rule_A.passed ? '✅ Yes' : '❌ No'}</td><td>${m.rule_A.points_gt_08} / ${m.rule_A.required} req.</td></tr>`;
            const maxB = Math.max(...Object.values(m.rule_B.failures_per_bar).concat([0]));
            const r2 = `<tr><td>Rule B (≤0.35/bar)</td><td>${m.rule_B.passed ? '✅ Yes' : '❌ No'}</td><td>Max per bar: ${maxB} (limit: 2)</td></tr>`;
            const maxC = Math.max(...Object.values(m.rule_C.failures_per_bar).concat([0]));
            const r3 = `<tr><td>Rule C (≤0.1 total)</td><td>${m.rule_C.passed ? '✅ Yes' : '❌ No'}</td><td>Total: ${m.rule_C.total_failures} (limit: 3), Max/bar: ${maxC} (limit: 1)</td></tr>`;
            rTable.innerHTML += r1 + r2 + r3;
        }
    }

    // ─── Init ───
    fetchMetrics();
    fetchLogs();
    setInterval(fetchLogs, 5000);
    setInterval(fetchMetrics, 10000);
});
