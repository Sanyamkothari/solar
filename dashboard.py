"""
Streamlit Dashboard for Factory QC Automation.
Shows EVERY pipeline step visually, with analytics, logs, and manual upload.
"""
import streamlit as st
import pandas as pd
import os
import time
import tempfile
from pathlib import Path
from datetime import datetime

# Adjust Python path
import sys
BASE_DIR = Path(__file__).parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from config import (
    INPUT_DIR, PROCESSED_DIR, FAILED_DIR, OUTPUT_DIR, LOGS_DIR,
    RULE_A_THRESHOLD, RULE_B_THRESHOLD, RULE_C_THRESHOLD,
    MIN_POINTS_RULE_A, MAX_RULE_B_PER_BAR, MAX_RULE_C_TOTAL, MAX_RULE_C_PER_BAR,
    VERIFY_TOLERANCE
)
from input_handler import InputHandler
from main import process_file

st.set_page_config(page_title="Factory QC Dashboard", layout="wide", page_icon="🏭")

# --- CUSTOM CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .metric-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 24px;
        border-radius: 16px;
        border: 1px solid rgba(255,255,255,0.08);
        text-align: center;
        margin-bottom: 8px;
    }
    .metric-card h3 { color: #a0aec0; font-size: 14px; margin-bottom: 4px; font-weight: 600; }
    .metric-value-green { color: #48BB78; font-size: 40px; font-weight: 700; }
    .metric-value-red   { color: #FC8181; font-size: 40px; font-weight: 700; }
    .metric-value-blue  { color: #63B3ED; font-size: 40px; font-weight: 700; }
    .metric-value-amber { color: #F6E05E; font-size: 40px; font-weight: 700; }

    .step-row {
        display: flex;
        align-items: center;
        padding: 10px 16px;
        margin: 4px 0;
        border-radius: 10px;
        font-size: 15px;
        border-left: 4px solid transparent;
    }
    .step-pass   { background: rgba(72,187,120,0.1); border-left-color: #48BB78; }
    .step-fail   { background: rgba(252,129,129,0.1); border-left-color: #FC8181; }
    .step-warn   { background: rgba(246,224,94,0.1); border-left-color: #F6E05E; }
    .step-info   { background: rgba(99,179,237,0.1); border-left-color: #63B3ED; }

    .step-icon   { font-size: 18px; margin-right: 10px; min-width: 28px; text-align: center;}
    .step-name   { font-weight: 600; color: #E2E8F0; min-width: 180px; }
    .step-status { font-weight: 700; min-width: 120px; text-align: center; }
    .step-detail { color: #A0AEC0; font-size: 13px; flex: 1; }
    .step-time   { color: #718096; font-size: 12px; min-width: 70px; text-align: right; }

    .decision-banner {
        text-align: center;
        padding: 20px;
        border-radius: 16px;
        font-size: 28px;
        font-weight: 700;
        margin: 16px 0;
        letter-spacing: 2px;
    }
    .decision-approved { background: linear-gradient(135deg, #22543d, #276749); color: #C6F6D5; }
    .decision-rejected { background: linear-gradient(135deg, #742a2a, #9b2c2c); color: #FED7D7; }
    .decision-error    { background: linear-gradient(135deg, #744210, #975a16); color: #FEFCBF; }
    .decision-review   { background: linear-gradient(135deg, #2a4365, #2b6cb0); color: #BEE3F8; }
</style>
""", unsafe_allow_html=True)

st.title("🏭 Manufacturing QC — Operator Dashboard")
st.caption("Real-time solder point quality control pipeline monitor")

# ─── TOP ANALYTICS ROW ───
st.markdown("---")
c1, c2, c3, c4 = st.columns(4)

processed_count = len(list(PROCESSED_DIR.glob('*')))
failed_count = len(list(FAILED_DIR.glob('*')))
output_count = len(list(OUTPUT_DIR.glob('*')))
pending_count = len(InputHandler.get_pending_files())

with c1:
    st.markdown(f"<div class='metric-card'><h3>✅ Processed</h3><span class='metric-value-green'>{processed_count}</span></div>", unsafe_allow_html=True)
with c2:
    st.markdown(f"<div class='metric-card'><h3>❌ Failed</h3><span class='metric-value-red'>{failed_count}</span></div>", unsafe_allow_html=True)
with c3:
    st.markdown(f"<div class='metric-card'><h3>📊 Reports</h3><span class='metric-value-blue'>{output_count}</span></div>", unsafe_allow_html=True)
with c4:
    st.markdown(f"<div class='metric-card'><h3>⏳ Pending</h3><span class='metric-value-amber'>{pending_count}</span></div>", unsafe_allow_html=True)

# ─── MANUAL UPLOAD & PROCESSING ───
st.markdown("---")
st.header("📂 Run Batch Inspection")
uploaded_file = st.file_uploader("Drop an Image (PNG/JPG) or Excel (XLSX/XLS) file to inspect", type=['png', 'jpg', 'jpeg', 'xlsx', 'xls'])

# Optional: user-provided Excel reference for cross-verification
st.markdown("##### 📎 Optional: Upload Reference Excel for Cross-Verification")
st.caption("If you upload an image above, provide the matching Excel file here to verify OCR accuracy.")
excel_ref_file = st.file_uploader("Reference Excel (XLSX/XLS)", type=['xlsx', 'xls'], key="excel_ref")

if uploaded_file is not None:
    if st.button("🚀  Start QC Pipeline", use_container_width=True, type="primary"):
        # Save file to a temporary directory so the background main.py loop
        # doesn't race to pick it up from input/ at the same time.
        tmp_dir = Path(tempfile.mkdtemp(prefix="qc_upload_"))
        file_path = tmp_dir / uploaded_file.name
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # Save reference Excel if provided
        excel_ref_path = None
        if excel_ref_file is not None:
            excel_ref_path = tmp_dir / f"ref_{excel_ref_file.name}"
            with open(excel_ref_path, "wb") as f:
                f.write(excel_ref_file.getbuffer())

        # ── RUN THE PIPELINE ──
        with st.spinner("Running factory QC pipeline..."):
            try:
                result = process_file(file_path, excel_ref_path=excel_ref_path)
            except Exception as e:
                st.error(f"Critical pipeline failure: {e}")
                result = None

        if result:
            # ── DECISION BANNER ──
            decision = result.get("decision", "UNKNOWN")
            if decision == "APPROVED":
                css = "decision-approved"
                icon = "✅"
            elif decision == "REJECTED":
                css = "decision-rejected"
                icon = "❌"
            elif decision == "DATA_ERROR":
                css = "decision-error"
                icon = "⚠️"
            elif decision == "VERIFICATION_FAILED":
                css = "decision-error"
                icon = "🔀"
            else:
                css = "decision-review"
                icon = "🔍"

            st.markdown(f"<div class='decision-banner {css}'>{icon}  {decision}</div>", unsafe_allow_html=True)
            st.caption(f"Batch ID: `{result.get('batch_id', 'N/A')}`")

            # ── MATRIX SOURCE INFO ──
            matrix_source = result.get("matrix_source")
            if matrix_source:
                st.info(f"📋 **Data Source:** {matrix_source}")

            # ── CROSS-VERIFICATION RESULTS ──
            vr = result.get("verification_report")
            if vr:
                st.subheader("🔀 Cross-Verification: Image vs Excel")
                vc1, vc2, vc3 = st.columns(3)
                with vc1:
                    color = "metric-value-green" if vr["passed"] else "metric-value-red"
                    st.markdown(f"<div class='metric-card'><h3>Match Rate</h3><span class='{color}'>{vr['match_percentage']}%</span></div>", unsafe_allow_html=True)
                with vc2:
                    st.markdown(f"<div class='metric-card'><h3>Matched Cells</h3><span class='metric-value-blue'>{vr['matched_cells']}/{vr['total_cells']}</span></div>", unsafe_allow_html=True)
                with vc3:
                    mismatch_color = "metric-value-green" if vr["mismatch_count"] == 0 else "metric-value-red"
                    st.markdown(f"<div class='metric-card'><h3>Mismatches</h3><span class='{mismatch_color}'>{vr['mismatch_count']}</span></div>", unsafe_allow_html=True)

                if vr["passed"]:
                    st.success(f"✅ Verification PASSED — OCR output matches Excel within ±{vr['tolerance']} tolerance.")
                else:
                    st.error(f"❌ Verification FAILED — {vr['mismatch_count']} cells differ beyond ±{vr['tolerance']} tolerance. Excel data used as ground truth.")

                # Show mismatch details table
                if vr["mismatches"]:
                    st.markdown("**Mismatch Details:**")
                    mismatch_df = pd.DataFrame(vr["mismatches"])
                    mismatch_df.columns = ["Bus Bar", "Point", "Image (OCR)", "Excel (Ref)", "Difference"]
                    st.dataframe(mismatch_df, use_container_width=True, hide_index=True)

            # ── STEP-BY-STEP PIPELINE VIEW ──
            st.subheader("🔗 Pipeline Steps")
            for step in result.get("steps", []):
                status = step["status"]
                if "PASS" in status or "DONE" in status:
                    row_class = "step-pass"
                elif "FAIL" in status:
                    row_class = "step-fail"
                elif "MOVED" in status or "OVERRIDE" in status:
                    row_class = "step-warn"
                else:
                    row_class = "step-info"

                st.markdown(f"""
                <div class='step-row {row_class}'>
                    <span class='step-name'>{step['name']}</span>
                    <span class='step-status'>{step['status']}</span>
                    <span class='step-detail'>{step['detail']}</span>
                    <span class='step-time'>{step['time']}</span>
                </div>
                """, unsafe_allow_html=True)

            # ── DATA MATRIX HEATMAP ──
            matrix = result.get("matrix")
            if matrix:
                st.subheader("🔬 Extracted Data Matrix (16 × 7)")
                df = pd.DataFrame(
                    matrix,
                    columns=[f"P{i+1}" for i in range(len(matrix[0]))],
                    index=[f"Bar {i+1}" for i in range(len(matrix))]
                )

                def color_cells(val):
                    if val <= RULE_C_THRESHOLD:
                        return 'background-color: #742a2a; color: #FED7D7; font-weight: bold;'
                    elif val <= RULE_B_THRESHOLD:
                        return 'background-color: #9b2c2c; color: #FED7D7;'
                    elif val > RULE_A_THRESHOLD:
                        return 'background-color: #22543d; color: #C6F6D5;'
                    else:
                        return 'background-color: #744210; color: #FEFCBF;'

                styled = df.style.map(color_cells).format("{:.3f}")
                st.dataframe(styled, use_container_width=True, height=620)

            # ── RULE SUMMARY TABLE ──
            eval_report = result.get("eval_report")
            if eval_report:
                st.subheader("📋 Rule Summary")
                metrics = eval_report["metrics"]
                summary_data = {
                    "Rule": ["Rule A (>0.8)", "Rule B (≤0.35/bar)", "Rule C (≤0.1 total)"],
                    "Passed": [
                        "✅ Yes" if metrics["rule_A"]["passed"] else "❌ No",
                        "✅ Yes" if metrics["rule_B"]["passed"] else "❌ No",
                        "✅ Yes" if metrics["rule_C"]["passed"] else "❌ No",
                    ],
                    "Detail": [
                        f"{metrics['rule_A']['points_gt_08']} / {metrics['rule_A']['required']} required",
                        f"Max per bar: {max(metrics['rule_B']['failures_per_bar'].values())} (limit: {MAX_RULE_B_PER_BAR})",
                        f"Total: {metrics['rule_C']['total_failures']} (limit: {MAX_RULE_C_TOTAL}), Max/bar: {max(metrics['rule_C']['failures_per_bar'].values())} (limit: {MAX_RULE_C_PER_BAR})",
                    ]
                }
                st.table(pd.DataFrame(summary_data))

            # ── REPORT DOWNLOAD ──
            report_path = result.get("report_path")
            if report_path and os.path.exists(report_path):
                with open(report_path, "rb") as f:
                    st.download_button(
                        "📥  Download Excel Report",
                        data=f.read(),
                        file_name=os.path.basename(report_path),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )

# ─── LIVE LOGS ───
st.markdown("---")
st.header("📜 Live System Logs")
logs = list(LOGS_DIR.glob('*.log'))
if logs:
    latest_log = max(logs, key=os.path.getctime)
    st.caption(f"Source: `{latest_log.name}`")
    try:
        with open(latest_log, "r", encoding="utf-8") as f:
            lines = f.readlines()
        log_text = "".join(lines[-30:])
        st.code(log_text, language="log")
    except Exception as e:
        st.error(f"Could not read log file: {e}")
else:
    st.info("No logs generated yet. Process a file to begin.")

if st.button("🔄 Refresh Dashboard", use_container_width=True):
    st.rerun()
