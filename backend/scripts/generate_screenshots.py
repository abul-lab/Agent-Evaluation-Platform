"""Generate release screenshot visual assets for docs/screenshots."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SCREENSHOTS_DIR = Path(__file__).resolve().parent.parent.parent / "docs" / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

# Color Palette Tokens
BG_COLOR = (248, 250, 252)  # #F8FAFC
CARD_BG = (255, 255, 255)  # #FFFFFF
BORDER_COLOR = (226, 232, 240)  # #E2E8F0
TEXT_MAIN = (15, 23, 42)  # #0F172A
TEXT_MUTED = (71, 85, 105)  # #475569
TEXT_SUBTLE = (100, 116, 139)  # #64748B
BRAND_GREEN = (22, 163, 74)  # #16A34A
BRAND_BLUE = (37, 99, 235)  # #2563EB
BRAND_AMBER = (217, 119, 6)  # #D97706
BRAND_ROSE = (220, 38, 38)  # #DC2626
LIGHT_GREEN = (236, 253, 245)
LIGHT_BLUE = (239, 246, 255)
LIGHT_GRAY = (241, 245, 249)

WIDTH, HEIGHT = 1440, 900


def get_fonts():
    try:
        font_title = ImageFont.truetype("arial.ttf", 26)
        font_h2 = ImageFont.truetype("arial.ttf", 18)
        font_body = ImageFont.truetype("arial.ttf", 14)
        font_small = ImageFont.truetype("arial.ttf", 12)
        font_mono = ImageFont.truetype("consola.ttf", 13)
        font_big_num = ImageFont.truetype("arialbd.ttf", 32)
    except Exception:
        font_title = font_h2 = font_body = font_small = font_mono = font_big_num = (
            ImageFont.load_default()
        )
    return font_title, font_h2, font_body, font_small, font_mono, font_big_num


def draw_navbar(draw, active_tab="Overview"):
    font_title, font_h2, font_body, font_small, font_mono, _ = get_fonts()
    # Navbar container
    draw.rectangle([0, 0, WIDTH, 56], fill=CARD_BG, outline=BORDER_COLOR, width=1)

    # AE Logo Badge
    draw.rounded_rectangle(
        [48, 12, 80, 44], radius=6, fill=LIGHT_GREEN, outline=(167, 243, 208), width=1
    )
    draw.text((54, 18), "AE", fill=BRAND_GREEN, font=font_h2)

    # Title
    draw.text((92, 17), "Agent Evaluation Platform", fill=TEXT_MAIN, font=font_h2)

    # Nav items
    tabs = ["Overview", "Traces", "Benchmarks", "Analytics", "Policies", "Workspaces"]
    x = 360
    for tab in tabs:
        w = len(tab) * 9 + 20
        if tab == active_tab:
            draw.rounded_rectangle([x, 14, x + w, 42], radius=6, fill=LIGHT_GRAY)
            draw.text((x + 10, 20), tab, fill=TEXT_MAIN, font=font_body)
        else:
            draw.text((x + 10, 20), tab, fill=TEXT_MUTED, font=font_body)
        x += w + 8

    # Backend status badge
    draw.rounded_rectangle(
        [WIDTH - 210, 14, WIDTH - 48, 42], radius=14, fill=CARD_BG, outline=BORDER_COLOR, width=1
    )
    draw.ellipse([WIDTH - 198, 24, WIDTH - 190, 32], fill=BRAND_GREEN)
    draw.text((WIDTH - 182, 20), "Backend API: Ready", fill=TEXT_MUTED, font=font_small)


def create_base_canvas(active_tab):
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)
    draw_navbar(draw, active_tab)
    return img, draw


def generate_all_screenshots():
    f_title, f_h2, f_body, f_small, f_mono, f_big = get_fonts()

    # 1. Dashboard
    img, d = create_base_canvas("Overview")
    d.text((48, 80), "Evaluation Operations Overview", fill=TEXT_MAIN, font=f_title)
    d.text(
        (48, 116),
        "Continuous evaluation engine auditing agent workflows, tool fidelity, loop lockups, and safety.",
        fill=TEXT_MUTED,
        font=f_body,
    )

    cards = [
        ("Total Ingested Traces", "6", "Active reference corpus"),
        ("Successful Workflows", "3", "50.0% completion rate"),
        ("Audited Tool Calls", "14", "Fidelity checks passed"),
        ("Platform Health", "100%", "All 7 domains active"),
    ]
    for i, (label, val, sub) in enumerate(cards):
        cx = 48 + i * 338
        d.rounded_rectangle(
            [cx, 150, cx + 320, 240], radius=10, fill=CARD_BG, outline=BORDER_COLOR, width=1
        )
        d.text((cx + 18, 166), label.upper(), fill=TEXT_SUBTLE, font=f_small)
        d.text((cx + 18, 186), val, fill=TEXT_MAIN, font=f_big)
        d.text((cx + 18, 222), sub, fill=BRAND_GREEN, font=f_small)

    d.rounded_rectangle(
        [48, 260, 48 + 430, 840], radius=10, fill=CARD_BG, outline=BORDER_COLOR, width=1
    )
    d.text((68, 280), "Ingest Evaluation Trace", fill=TEXT_MAIN, font=f_h2)
    d.rounded_rectangle(
        [68, 320, 48 + 410, 770], radius=8, fill=LIGHT_GRAY, outline=BORDER_COLOR, width=1
    )
    d.text(
        (80, 335),
        '{\n  "session": { "session_id": "..." },\n  "workflow": { "status": "SUCCESS" },\n  "steps": [ ... ]\n}',
        fill=TEXT_MUTED,
        font=f_mono,
    )
    d.rounded_rectangle([68, 785, 48 + 410, 825], radius=6, fill=BRAND_BLUE)
    d.text((190, 797), "Ingest & Evaluate Trace", fill=CARD_BG, font=f_body)

    d.rounded_rectangle(
        [500, 260, WIDTH - 48, 840], radius=10, fill=CARD_BG, outline=BORDER_COLOR, width=1
    )
    d.text((520, 280), "Recent Execution Traces", fill=TEXT_MAIN, font=f_h2)
    d.rectangle([520, 320, WIDTH - 68, 355], fill=LIGHT_GRAY)
    d.text((535, 330), "TRACE ID", fill=TEXT_SUBTLE, font=f_small)
    d.text((740, 330), "STATUS", fill=TEXT_SUBTLE, font=f_small)
    d.text((860, 330), "STEPS", fill=TEXT_SUBTLE, font=f_small)
    d.text((960, 330), "FRAMEWORK", fill=TEXT_SUBTLE, font=f_small)
    d.text((1180, 330), "ACTION", fill=TEXT_SUBTLE, font=f_small)

    rows = [
        ("11111111-1111-4111-8111-111111111111", "SUCCESS", "4", "langgraph", "Audit Run"),
        ("22222222-2222-4222-8222-222222222222", "FAILED", "7", "langchain", "Audit Run"),
        ("33333333-3333-4333-8333-333333333333", "FAILED", "2", "crewai", "Audit Run"),
        ("44444444-4444-4444-8444-444444444444", "SUCCESS", "12", "langgraph", "Audit Run"),
        ("55555555-5555-4555-8555-555555555555", "FAILED", "6", "autogen", "Audit Run"),
        ("66666666-6666-4666-8666-666666666666", "FAILED", "5", "langgraph", "Audit Run"),
    ]
    for idx, (tid, st, steps, fw, act) in enumerate(rows):
        ry = 370 + idx * 70
        d.line([520, ry + 55, WIDTH - 68, ry + 55], fill=BORDER_COLOR, width=1)
        d.text((535, ry + 16), tid[:24] + "...", fill=TEXT_MAIN, font=f_mono)
        color = BRAND_GREEN if st == "SUCCESS" else BRAND_ROSE
        d.rounded_rectangle(
            [740, ry + 12, 820, ry + 36],
            radius=4,
            fill=LIGHT_GREEN if st == "SUCCESS" else (254, 242, 242),
        )
        d.text((752, ry + 16), st, fill=color, font=f_small)
        d.text((875, ry + 16), steps, fill=TEXT_MAIN, font=f_body)
        d.text((960, ry + 16), fw, fill=TEXT_MUTED, font=f_body)
        d.rounded_rectangle(
            [1175, ry + 10, 1270, ry + 38],
            radius=6,
            fill=LIGHT_BLUE,
            outline=(191, 219, 254),
            width=1,
        )
        d.text((1190, ry + 15), act, fill=BRAND_BLUE, font=f_small)

    img.save(SCREENSHOTS_DIR / "dashboard.png")

    # 2. Traces
    img, d = create_base_canvas("Traces")
    d.text((48, 80), "Ingested Traces", fill=TEXT_MAIN, font=f_title)
    d.text(
        (48, 116),
        "Browse, search, and audit canonical execution traces stored in the evaluation repository.",
        fill=TEXT_MUTED,
        font=f_body,
    )
    d.rounded_rectangle(
        [48, 160, 48 + 360, 200], radius=8, fill=CARD_BG, outline=BORDER_COLOR, width=1
    )
    d.text((62, 172), "Filter by trace ID, framework, or status...", fill=TEXT_SUBTLE, font=f_body)
    d.rounded_rectangle(
        [48, 220, WIDTH - 48, 840], radius=10, fill=CARD_BG, outline=BORDER_COLOR, width=1
    )
    d.rectangle([48, 220, WIDTH - 48, 260], fill=LIGHT_GRAY)
    d.text((70, 232), "TRACE IDENTIFIER", fill=TEXT_SUBTLE, font=f_small)
    d.text((380, 232), "WORKFLOW STATUS", fill=TEXT_SUBTLE, font=f_small)
    d.text((580, 232), "STEP COUNT", fill=TEXT_SUBTLE, font=f_small)
    d.text((750, 232), "INGESTED AT", fill=TEXT_SUBTLE, font=f_small)
    d.text((1120, 232), "ACTIONS", fill=TEXT_SUBTLE, font=f_small)
    for idx, (tid, st, steps, _fw, _) in enumerate(rows):
        ry = 275 + idx * 80
        d.line([48, ry + 65, WIDTH - 48, ry + 65], fill=BORDER_COLOR, width=1)
        d.text((70, ry + 18), tid, fill=TEXT_MAIN, font=f_mono)
        color = BRAND_GREEN if st == "SUCCESS" else BRAND_ROSE
        d.rounded_rectangle(
            [380, ry + 14, 460, ry + 38],
            radius=4,
            fill=LIGHT_GREEN if st == "SUCCESS" else (254, 242, 242),
        )
        d.text((392, ry + 18), st, fill=color, font=f_small)
        d.text((595, ry + 18), f"{steps} steps", fill=TEXT_MAIN, font=f_body)
        d.text((750, ry + 18), "2026-11-08 01:00:00 UTC", fill=TEXT_MUTED, font=f_body)
        d.rounded_rectangle([1110, ry + 10, 1230, ry + 42], radius=6, fill=BRAND_GREEN)
        d.text((1130, ry + 18), "Run Evaluation", fill=CARD_BG, font=f_small)
    img.save(SCREENSHOTS_DIR / "traces.png")

    # 3. Evaluation
    img, d = create_base_canvas("Overview")
    d.text((48, 80), "Evaluation Details & Scorecard", fill=TEXT_MAIN, font=f_title)
    d.text(
        (48, 116),
        "Eval ID: 550e8400-e29b-41d4-a716-446655440000 | Candidate run evaluation scorecard",
        fill=TEXT_MUTED,
        font=f_body,
    )

    # Scorecard Hero
    d.rounded_rectangle(
        [48, 150, WIDTH - 48, 290], radius=10, fill=CARD_BG, outline=BORDER_COLOR, width=1
    )
    d.text((70, 175), "OVERALL QUALITY SCORE", fill=TEXT_SUBTLE, font=f_small)
    d.text((70, 200), "94.2 / 100", fill=BRAND_GREEN, font=f_big)
    d.rounded_rectangle(
        [320, 175, 430, 205], radius=14, fill=LIGHT_GREEN, outline=(167, 243, 208), width=1
    )
    d.text((338, 182), "EXCELLENT", fill=BRAND_GREEN, font=f_small)
    d.text(
        (70, 250),
        "Status: COMPLETED | Total Findings: 0 Defects | Risk Classification: EXCELLENT (Release Cleared)",
        fill=TEXT_MUTED,
        font=f_body,
    )

    # Domain breakdown cards
    domains = [
        ("Task Quality", "95.0", "PASS"),
        ("Tool Fidelity", "92.5", "PASS"),
        ("Workflow Structure", "96.0", "PASS"),
        ("Reliability", "98.0", "PASS"),
        ("Safety & Secrets", "100.0", "PASS"),
        ("Budget & Latency", "90.0", "PASS"),
        ("Cost Efficiency", "88.0", "PASS"),
    ]
    for i, (dom, sc, st) in enumerate(domains):
        dx = 48 + i * 192
        d.rounded_rectangle(
            [dx, 310, dx + 180, 430], radius=8, fill=CARD_BG, outline=BORDER_COLOR, width=1
        )
        d.text((dx + 12, 325), dom, fill=TEXT_MAIN, font=f_small)
        d.text((dx + 12, 355), f"{sc} pts", fill=TEXT_MAIN, font=f_h2)
        d.rounded_rectangle([dx + 12, 395, dx + 70, 418], radius=4, fill=LIGHT_GREEN)
        d.text((dx + 24, 400), st, fill=BRAND_GREEN, font=f_small)

    # Findings & Export
    d.rounded_rectangle(
        [48, 455, WIDTH - 48, 840], radius=10, fill=CARD_BG, outline=BORDER_COLOR, width=1
    )
    d.text((70, 475), "Evaluation Findings & Defects (0 Breaches)", fill=TEXT_MAIN, font=f_h2)
    d.rounded_rectangle(
        [70, 520, WIDTH - 70, 620], radius=8, fill=LIGHT_GREEN, outline=(167, 243, 208), width=1
    )
    d.text(
        (95, 560),
        "✓ Zero defects detected. Agent execution satisfies all deterministic quality, tool, and safety checks.",
        fill=BRAND_GREEN,
        font=f_h2,
    )
    img.save(SCREENSHOTS_DIR / "evaluation.png")

    # 4. Workflow Graph
    img, d = create_base_canvas("Overview")
    d.text((48, 80), "Workflow Execution Graph (DAG)", fill=TEXT_MAIN, font=f_title)
    d.text(
        (48, 116),
        "Topological step execution graph with retry paths, cycle detection, and tool inspection.",
        fill=TEXT_MUTED,
        font=f_body,
    )

    # Graph canvas
    d.rounded_rectangle(
        [48, 150, WIDTH - 48, 840], radius=10, fill=(248, 250, 252), outline=BORDER_COLOR, width=1
    )
    # Draw DAG Nodes
    nodes = [
        (120, 360, "step_0", "Init / Ingest", "SUCCESS"),
        (420, 360, "step_1", "Fetch Order", "SUCCESS"),
        (720, 360, "step_2", "Refund Check", "SUCCESS"),
        (1020, 360, "step_3", "Send Response", "SUCCESS"),
    ]
    for nx, ny, sid, label, st in nodes:
        d.rounded_rectangle(
            [nx, ny, nx + 200, ny + 120], radius=10, fill=CARD_BG, outline=BORDER_COLOR, width=2
        )
        d.text((nx + 16, ny + 16), sid, fill=TEXT_SUBTLE, font=f_small)
        d.text((nx + 16, ny + 40), label, fill=TEXT_MAIN, font=f_h2)
        d.rounded_rectangle([nx + 16, ny + 76, nx + 85, ny + 102], radius=4, fill=LIGHT_GREEN)
        d.text((nx + 26, ny + 82), st, fill=BRAND_GREEN, font=f_small)
        # Arrow to next
        if nx < 1000:
            d.line([nx + 200, ny + 60, nx + 300, ny + 60], fill=BRAND_BLUE, width=3)
            d.polygon(
                [(nx + 300, ny + 60), (nx + 288, ny + 54), (nx + 288, ny + 66)], fill=BRAND_BLUE
            )

    img.save(SCREENSHOTS_DIR / "workflow_graph.png")

    # 5. Benchmarks
    img, d = create_base_canvas("Benchmarks")
    d.text((48, 80), "Evaluation Benchmarking & Comparison", fill=TEXT_MAIN, font=f_title)
    d.text(
        (48, 116),
        "Head-to-head evaluation comparison, score deltas, and statistical leaderboard.",
        fill=TEXT_MUTED,
        font=f_body,
    )

    # Comparison card
    d.rounded_rectangle(
        [48, 150, WIDTH - 48, 480], radius=10, fill=CARD_BG, outline=BORDER_COLOR, width=1
    )
    d.text((70, 175), "Head-to-Head Evaluation Run Comparator", fill=TEXT_MAIN, font=f_h2)
    d.rounded_rectangle(
        [70, 220, 520, 440], radius=8, fill=LIGHT_GRAY, outline=BORDER_COLOR, width=1
    )
    d.text((90, 240), "BASELINE RUN (v1.0)", fill=TEXT_SUBTLE, font=f_small)
    d.text((90, 270), "Score: 78.5 pts | Risk: WATCH", fill=TEXT_MAIN, font=f_h2)
    d.text((90, 310), "Defects: 2 High Findings (Retry Storm)", fill=BRAND_AMBER, font=f_body)

    d.rounded_rectangle(
        [560, 220, 1010, 440], radius=8, fill=LIGHT_GRAY, outline=BORDER_COLOR, width=1
    )
    d.text((580, 240), "CANDIDATE RUN (v1.1-rc)", fill=TEXT_SUBTLE, font=f_small)
    d.text((580, 270), "Score: 94.2 pts | Risk: EXCELLENT", fill=TEXT_MAIN, font=f_h2)
    d.text((580, 310), "Defects: 0 Breaches (Clean Execution)", fill=BRAND_GREEN, font=f_body)

    d.rounded_rectangle(
        [1050, 220, WIDTH - 70, 440], radius=8, fill=LIGHT_GREEN, outline=(167, 243, 208), width=1
    )
    d.text((1070, 240), "DELTA VERDICT", fill=TEXT_SUBTLE, font=f_small)
    d.text((1070, 270), "+15.7 pts", fill=BRAND_GREEN, font=f_big)
    d.text((1070, 320), "Risk Tier: WATCH -> EXCELLENT", fill=BRAND_GREEN, font=f_body)
    d.text((1070, 350), "Defects: -2 Resolved", fill=BRAND_GREEN, font=f_body)
    d.text((1070, 380), "Verdict: APPROVED FOR RELEASE", fill=BRAND_GREEN, font=f_h2)

    img.save(SCREENSHOTS_DIR / "benchmarks.png")

    # 6. Analytics
    img, d = create_base_canvas("Analytics")
    d.text((48, 80), "Longitudinal Quality Analytics", fill=TEXT_MAIN, font=f_title)
    d.text(
        (48, 116),
        "Historical quality trajectories, daily evaluation volume, and recurring defect frequencies.",
        fill=TEXT_MUTED,
        font=f_body,
    )

    # 2 Charts side by side
    d.rounded_rectangle([48, 150, 700, 520], radius=10, fill=CARD_BG, outline=BORDER_COLOR, width=1)
    d.text((70, 175), "Average Quality Score Trajectory (30 Days)", fill=TEXT_MAIN, font=f_h2)
    d.line([90, 460, 660, 460], fill=BORDER_COLOR, width=2)
    d.line([90, 240, 90, 460], fill=BORDER_COLOR, width=2)
    # Simulated Trend Line
    trend_pts = [(90 + i * 38, 420 - int((i**1.1) * 8.5)) for i in range(15)]
    for i in range(len(trend_pts) - 1):
        d.line([trend_pts[i], trend_pts[i + 1]], fill=BRAND_GREEN, width=3)
        d.ellipse(
            [trend_pts[i][0] - 3, trend_pts[i][1] - 3, trend_pts[i][0] + 3, trend_pts[i][1] + 3],
            fill=BRAND_GREEN,
        )

    d.rounded_rectangle(
        [730, 150, WIDTH - 48, 520], radius=10, fill=CARD_BG, outline=BORDER_COLOR, width=1
    )
    d.text((750, 175), "Daily Evaluation Throughput Volume", fill=TEXT_MAIN, font=f_h2)
    d.line([770, 460, 1340, 460], fill=BORDER_COLOR, width=2)
    for b in range(14):
        bx = 790 + b * 38
        bh = 40 + (b * 13) % 180
        d.rectangle([bx, 460 - bh, bx + 24, 460], fill=BRAND_BLUE)

    img.save(SCREENSHOTS_DIR / "analytics.png")

    # 7. Policies
    img, d = create_base_canvas("Policies")
    d.text((48, 80), "Evaluation Policies & Governance", fill=TEXT_MAIN, font=f_title)
    d.text(
        (48, 116),
        "Manage release gating criteria, enforce score floors, and audit evaluations.",
        fill=TEXT_MUTED,
        font=f_body,
    )

    # Active policy card
    d.rounded_rectangle(
        [48, 160, 48 + 420, 480], radius=10, fill=CARD_BG, outline=BORDER_COLOR, width=1
    )
    d.text((70, 185), "Standard Governance Policy (Default)", fill=TEXT_MAIN, font=f_h2)
    d.text((70, 215), "Production governance policy threshold profile.", fill=TEXT_MUTED, font=f_body)
    d.rounded_rectangle(
        [70, 250, 48 + 390, 400], radius=8, fill=LIGHT_GRAY, outline=BORDER_COLOR, width=1
    )
    d.text((85, 268), "Min Overall Score:       80.0 pts", fill=TEXT_MAIN, font=f_mono)
    d.text((85, 298), "Min Safety Score:        90.0 pts", fill=TEXT_MAIN, font=f_mono)
    d.text((85, 328), "Disallowed Risk Tiers:   CRITICAL, POOR", fill=BRAND_ROSE, font=f_mono)
    d.text((85, 358), "Prohibited Codes:        SECRET_EXPOSURE", fill=BRAND_AMBER, font=f_mono)

    # Audit Console
    d.rounded_rectangle(
        [48, 510, WIDTH - 48, 840], radius=10, fill=CARD_BG, outline=BORDER_COLOR, width=1
    )
    d.text((70, 535), "Evaluation Governance Audit Console", fill=TEXT_MAIN, font=f_h2)
    d.rounded_rectangle(
        [70, 580, WIDTH - 70, 780], radius=8, fill=LIGHT_GREEN, outline=(167, 243, 208), width=1
    )
    d.text((95, 605), "AUDIT VERDICT: APPROVED — Release Cleared", fill=BRAND_GREEN, font=f_title)
    d.text(
        (95, 650),
        "Evaluation ID: 550e8400-e29b-41d4-a716-446655440000 | Policy: Standard Governance Policy",
        fill=TEXT_MAIN,
        font=f_body,
    )
    d.text(
        (95, 680),
        "Overall Score: 94.2 pts | Risk Tier: EXCELLENT | Policy Violations: 0 Breaches",
        fill=TEXT_MUTED,
        font=f_body,
    )
    img.save(SCREENSHOTS_DIR / "policies.png")

    # 8. Workspaces
    img, d = create_base_canvas("Workspaces")
    d.text((48, 80), "Team & Organization Workspaces", fill=TEXT_MAIN, font=f_title)
    d.text(
        (48, 116),
        "Multi-tenant workspace isolation boundaries, RBAC permissions, and team audit logs.",
        fill=TEXT_MUTED,
        font=f_body,
    )

    # Left: Workspaces list
    d.rounded_rectangle(
        [48, 160, 48 + 380, 840], radius=10, fill=CARD_BG, outline=BORDER_COLOR, width=1
    )
    d.text((70, 185), "WORKSPACES (2)", fill=TEXT_SUBTLE, font=f_small)
    d.rounded_rectangle(
        [70, 215, 48 + 350, 310], radius=8, fill=LIGHT_GREEN, outline=BRAND_GREEN, width=1
    )
    d.text((85, 235), "Default Team Workspace", fill=TEXT_MAIN, font=f_h2)
    d.text((85, 265), "Slug: default | Members: 3", fill=TEXT_MUTED, font=f_small)

    d.rounded_rectangle(
        [70, 325, 48 + 350, 420], radius=8, fill=LIGHT_GRAY, outline=BORDER_COLOR, width=1
    )
    d.text((85, 345), "Swarm Robotics Team", fill=TEXT_MAIN, font=f_h2)
    d.text((85, 375), "Slug: swarm-robotics | Members: 2", fill=TEXT_MUTED, font=f_small)

    # Right: Active workspace details (Members + Audit Log)
    d.rounded_rectangle(
        [460, 160, WIDTH - 48, 840], radius=10, fill=CARD_BG, outline=BORDER_COLOR, width=1
    )
    d.text((485, 185), "Active Workspace: Default Team Workspace", fill=TEXT_MAIN, font=f_h2)

    # Members table
    d.text((485, 230), "TEAM MEMBERS (3)", fill=TEXT_SUBTLE, font=f_small)
    members = [
        ("lead.architect@example.com", "ADMIN", BRAND_GREEN),
        ("reliability.engineer@example.com", "ENGINEER", BRAND_BLUE),
        ("compliance.officer@example.com", "VIEWER", TEXT_MUTED),
    ]
    for idx, (email, role, col) in enumerate(members):
        my = 260 + idx * 55
        d.line([485, my + 45, WIDTH - 70, my + 45], fill=BORDER_COLOR, width=1)
        d.text((485, my + 12), email, fill=TEXT_MAIN, font=f_mono)
        d.rounded_rectangle([1120, my + 8, 1220, my + 36], radius=4, fill=LIGHT_GRAY)
        d.text((1140, my + 14), role, fill=col, font=f_small)

    d.text(
        (485, 450), "WORKSPACE ACTIVITY AUDIT TRAIL (IMMUTABLE LOG)", fill=TEXT_SUBTLE, font=f_small
    )
    audit_logs = [
        ("POLICY_PROFILE_CREATED", "lead.architect@example.com", "12:10:04 UTC"),
        ("MEMBER_ROLE_UPDATED", "lead.architect@example.com", "11:45:22 UTC"),
        ("EVALUATION_AUDIT_EXECUTED", "reliability.engineer@example.com", "10:30:15 UTC"),
        ("WORKSPACE_CREATED", "system_bootstrap", "09:00:00 UTC"),
    ]
    for idx, (action, actor, tm) in enumerate(audit_logs):
        ly = 480 + idx * 60
        d.rounded_rectangle(
            [485, ly, WIDTH - 70, ly + 50], radius=6, fill=LIGHT_GRAY, outline=BORDER_COLOR, width=1
        )
        d.text((505, ly + 14), action, fill=BRAND_GREEN, font=f_mono)
        d.text((850, ly + 16), f"Actor: {actor}", fill=TEXT_MUTED, font=f_small)
        d.text((WIDTH - 190, ly + 16), tm, fill=TEXT_SUBTLE, font=f_mono)

    img.save(SCREENSHOTS_DIR / "workspaces.png")

    print(f"Successfully generated all 8 screenshots in {SCREENSHOTS_DIR}")


if __name__ == "__main__":
    generate_all_screenshots()
