from manim import (
    AnimationGroup,
    Arrow,
    BarChart,
    Create,
    DOWN,
    FadeIn,
    FadeOut,
    GrowFromCenter,
    LEFT,
    Line,
    MovingCameraScene,
    RIGHT,
    RoundedRectangle,
    Scene,
    Text,
    UP,
    VGroup,
    Write,
    config,
)


BG = "#111714"
PAPER = "#F4F1E8"
MUTED = "#A9B3AC"
GREEN = "#4FC08D"
BLUE = "#64A7D8"
GOLD = "#E7B85C"
CORAL = "#E8796F"
INK = "#17201B"
FONT = "Segoe UI"


def text(content: str, size: int, color: str = PAPER, weight: str = "NORMAL") -> Text:
    return Text(content, font=FONT, font_size=size, color=color, weight=weight)


def pill(content: str, color: str, width: float = 1.55) -> VGroup:
    box = RoundedRectangle(
        width=width,
        height=0.5,
        corner_radius=0.08,
        stroke_color=color,
        stroke_width=2,
        fill_color=BG,
        fill_opacity=1,
    )
    label = text(content, 20, color, "BOLD")
    return VGroup(box, label)


def section_label(content: str) -> Text:
    return text(content.upper(), 18, GREEN, "BOLD").to_edge(UP, buff=0.45)


def pipeline_node(number: str, title: str, detail: str, color: str) -> VGroup:
    box = RoundedRectangle(
        width=2.2,
        height=1.25,
        corner_radius=0.08,
        stroke_color=color,
        stroke_width=2,
        fill_color="#18211C",
        fill_opacity=1,
    )
    number_text = text(number, 18, color, "BOLD").move_to(box.get_corner(UP + LEFT) + [0.28, -0.22, 0])
    title_text = text(title, 21, PAPER, "BOLD").move_to(box.get_center() + [0, 0.12, 0])
    detail_text = text(detail, 14, MUTED).move_to(box.get_center() + [0, -0.27, 0])
    return VGroup(box, number_text, title_text, detail_text)


