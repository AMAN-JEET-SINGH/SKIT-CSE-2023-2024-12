import argparse
from collections import defaultdict
import datetime
import io
import json
import html
from pathlib import Path

import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    KeepTogether,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


# -------------------------------------------------------------
# CONFIGURATION: Institution & Department Details
# -------------------------------------------------------------

COLLEGE_NAME = "Swami Keshvanand Institute of Technology,Management & Gramothan, Jaipur"
DEPARTMENT_NAME = "Department of Computer Science & Engineering"

# -------------------------------------------------------------


def load_static_data(data_path):
    """Load five weekly report datasets and aggregate their student metrics."""
    with open(data_path, encoding="utf-8") as data_file:
        source_data = json.load(data_file)

    required_metadata = ("project_repository", "branch", "weeks")
    missing_metadata = [
        key for key in required_metadata if key not in source_data
    ]
    if missing_metadata:
        raise ValueError(
            "Missing required JSON fields: "
            + ", ".join(missing_metadata)
        )

    if not source_data["weeks"]:
        raise ValueError("The JSON must contain weekly report data.")
    profile_names = [
        student["name"].strip()
        for student in source_data["weeks"][0]["students"]
    ]
    if not profile_names or any(not name for name in profile_names):
        raise ValueError("The JSON must define named student profiles.")
    if len(profile_names) != len(set(profile_names)):
        raise ValueError("Student profile names in the JSON must be unique.")
    if len(source_data["weeks"]) != 5:
        raise ValueError("The JSON must contain exactly five weekly reports.")

    weekly_reports = []
    previous_generated_date = None
    for week in source_data["weeks"]:
        since_date = datetime.date.fromisoformat(week["evaluation_start"])
        generated_date = datetime.date.fromisoformat(week["generated_on"])
        if generated_date < since_date:
            raise ValueError(
                "'generated_on' must be on or after 'evaluation_start'."
            )
        if (generated_date - since_date).days != 7:
            raise ValueError("Each evaluation window must span exactly 7 days.")
        if (
            previous_generated_date is not None
            and since_date != previous_generated_date
        ):
            raise ValueError(
                "Weekly evaluation windows must be consecutive and ordered."
            )
        previous_generated_date = generated_date

        week_students = {
            student["name"].strip(): student
            for student in week["students"]
        }
        if (
            len(week_students) != len(week["students"])
            or set(week_students) != set(profile_names)
        ):
            raise ValueError(
                f"Week ending {week['generated_on']} must include every "
                "profile exactly once."
            )

        students = defaultdict(
            lambda: {
                "commits": 0,
                "added": 0,
                "deleted": 0,
                "active_days": set(),
            }
        )
        timeline_activity = defaultdict(lambda: defaultdict(int))
        student_logs = defaultdict(list)

        for name in profile_names:
            students[name]
            commits = week_students[name].get("commits", [])
            if not commits:
                raise ValueError(
                    f"Week ending {week['generated_on']} has no activity "
                    f"for {name}."
                )
            for commit in commits:
                commit_date = datetime.date.fromisoformat(commit["date"])
                if not since_date <= commit_date <= generated_date:
                    raise ValueError(
                        f"Commit date {commit['date']} for {name} is outside "
                        "the configured evaluation window."
                    )

                added = commit["lines_added"]
                deleted = commit["lines_deleted"]
                if (
                    not isinstance(added, int)
                    or isinstance(added, bool)
                    or not isinstance(deleted, int)
                    or isinstance(deleted, bool)
                ):
                    raise ValueError(
                        f"Commit line counts for {name} must be integers."
                    )

                students[name]["commits"] += 1
                students[name]["added"] += added
                students[name]["deleted"] += deleted
                students[name]["active_days"].add(commit["date"])
                student_logs[name].append(
                    (commit["date"], commit["sha"], commit["message"])
                )
                period_key = commit_date.strftime("%a (%b %d)")
                timeline_activity[period_key][name] += 1

        for logs in student_logs.values():
            logs.sort(key=lambda log: (log[0], log[1]))

        report_data = {
            "project_repository": source_data["project_repository"],
            "branch": source_data["branch"],
            "generated_on": week["generated_on"],
        }
        scope_title = (
            "Last 7 Days (Since "
            f"{since_date.strftime('%Y-%m-%d')})"
        )
        weekly_reports.append(
            (
                report_data,
                students,
                timeline_activity,
                student_logs,
                scope_title,
            )
        )

    return weekly_reports


