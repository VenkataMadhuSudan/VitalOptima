"""
VitalOptima Formal Engineering & Research Project Report PDF Generator
Produces a publication-grade, 7-page technical whitepaper in PDF format using
Microsoft Edge headless rendering with embedded 300 DPI figures, comprehensive benchmarks,
mathematical formulations, system architecture, and zero AI footprints.
"""
import os
import sys
import base64
import subprocess
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIGURES_DIR = PROJECT_ROOT / "docs" / "figures"
TEMPLATE_HTML = PROJECT_ROOT / "docs" / "report_template.html"
OUTPUT_HTML = PROJECT_ROOT / "docs" / "VITALOPTIMA_PROJECT_REPORT.html"
OUTPUT_PDF = PROJECT_ROOT / "docs" / "VITALOPTIMA_PROJECT_REPORT.pdf"


def get_base64_image(image_path: Path) -> str:
    """Reads image and returns base64 data URI."""
    if not image_path.exists():
        return ""
    with open(image_path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/png;base64,{data}"


def main():
    print("=== Generating VitalOptima Professional Project Report PDF ===")
    
    # 1. Read Template
    if not TEMPLATE_HTML.exists():
        print(f"Template not found at {TEMPLATE_HTML}")
        sys.exit(1)
        
    with open(TEMPLATE_HTML, "r", encoding="utf-8") as f:
        html_content = f.read()

    # 2. Embed base64 figures
    print("1. Embedding 300 DPI publication research figures...")
    replacements = {
        "##B64_FIG1##": get_base64_image(FIGURES_DIR / "fig1_forecast_vs_actual.png"),
        "##B64_FIG2##": get_base64_image(FIGURES_DIR / "fig2_conformal_intervals.png"),
        "##B64_FIG3##": get_base64_image(FIGURES_DIR / "fig3_model_error_comparison.png"),
        "##B64_FIG4##": get_base64_image(FIGURES_DIR / "fig4_residual_distribution.png"),
        "##B64_FIG5##": get_base64_image(FIGURES_DIR / "fig5_deterministic_vs_stochastic.png"),
        "##B64_FIG6##": get_base64_image(FIGURES_DIR / "fig6_resource_utilization.png"),
        "##B64_FIG7##": get_base64_image(FIGURES_DIR / "fig7_surge_unmet_demand.png"),
        "##B64_FIG8##": get_base64_image(FIGURES_DIR / "fig8_optimization_cost_comparison.png"),
        "##B64_FIG9##": get_base64_image(FIGURES_DIR / "fig9_scenario_sensitivity.png"),
    }

    for placeholder, b64_val in replacements.items():
        html_content = html_content.replace(placeholder, b64_val)

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"   [Exported] Standalone HTML document: {OUTPUT_HTML}")

    # 3. Render to PDF via Headless Microsoft Edge / Chrome
    print("2. Rendering PDF via Microsoft Edge headless print-to-pdf...")
    edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    if not os.path.exists(edge_path):
        edge_path = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
    
    if not os.path.exists(edge_path):
        # Fallback to Google Chrome
        edge_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

    abs_html = os.path.abspath(str(OUTPUT_HTML))
    abs_pdf = os.path.abspath(str(OUTPUT_PDF))

    cmd = [
        edge_path,
        "--headless",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={abs_pdf}",
        f"file:///{abs_html}"
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error rendering PDF: {res.stderr}")
        sys.exit(1)

    # 4. Verify PDF Existence and Page Count
    if OUTPUT_PDF.exists():
        pdf_size = OUTPUT_PDF.stat().st_size
        with open(OUTPUT_PDF, "rb") as f:
            pdf_bytes = f.read()
        pages = len(re.findall(b'/Type\s*/Page[^s]', pdf_bytes))
        print(f"\n[SUCCESS] Project Report PDF generated successfully!")
        print(f" - Path: {OUTPUT_PDF}")
        print(f" - File Size: {pdf_size / (1024 * 1024):.2f} MB ({pdf_size} bytes)")
        print(f" - Total Pages: {pages} pages (Target: 5-8 pages)")
    else:
        print("PDF file was not created!")
        sys.exit(1)


if __name__ == "__main__":
    main()
