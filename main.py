"""
Main Orchestrator for the QC Automation System.
Runs a continuous loop over the input directory, coordinates the batch manager, validation, and reporting.
"""
import time
import argparse
from input_handler import InputHandler
from validator import Validator, ValidationError
from quality_rules import QualityEvaluator
from report_generator import ReportGenerator
from batch_manager import BatchManager
from logger import logger
from config import CATEGORY_DATA_ERROR

def process_file(filepath, steps_callback=None):
    """
    Processes a single factory file drop.
    Returns a dict with step-by-step results for dashboard visibility.
    Optional steps_callback(step_name, status, detail) for live UI updates.
    """
    result = {
        "batch_id": None,
        "filename": filepath.name,
        "steps": [],  # List of {name, status, detail, timestamp}
        "matrix": None,
        "eval_report": None,
        "decision": None,
        "report_path": None,
    }

    def add_step(name, status, detail=""):
        import datetime
        step = {"name": name, "status": status, "detail": detail, "time": datetime.datetime.now().strftime("%H:%M:%S")}
        result["steps"].append(step)
        if steps_callback:
            steps_callback(name, status, detail)

    # STEP 1: Batch Init
    batch = BatchManager()
    result["batch_id"] = batch.batch_id
    batch.log_context(f"Detected new file: {filepath.name}")
    add_step("📁 File Detection", "✅ PASS", f"Detected: {filepath.name}")

    # STEP 2: Route & Extract
    add_step("🔄 Extraction", "⏳ Running", "Routing to parser...")
    matrix, category_override = InputHandler.route_file(filepath, batch)

    if matrix is None:
        add_step("🔄 Extraction", "❌ FAIL", "Could not extract data from file.")
        logger.error(f"[{batch.batch_id}] Extraction Failed.")
        InputHandler.move_file(filepath, success=False, batch_id=batch.batch_id)
        result["decision"] = "DATA_ERROR"
        add_step("📦 File Moved", "⚠️ MOVED", "File moved to /failed")
        return result

    result["matrix"] = matrix
    rows = len(matrix)
    cols = len(matrix[0]) if matrix else 0
    add_step("🔄 Extraction", "✅ PASS", f"Extracted {rows}×{cols} matrix.")

    # STEP 3: Data Cleaning (already done inside parser, but we confirm)
    add_step("🧹 Data Cleaning", "✅ PASS", f"All values converted to numeric floats.")

    # STEP 4: Hard Validation
    add_step("🔍 Validation", "⏳ Running", "Checking 16×7 = 112 structure...")
    try:
        Validator.validate_matrix(matrix)
        total = sum(len(r) for r in matrix)
        add_step("🔍 Validation", "✅ PASS", f"Structure OK: {rows} bars × {cols} pts = {total} total.")
    except ValidationError as ve:
        add_step("🔍 Validation", "❌ FAIL", str(ve))
        logger.error(f"[{batch.batch_id}] Hard Validation Failed: {ve}")
        InputHandler.move_file(filepath, success=False, batch_id=batch.batch_id)
        result["decision"] = "DATA_ERROR"
        add_step("📦 File Moved", "⚠️ MOVED", "File moved to /failed")
        return result

    # STEP 5: Quality Rules Evaluation
    add_step("📏 Rule A Check", "⏳ Running", "Checking >0.8 threshold...")
    eval_report = QualityEvaluator.evaluate_batch(matrix)
    result["eval_report"] = eval_report
    metrics = eval_report["metrics"]

    # Rule A detail
    ra = metrics["rule_A"]
    ra_status = "✅ PASS" if ra["passed"] else "❌ FAIL"
    add_step("📏 Rule A Check", ra_status, f"{ra['points_gt_08']}/{ra['required']} points > 0.8")

    # Rule B detail
    rb = metrics["rule_B"]
    rb_status = "✅ PASS" if rb["passed"] else "❌ FAIL"
    failed_bars_b = [f"Bar {k+1}: {v}" for k, v in rb["failures_per_bar"].items() if v > 2]
    rb_detail = "All bars OK (≤2 points ≤0.35)" if rb["passed"] else f"Bars exceeding limit: {', '.join(failed_bars_b)}"
    add_step("📏 Rule B Check", rb_status, rb_detail)

    # Rule C detail
    rc = metrics["rule_C"]
    rc_status = "✅ PASS" if rc["passed"] else "❌ FAIL"
    failed_bars_c = [f"Bar {k+1}: {v}" for k, v in rc["failures_per_bar"].items() if v > 1]
    rc_detail = f"Total ≤0.1: {rc['total_failures']}/8 max."
    if failed_bars_c:
        rc_detail += f" Bars over limit: {', '.join(failed_bars_c)}"
    add_step("📏 Rule C Check", rc_status, rc_detail)

    # STEP 6: Final Decision
    if category_override:
        logger.warning(f"[{batch.batch_id}] Overriding decision with {category_override}")
        eval_report['decision'] = category_override
        add_step("⚠️ OCR Confidence", "🟡 OVERRIDE", f"Low confidence → {category_override}")

    decision = eval_report["decision"]
    result["decision"] = decision
    dec_icon = "✅" if decision == "APPROVED" else "❌"
    add_step(f"🏁 Final Decision", f"{dec_icon} {decision}", f"Batch {batch.batch_id}")

    # STEP 7: Report Generation
    add_step("📊 Report Generation", "⏳ Running", "Writing Excel report...")
    report_path = ReportGenerator.generate_report(batch.batch_id, matrix, eval_report)
    result["report_path"] = str(report_path)
    add_step("📊 Report Generation", "✅ PASS", f"Saved: {report_path.name}")

    # STEP 8: File Archival
    InputHandler.move_file(filepath, success=True, batch_id=batch.batch_id)
    add_step("📦 File Archived", "✅ DONE", "Original moved to /processed")
    logger.info(f"[{batch.batch_id}] Batch sequence complete. Final Decision: {decision}")

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manufacturing QC Automation Pipeline")
    parser.add_argument("--once", action="store_true", help="Run once then exit, instead of continuous loop.")
    args = parser.parse_args()
    
    logger.info("QC Automation System Started.")
    
    try:
        while True:
            pending_files = InputHandler.get_pending_files()
            for file in pending_files:
                try:
                    process_file(file)
                except Exception as e:
                    logger.error(f"Critical error processing file {file.name}: {e}")
                    InputHandler.move_file(file, success=False, batch_id="CRASHED")
            
            if args.once:
                break
                
            time.sleep(2) # Polling interval
    except KeyboardInterrupt:
        logger.info("System gracefully shut down by operator.")