class LinkedInRAGAnimation(MovingCameraScene):
    def construct(self) -> None:
        config.background_color = BG
        self.opening()
        self.ingestion()
        self.retrieval()
        self.results()
        self.grounded_answer()

    def opening(self) -> None:
        eyebrow = text("BNM COMPLIANCE ONBOARDING ASSISTANT", 19, GREEN, "BOLD")
        eyebrow.to_edge(UP, buff=0.6)
        title = VGroup(
            text("From regulatory PDFs", 44, PAPER, "BOLD"),
            text("to cited answers", 44, PAPER, "BOLD"),
        ).arrange(DOWN, buff=0.12)
        title.move_to([0, 0.6, 0])
        rule = Line(LEFT * 2.7, RIGHT * 2.7, color="#35423A", stroke_width=2)
        rule.next_to(title, DOWN, buff=0.5)
        tags = VGroup(pill("RMiT", BLUE), pill("AML/CFT", GOLD)).arrange(RIGHT, buff=0.25)
        tags.next_to(rule, DOWN, buff=0.45)
        footer = text("Structure-aware RAG for Malaysian banking regulation", 18, MUTED)
        footer.to_edge(DOWN, buff=0.65)

        self.play(FadeIn(eyebrow, shift=DOWN * 0.15), run_time=0.6)
        self.play(Write(title), run_time=1.2)
        self.play(Create(rule), FadeIn(tags, shift=UP * 0.15), run_time=0.8)
        self.play(FadeIn(footer), run_time=0.5)
        self.wait(1.2)
        self.play(FadeOut(VGroup(eyebrow, title, rule, tags, footer)), run_time=0.6)

    def ingestion(self) -> None:
        heading = section_label("01 / Preserve document structure")
        doc = RoundedRectangle(
            width=5.9,
            height=4.8,
            corner_radius=0.08,
            stroke_color="#56645C",
            stroke_width=2,
            fill_color="#F4F1E8",
            fill_opacity=1,
        ).shift(DOWN * 0.25)
        doc_title = text("11  Cybersecurity Management", 25, INK, "BOLD")
        doc_title.move_to(doc.get_top() + DOWN * 0.55)
        subhead = text("Cybersecurity Operations", 19, "#496B5B", "BOLD")
        subhead.next_to(doc_title, DOWN, buff=0.35).align_to(doc_title, LEFT)

        clauses = VGroup()
        rows = [
            ("S 11.1", "mandatory control", GREEN),
            ("S 11.2", "monitoring obligation", GREEN),
            ("G 11.3", "recommended practice", BLUE),
        ]
        for clause, summary, color in rows:
            tag = text(clause, 18, color, "BOLD")
            body = text(summary, 18, "#34423A")
            row = VGroup(tag, body).arrange(RIGHT, buff=0.45)
            clauses.add(row)
        clauses.arrange(DOWN, buff=0.45, aligned_edge=LEFT)
        clauses.move_to(doc.get_center() + DOWN * 0.35)
        annotations = VGroup(
            text("Clause boundaries", 18, GREEN, "BOLD"),
            text("S / G metadata", 18, BLUE, "BOLD"),
            text("Nested lists retained", 18, GOLD, "BOLD"),
        ).arrange(DOWN, buff=0.18, aligned_edge=LEFT)
        annotations.next_to(doc, DOWN, buff=0.35)

        self.play(FadeIn(heading), GrowFromCenter(doc), run_time=0.8)
        self.play(Write(doc_title), FadeIn(subhead), run_time=0.7)
        self.play(AnimationGroup(*(FadeIn(row, shift=RIGHT * 0.15) for row in clauses), lag_ratio=0.25))
        self.play(FadeIn(annotations, shift=UP * 0.15), run_time=0.6)
        self.wait(1.2)
        self.play(FadeOut(VGroup(heading, doc, doc_title, subhead, clauses, annotations)), run_time=0.6)

    def retrieval(self) -> None:
        heading = section_label("02 / Retrieve, combine, rerank")
        top = VGroup(
            pipeline_node("1", "BM25", "exact terms", GOLD),
            pipeline_node("2", "Qdrant", "dense vectors", BLUE),
        ).arrange(RIGHT, buff=0.7)
        top.move_to([0, 1.25, 0])
        hybrid = pipeline_node("3", "Hybrid", "score fusion", GREEN).move_to([0, -0.55, 0])
        reranker = pipeline_node("4", "Reranker", "top 20 candidates", CORAL).move_to([0, -2.35, 0])

        arrows = VGroup(
            Arrow(top[0].get_bottom(), hybrid.get_top() + LEFT * 0.45, buff=0.12, color=GOLD),
            Arrow(top[1].get_bottom(), hybrid.get_top() + RIGHT * 0.45, buff=0.12, color=BLUE),
            Arrow(hybrid.get_bottom(), reranker.get_top(), buff=0.12, color=GREEN),
        )

        self.play(FadeIn(heading), run_time=0.4)
        self.play(AnimationGroup(*(GrowFromCenter(node) for node in top), lag_ratio=0.25), run_time=0.8)
        self.play(Create(arrows[0]), Create(arrows[1]), GrowFromCenter(hybrid), run_time=0.8)
        self.play(Create(arrows[2]), GrowFromCenter(reranker), run_time=0.8)
        exact = text("Exact clause lookup + semantic matching", 18, MUTED)
        exact.to_edge(DOWN, buff=0.45)
        self.play(FadeIn(exact), run_time=0.5)
        self.wait(1.2)
        self.play(FadeOut(VGroup(heading, top, hybrid, reranker, arrows, exact)), run_time=0.6)

    def results(self) -> None:
        heading = section_label("03 / Measured retrieval quality")
        chart = BarChart(
            values=[85.19, 100],
            bar_names=["BM25", "Reranked"],
            y_range=[0, 100, 20],
            y_length=4.2,
            x_length=5.8,
            bar_colors=[GOLD, GREEN],
            x_axis_config={"font_size": 24, "color": MUTED},
            y_axis_config={"font_size": 18, "color": MUTED},
        ).shift(DOWN * 0.25)
        values = VGroup(
            text("85.19%", 25, GOLD, "BOLD").move_to([-1.45, 1.72, 0]),
            text("100%", 25, GREEN, "BOLD").move_to([1.45, 2.28, 0]),
        )
        caption = text("Top-3 accuracy / 27-case smoke set", 18, MUTED)
        caption.to_edge(DOWN, buff=0.42)

        self.play(FadeIn(heading), run_time=0.4)
        self.play(Create(chart), run_time=1.2)
        self.play(FadeIn(values, shift=UP * 0.15), FadeIn(caption), run_time=0.6)
        self.wait(1.5)
        self.play(FadeOut(VGroup(heading, chart, values, caption)), run_time=0.6)

    def grounded_answer(self) -> None:
        heading = section_label("04 / Generate only from evidence")
        question_box = RoundedRectangle(
            width=6.8,
            height=1.25,
            corner_radius=0.08,
            stroke_color="#536159",
            fill_color="#18211C",
            fill_opacity=1,
        ).move_to([0, 2.15, 0])
        question = text("What should a bank do during a partial outage?", 20, PAPER, "BOLD")
        question.move_to(question_box)

        source = RoundedRectangle(
            width=2.35,
            height=1.8,
            corner_radius=0.08,
            stroke_color=BLUE,
            stroke_width=2,
            fill_color="#18211C",
            fill_opacity=1,
        ).move_to([-2.05, 0.05, 0])
        source_text = VGroup(
            text("SOURCE S1", 16, BLUE, "BOLD"),
            text("RMiT 10.35", 22, PAPER, "BOLD"),
            text("Standard (S)", 16, GREEN),
        ).arrange(DOWN, buff=0.16).move_to(source)

        answer = RoundedRectangle(
            width=3.75,
            height=2.35,
            corner_radius=0.08,
            stroke_color=GREEN,
            stroke_width=2,
            fill_color="#18211C",
            fill_opacity=1,
        ).move_to([1.45, -0.1, 0])
        answer_text = VGroup(
            text("GROUNDED ANSWER", 16, GREEN, "BOLD"),
            text("Respond using the", 18, PAPER),
            text("retrieved obligation", 18, PAPER),
            text("[S1]", 20, BLUE, "BOLD"),
        ).arrange(DOWN, buff=0.12).move_to(answer)
        evidence_arrow = Arrow(source.get_right(), answer.get_left(), buff=0.15, color=GREEN)

        close = VGroup(
            text("Structure-aware.", 24, GOLD, "BOLD"),
            text("Hybrid.", 24, BLUE, "BOLD"),
            text("Grounded.", 24, GREEN, "BOLD"),
        ).arrange(RIGHT, buff=0.28).to_edge(DOWN, buff=0.65)

        self.play(FadeIn(heading), FadeIn(question_box, shift=DOWN * 0.15), Write(question), run_time=0.8)
        self.play(GrowFromCenter(source), FadeIn(source_text), run_time=0.7)
        self.play(Create(evidence_arrow), GrowFromCenter(answer), run_time=0.7)
        self.play(FadeIn(answer_text), run_time=0.6)
        self.play(AnimationGroup(*(FadeIn(item, shift=UP * 0.12) for item in close), lag_ratio=0.22))
        self.wait(2)