def create_charts(students, timeline_activity, interval):
    """Generates visual workload and trend charts."""

    fig, (ax1, ax2) = plt.subplots(
        1,
        2,
        figsize=(11, 3.8),
    )

    authors = list(students.keys())
    periods = sorted(timeline_activity.keys())

    # 1. Timeline Line Chart

    if periods and authors:

        for author in authors:

            counts = [
                timeline_activity[p].get(author, 0)
                for p in periods
            ]

            ax1.plot(
                periods,
                counts,
                marker="o",
                linewidth=2,
                label=author,
            )

        ax1.set_title(
            f"Commit Timeline ({interval.capitalize()})",
            fontsize=10,
            fontweight="bold",
        )

        ax1.set_ylabel("Commits")
        ax1.tick_params(axis="x", rotation=30)

        ax1.grid(
            True,
            linestyle="--",
            alpha=0.5,
        )

        ax1.legend(fontsize=8)

    else:
        ax1.text(
            0.5,
            0.5,
            "No commits found in this interval",
            ha="center",
            va="center",
        )

    # 2. Net LOC Bar Chart

    if authors:

        net_loc = [
            students[a]["added"] - students[a]["deleted"]
            for a in authors
        ]

        colors_list = [
            "#4E79A7",
            "#F28E2B",
            "#E15759",
            "#76B7B2",
            "#59A14F",
        ]

        ax2.bar(
            authors,
            net_loc,
            color=colors_list[:len(authors)],
            width=0.45,
        )

        ax2.set_title(
            "Net Lines of Code Written",
            fontsize=10,
            fontweight="bold",
        )

        ax2.set_ylabel("LOC (Added - Deleted)")

        ax2.grid(
            axis="y",
            linestyle="--",
            alpha=0.5,
        )

    else:
        ax2.text(
            0.5,
            0.5,
            "No LOC changes recorded",
            ha="center",
            va="center",
        )

    plt.tight_layout()

    img_buffer = io.BytesIO()

    plt.savefig(
        img_buffer,
        format="png",
        dpi=200,
    )

    plt.close()

    img_buffer.seek(0)

    return Image(
        img_buffer,
        width=500,
        height=170,
    )


