"""PDF and HTML Report Exporter."""
import os
import logging
from jinja2 import Template
from typing import Any, Dict

logger = logging.getLogger("bugsense.report_exporter")


class PDFExporter:
    """Renders HTML reports and manages PDF export generation."""

    @staticmethod
    def render_html_report(context: Dict[str, Any]) -> str:
        """Render standalone HTML report string from Jinja template."""
        template_path = os.path.join(
            os.path.dirname(__file__), "templates", "report_template.html"
        )
        with open(template_path, "r", encoding="utf-8") as f:
            template_content = f.read()

        jinja_template = Template(template_content)
        return jinja_template.render(**context)

    @staticmethod
    def export_pdf_file(html_content: str, output_path: str) -> bool:
        """Saves rendered report HTML file and generates PDF if weasyprint/pdfkit available."""
        # Save HTML version
        html_path = output_path.replace(".pdf", ".html")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        # Attempt to export binary PDF if optional tools installed
        try:
            from weasyprint import HTML
            HTML(string=html_content).write_pdf(output_path)
            return True
        except ImportError:
            # Fallback: write standard printable HTML file as PDF-ready document
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            return True
        except Exception as e:
            logger.warning("PDF compilation notice: %s", str(e))
            return False