class LinkedInCover(Scene):
    def construct(self) -> None:
        config.background_color = BG
        eyebrow = text("PORTFOLIO PROJECT", 20, GREEN, "BOLD").to_edge(UP, buff=0.65)
        title = VGroup(
            text("Building a grounded", 43, PAPER, "BOLD"),
            text("regulatory RAG", 43, PAPER, "BOLD"),
        ).arrange(DOWN, buff=0.12).move_to([0, 1.35, 0])
        subtitle = text("RMiT + AML/CFT", 22, MUTED, "BOLD").next_to(title, DOWN, buff=0.4)

        flow = VGroup(
            pill("PARSE", GOLD, 1.35),
            text("+", 22, MUTED, "BOLD"),
            pill("RETRIEVE", BLUE, 1.7),
            text("+", 22, MUTED, "BOLD"),
            pill("RERANK", CORAL, 1.55),
        ).arrange(RIGHT, buff=0.16).move_to([0, -0.35, 0])

        metric_box = RoundedRectangle(
            width=5.6,
            height=1.35,
            corner_radius=0.08,
            stroke_color=GREEN,
            stroke_width=2,
            fill_color="#18211C",
            fill_opacity=1,
        ).move_to([0, -2.05, 0])
        metric = VGroup(
            text("100%", 34, GREEN, "BOLD"),
            text("top-3 retrieval / 27 cases", 19, PAPER, "BOLD"),
        ).arrange(RIGHT, buff=0.3).move_to(metric_box)
        footer = text("Gemini  |  Qdrant  |  BM25  |  Cross-encoder  |  FastAPI", 16, MUTED)
        footer.to_edge(DOWN, buff=0.55)

        self.add(eyebrow, title, subtitle, flow, metric_box, metric, footer)
