# LinkedIn Visuals

The Manim source produces a square portfolio animation and matching cover image.

```powershell
conda run -n bnm-manim manim --format=mp4 manim_rag_visual.py LinkedInRAGAnimation
conda run -n bnm-manim manim -s --format=png manim_rag_visual.py LinkedInCover
```

Rendered files are generated under `media/` and intentionally excluded from Git. The
published MP4 and PNG copies in this directory are the reviewed exports.

Claims in the visual correspond to the committed retrieval smoke set:

- BM25 top-3: 85.19% (23/27)
- Reranked top-3: 100.00% (27/27)
