"""Create a tiny synthetic example. No real scholarly articles or API calls."""
from pathlib import Path
import pymupdf

root = Path(__file__).resolve().parent
(root / "papers").mkdir(exist_ok=True)
pdf = pymupdf.open()
page = pdf.new_page()
page.insert_textbox(pymupdf.Rect(50, 80, 540, 250),
    "A synthetic example paper (not real research)\n\n"
    "We studied eight synthetic observations. In this artificial sample,"
    " the intervention was associated with an improvement in the measured outcome.\n\n"
    "The study was observational; it cannot establish a causal benefit.", fontsize=12)
pdf.save(root / "papers" / "demo2026.pdf")
pdf.close()
(root / "manuscript.tex").write_text(r"""\documentclass{article}
\begin{document}
The intervention is associated with improved outcomes in a small sample \citep{demo2026}.
The intervention causally improves outcomes for everyone \citep{demo2026}.
\end{document}
""", encoding="utf-8")
(root / "references.bib").write_text(r"""@article{demo2026,
  title={A Synthetic Example Paper},
  author={Example, Taylor},
  year={2026},
  url={https://example.org/synthetic-paper}
}
""", encoding="utf-8")
print("Created a purely synthetic demo in demo/")