def generate_pdf(
    report_data,
    students,
    timeline_activity,
    student_logs,
    scope_title,
    output_path,
):
    """Render one weekly team PDF using only the loaded JSON data."""
    interval = "weekly"
    repo_name = report_data["project_repository"]
    branch_name = report_data["branch"]
    date_stamp = report_data["generated_on"]

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=30,
        bottomMargin=30,
    )

    styles = getSampleStyleSheet()

    college_style = ParagraphStyle(
        "CollegeStyle",
        parent=styles["Heading1"],
        fontSize=13.5,
        leading=17,
        textColor=colors.HexColor("#0F172A"),
        alignment=1,
        spaceAfter=2,
    )

    dept_style = ParagraphStyle(
        "DeptStyle",
        parent=styles["Normal"],
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#475569"),
        alignment=1,
        spaceAfter=6,
    )

    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Heading2"],
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#1A365D"),
        alignment=1,
        spaceAfter=5,
    )

    repo_style = ParagraphStyle(
        "RepoStyle",
        parent=styles["Normal"],
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=3,
    )

    meta_style = ParagraphStyle(
        "MetaStyle",
        parent=styles["Normal"],
        fontSize=8.5,
        textColor=colors.HexColor("#64748B"),
        spaceAfter=8,
    )

    section_style = ParagraphStyle(
        "SectionStyle",
        parent=styles["Heading2"],
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#0F172A"),
        spaceBefore=7,
        spaceAfter=4,
    )

    sub_section_style = ParagraphStyle(
        "SubSectionStyle",
        parent=styles["Heading3"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#2563EB"),
        spaceBefore=5,
        spaceAfter=2,
    )

    msg_style = ParagraphStyle(
        "MsgStyle",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#1E293B"),
    )

    meta_cell_style = ParagraphStyle(
        "MetaCellStyle",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#475569"),
        alignment=1,
    )

    marks_style = ParagraphStyle(
        "MarksStyle",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#0F172A"),
        alignment=1,
    )

    sig_block_style = ParagraphStyle(
        "SigBlockStyle",
        parent=styles["Normal"],
        fontSize=9,
        leading=15,
        textColor=colors.HexColor("#0F172A"),
        alignment=0,
    )

    story = []

    # 1. Header with College & Department Name and Form-3 Title

    story.append(
        Paragraph(
            f"<b>{html.escape(COLLEGE_NAME)}</b>",
            college_style,
        )
    )

    story.append(
        Paragraph(
            f"<b>{html.escape(DEPARTMENT_NAME)}</b>",
            dept_style,
        )
    )

    story.append(
        Paragraph(
            "<u><b>Weekly Progress Report (Form-3)</b></u>",
            title_style,
        )
    )

    story.append(Spacer(1, 3))

    # 2. Metadata (Repo, Branch, Scope, Date)

    story.append(
        Paragraph(
            f"<b>Project Repository:</b> "
            f"<font color='#2563EB'>"
            f"<b>{html.escape(repo_name)}</b>"
            f"</font> &nbsp;|&nbsp; "
            f"<b>Branch:</b> "
            f"<code>{html.escape(branch_name)}</code>",
            repo_style,
        )
    )

    story.append(
        Paragraph(
            f"<b>Evaluation Window:</b> "
            f"{scope_title} &nbsp;|&nbsp; "
            f"<b>Generated On:</b> "
            f"{datetime.date.fromisoformat(date_stamp).strftime('%B %d, %Y')}",
            meta_style,
        )
    )

    # 3. Individual Summary Table

    story.append(
        Paragraph(
            "1. Individual Contribution Breakdown",
            section_style,
        )
    )

    total_commits = sum(
        data["commits"]
        for data in students.values()
    )

    table_data = [
        [
            "Student Name",
            "Commits (%)",
            "Lines Added",
            "Lines Deleted",
            "Net LOC",
            "Active Days",
        ]
    ]

    if students:

        for name, data in students.items():

            pct = (
                data["commits"] / total_commits * 100
                if total_commits > 0
                else 0
            )

            net = data["added"] - data["deleted"]

            table_data.append(
                [
                    html.escape(name),
                    f"{data['commits']} ({pct:.1f}%)",
                    f"+{data['added']:,}",
                    f"-{data['deleted']:,}",
                    f"{net:,}",
                    f"{len(data['active_days'])} days",
                ]
            )

    else:

        table_data.append(
            [
                "No commits found in this period. "
                "Run with 'final' to see all commits.",
                "-",
                "-",
                "-",
                "-",
                "-",
            ]
        )

    table = Table(
        table_data,
        colWidths=[
            120,
            80,
            80,
            80,
            80,
            100,
        ],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#1E293B"),
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.whitesmoke,
                ),
                (
                    "ALIGN",
                    (0, 0),
                    (-1, -1),
                    "CENTER",
                ),
                (
                    "ALIGN",
                    (0, 1),
                    (0, -1),
                    "LEFT",
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold",
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    3.5,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    3.5,
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#CBD5E1"),
                ),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [
                        colors.white,
                        colors.HexColor("#F8FAFC"),
                    ],
                ),
            ]
        )
    )

    story.append(table)
    story.append(Spacer(1, 6))

    # 4. Visual Charts

    story.append(
        Paragraph(
            "2. Visual Trends & Volume",
            section_style,
        )
    )

    chart_image = create_charts(
        students,
        timeline_activity,
        interval,
    )

    story.append(chart_image)
    story.append(Spacer(1, 6))

    # 5. Detailed Commit Logs per Student
    # WITH Vertically Merged Mentor Marks

    story.append(
        Paragraph(
            f"3. Detailed Commit Logs & Mentor Evaluation "
            f"({interval.capitalize()})",
            section_style,
        )
    )

    if not student_logs:

        story.append(
            Paragraph(
                "<i>No commit logs found for this timeframe.</i>",
                styles["Normal"],
            )
        )

    else:

        for student_name, logs in student_logs.items():

            student_section = []

            student_section.append(
                Paragraph(
                    f"<b>Student:</b> "
                    f"{html.escape(student_name)} — "
                    f"<i>{len(logs)} commit(s)</i>",
                    sub_section_style,
                )
            )

            log_table_data = [
                [
                    "Date",
                    "Hash",
                    "Commit Message",
                    "Mentor Marks (/10)",
                ]
            ]

            # Place the clean marking line in the first row

            first_date, first_sha, first_msg = logs[0]

            safe_msg = (
                html.escape(first_msg)
                if first_msg
                else "(No commit message)"
            )

            log_table_data.append(
                [
                    Paragraph(
                        first_date,
                        meta_cell_style,
                    ),
                    Paragraph(
                        f"<code>{first_sha}</code>",
                        meta_cell_style,
                    ),
                    Paragraph(
                        safe_msg,
                        msg_style,
                    ),
                    Paragraph(
                        "<b>_____ / 10</b>",
                        marks_style,
                    ),
                ]
            )

            # Subsequent commit rows have blank placeholder
            # for merged cell

            for date_val, sha_val, msg_val in logs[1:]:

                safe_msg = (
                    html.escape(msg_val)
                    if msg_val
                    else "(No commit message)"
                )

                log_table_data.append(
                    [
                        Paragraph(
                            date_val,
                            meta_cell_style,
                        ),
                        Paragraph(
                            f"<code>{sha_val}</code>",
                            meta_cell_style,
                        ),
                        Paragraph(
                            safe_msg,
                            msg_style,
                        ),
                        "",
                    ]
                )

            num_rows = len(log_table_data)

            log_table = Table(
                log_table_data,
                colWidths=[
                    65,
                    50,
                    335,
                    90,
                ],
            )

            t_style = [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#475569"),
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.whitesmoke,
                ),
                (
                    "ALIGN",
                    (0, 0),
                    (-1, -1),
                    "LEFT",
                ),
                (
                    "ALIGN",
                    (3, 0),
                    (3, -1),
                    "CENTER",
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold",
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    7.5,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    2.5,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    2.5,
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#CBD5E1"),
                ),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (2, -1),
                    [
                        colors.white,
                        colors.HexColor("#F8FAFC"),
                    ],
                ),
                (
                    "SPAN",
                    (3, 1),
                    (3, num_rows - 1),
                ),
                (
                    "VALIGN",
                    (3, 1),
                    (3, num_rows - 1),
                    "MIDDLE",
                ),
                (
                    "BACKGROUND",
                    (3, 1),
                    (3, num_rows - 1),
                    colors.HexColor("#FEF3C7"),
                ),
            ]

            log_table.setStyle(
                TableStyle(t_style)
            )

            student_section.append(log_table)
            student_section.append(Spacer(1, 5))

            story.append(
                KeepTogether(student_section)
            )

    # 6. Symmetrical Signatures

    story.append(Spacer(1, 16))

    mentor_cell = [
        Paragraph(
            "<b>Name:</b> ___________________________",
            sig_block_style,
        ),
        Paragraph(
            "<b>Designation:</b> Project Mentor",
            sig_block_style,
        ),
        Spacer(1, 6),
        Paragraph(
            "<b>Signature:</b> ________________________",
            sig_block_style,
        ),
    ]

    coordinator_cell = [
        Paragraph(
            "<b>Name:</b> ___________________________",
            sig_block_style,
        ),
        Paragraph(
            "<b>Designation:</b> Lab Coordinator",
            sig_block_style,
        ),
        Spacer(1, 6),
        Paragraph(
            "<b>Signature:</b> ________________________",
            sig_block_style,
        ),
    ]

    sig_table = Table(
        [[mentor_cell, coordinator_cell]],
        colWidths=[270, 270],
    )

    sig_table.setStyle(
        TableStyle(
            [
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (0, -1),
                    0,
                ),
                (
                    "LEFTPADDING",
                    (1, 0),
                    (1, -1),
                    40,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
            ]
        )
    )

    story.append(
        KeepTogether(sig_table)
    )

    doc.build(story)

    print(f"\n[SUCCESS] Generated: {output_path}")
    print(
        f" -> Found {len(students)} student(s) "
        f"and {total_commits} total commits."
    )


def generate_reports(data_path, output_dir):
    weekly_reports = load_static_data(data_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    generated_reports = []
    for (
        report_data,
        students,
        timeline_activity,
        student_logs,
        scope_title,
    ) in weekly_reports:
        report_path = output_dir / (
            f"{report_data['project_repository']}_Weekly_Report_"
            f"{report_data['generated_on']}.pdf"
        )
        generate_pdf(
            report_data,
            students,
            timeline_activity,
            student_logs,
            scope_title,
            report_path,
        )
        generated_reports.append(report_path)

    print(
        f"\nGenerated {len(generated_reports)} weekly reports in "
        f"{output_dir}; each report includes all "
        f"{len(weekly_reports[0][1])} students."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Generate five weekly team reports from static JSON data."
        )
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=Path(__file__).with_name("static_report_data.json"),
        help="Path to the static report data JSON file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent / "weekly_reports",
        help="Directory where the five PDF reports will be written.",
    )
    args = parser.parse_args()

    generate_reports(args.data, args.output)