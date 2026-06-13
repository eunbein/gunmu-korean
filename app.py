import base64
import json
import random
from collections import defaultdict
from pathlib import Path

import fitz
import streamlit as st

st.set_page_config(
    page_title="군무원 9급 국어 기출",
    page_icon="📚",
    layout="wide",
)

ROOT = Path(__file__).parent


@st.cache_data
def load_items():
    return json.loads(
        (ROOT / "questions.json").read_text(encoding="utf-8")
    )


@st.cache_resource
def load_pdf(year):
    return fitz.open(ROOT / f"{year}.pdf")


@st.cache_data(show_spinner=False)
def crop_image(year, crop):
    page_no, x0, y0, x1, y1 = crop
    page = load_pdf(year).load_page(page_no - 1)
    rectangle = fitz.Rect(x0, y0, x1, y1)
    pixmap = page.get_pixmap(
        matrix=fitz.Matrix(2.15, 2.15),
        clip=rectangle,
        alpha=False,
    )
    return pixmap.tobytes("png")


def make_balanced_exam(items, count):
    by_year = defaultdict(list)
    for item in items:
        by_year[item["year"]].append(item)

    years = list(by_year)
    random.shuffle(years)

    base, remainder = divmod(count, len(years))
    selected = []

    for position, year in enumerate(years):
        amount = base + (1 if position < remainder else 0)
        amount = min(amount, len(by_year[year]))
        selected.extend(random.sample(by_year[year], amount))

    selected_keys = {(item["year"], item["number"]) for item in selected}
    remaining = [item for item in items if (item["year"], item["number"]) not in selected_keys]

    if len(selected) < count:
        selected.extend(random.sample(remaining, count - len(selected)))

    random.shuffle(selected)
    return selected


def image_data_uri(year, crop):
    encoded = base64.b64encode(crop_image(year, crop)).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def build_print_html(exam_items, show_source=False, include_answer_key=False, compact=False):
    body_parts = []
    answer_rows = []
    answer_lookup = {
        (item["year"], item["number"]): item.get("answer")
        for item in load_items()
    }

    for exam_number, item in enumerate(exam_items, start=1):
        source = f'{item["year"]}년 {item["number"]}번'
        body_parts.append('<section class="question">')
        body_parts.append(f'<h2>문제 {exam_number}</h2>')

        if show_source:
            body_parts.append(f'<div class="source">원문: {source}</div>')

        if item.get("passage_crops"):
            body_parts.append('<div class="label">지문</div>')
            for crop in item["passage_crops"]:
                body_parts.append(f'<img src="{image_data_uri(item["year"], crop)}">')

        body_parts.append('<div class="label">문제</div>')
        for crop in item["question_crops"]:
            body_parts.append(f'<img src="{image_data_uri(item["year"], crop)}">')

        body_parts.append('<div class="answer-blank">정답: ① ② ③ ④</div>')
        body_parts.append('</section>')

        answer_value = item.get("answer", answer_lookup.get((item["year"], item["number"]), ""))
        answer_rows.append(
            f'<tr><td>{exam_number}</td><td>{source}</td><td>{answer_value}번</td></tr>'
        )

    compact_class = " compact" if compact else ""
    answer_key_html = ""
    if include_answer_key:
        answer_key_html = (
            '<section class="answer-key">'
            '<h2>정답표</h2>'
            '<table>'
            '<thead><tr><th>시험 번호</th><th>원문</th><th>정답</th></tr></thead>'
            f'<tbody>{"".join(answer_rows)}</tbody>'
            '</table>'
            '</section>'
        )

    return f"""
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>군무원 9급 국어 랜덤 기출</title>
<style>
    body {{
        font-family: Arial, "Malgun Gothic", sans-serif;
        margin: 28px;
        color: #111;
    }}
    .top {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 2px solid #111;
        margin-bottom: 24px;
        padding-bottom: 12px;
    }}
    h1 {{ font-size: 24px; margin: 0; }}
    .print-button {{ padding: 10px 16px; font-size: 15px; cursor: pointer; }}
    .question {{
        page-break-inside: avoid;
        margin-bottom: 34px;
        padding-bottom: 22px;
        border-bottom: 1px solid #ddd;
    }}
    h2 {{ font-size: 20px; margin: 0 0 8px; }}
    .source {{ font-size: 13px; color: #666; margin-bottom: 10px; }}
    .label {{
        font-weight: bold;
        margin: 14px 0 8px;
        padding: 6px 8px;
        background: #f1f1f1;
        border-left: 4px solid #333;
    }}
    img {{
        width: 100%;
        max-width: 760px;
        display: block;
        margin: 8px 0 12px;
    }}
    .answer-blank {{ margin-top: 12px; font-size: 17px; font-weight: bold; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 12px; }}
    th, td {{ border: 1px solid #888; padding: 8px; text-align: center; }}
    @media print {{
        .print-button {{ display: none; }}
        body {{ margin: 14mm; }}
        .question {{ page-break-inside: avoid; }}
    }}
</style>
</head>
<body class="{compact_class}">
<div class="top">
    <h1>군무원 9급 국어 랜덤 기출</h1>
    <button class="print-button" onclick="window.print()">인쇄하기</button>
</div>
{''.join(body_parts)}
{answer_key_html}
</body>
</html>
"""


for key, default in {"exam": None, "answers": {}, "submitted": False}.items():
    if key not in st.session_state:
        st.session_state[key] = default


items = load_items()

latest_by_key = {
    (item["year"], item["number"]): item
    for item in items
}

# 이전 버전에서 만든 시험이 브라우저 세션에 남아 있으면
# 최신 questions.json의 정답 데이터를 다시 붙입니다.
if st.session_state.exam is not None:
    st.session_state.exam = [
        latest_by_key.get((item.get("year"), item.get("number")), item)
        for item in st.session_state.exam
    ]

st.title("📚 군무원 9급 국어 기출 랜덤 문제")
st.caption(
    "2020~2025년 총 150문항에서 연도별로 골고루 출제합니다. "
    "공통 지문 문항은 해당 지문과 함께 표시됩니다."
)

with st.sidebar:
    st.header("시험 설정")

    selected_years = st.multiselect(
        "출제 연도",
        options=list(range(2020, 2026)),
        default=list(range(2020, 2026)),
    )

    pool = [item for item in items if item["year"] in selected_years]
    maximum = max(1, len(pool))

    question_count = st.number_input(
        "출제 문항 수",
        min_value=1,
        max_value=maximum,
        value=min(25, maximum),
        step=1,
    )

    show_source = st.checkbox("원래 연도·문항 번호 표시", value=False)

    if st.button("새 시험 만들기", type="primary", use_container_width=True):
        if not pool:
            st.error("출제 연도를 하나 이상 선택해 주세요.")
        else:
            st.session_state.exam = make_balanced_exam(pool, int(question_count))
            st.session_state.answers = {}
            st.session_state.submitted = False
            st.rerun()

    if st.button("초기화", use_container_width=True):
        st.session_state.exam = None
        st.session_state.answers = {}
        st.session_state.submitted = False
        st.rerun()


if st.session_state.exam is None:
    st.info("왼쪽에서 설정한 뒤 **새 시험 만들기**를 눌러 주세요.")
    st.stop()


st.download_button(
    "🖨️ 일반 인쇄용 HTML 다운로드",
    data=build_print_html(
        st.session_state.exam,
        show_source=show_source,
        include_answer_key=False,
        compact=False,
    ),
    file_name="gunmu_korean_exam.html",
    mime="text/html",
    use_container_width=True,
)

st.download_button(
    "📄 실제 시험지처럼 압축 인쇄용 HTML 다운로드",
    data=build_print_html(
        st.session_state.exam,
        show_source=show_source,
        include_answer_key=False,
        compact=True,
    ),
    file_name="gunmu_korean_exam_compact.html",
    mime="text/html",
    use_container_width=True,
)

if st.session_state.submitted:
    st.download_button(
        "✅ 정답표 포함 인쇄용 HTML 다운로드",
        data=build_print_html(st.session_state.exam, show_source=True, include_answer_key=True),
        file_name="gunmu_korean_exam_with_answers.html",
        mime="text/html",
        use_container_width=True,
    )


for exam_number, item in enumerate(st.session_state.exam, start=1):
    st.divider()
    st.markdown(f"## 시험 {exam_number}번")

    if show_source:
        st.caption(f'원문: {item["year"]}년 {item["number"]}번')

    if item.get("passage_crops"):
        st.markdown("#### 지문")
        for crop in item["passage_crops"]:
            st.image(crop_image(item["year"], crop), use_container_width=True)

    st.markdown("#### 문제")
    for crop in item["question_crops"]:
        st.image(crop_image(item["year"], crop), use_container_width=True)

    answer_key = f'{item["year"]}_{item["number"]}'
    selected = st.radio(
        f"시험 {exam_number}번 답안",
        options=[1, 2, 3, 4],
        format_func=lambda answer: f"{answer}번",
        horizontal=True,
        index=None,
        key=f"answer_{answer_key}",
        disabled=st.session_state.submitted,
        label_visibility="collapsed",
    )

    if selected is not None:
        st.session_state.answers[answer_key] = selected


st.divider()
total = len(st.session_state.exam)
answered = len(st.session_state.answers)
st.write(f"답안 작성: **{answered}/{total}문항**")

if not st.session_state.submitted:
    if st.button("채점하기", type="primary", use_container_width=True):
        if answered < total:
            st.warning(f"아직 {total - answered}문항을 풀지 않았습니다.")
        else:
            st.session_state.submitted = True
            st.rerun()
else:
    correct_count = 0
    wrong_items = []

    for exam_number, item in enumerate(st.session_state.exam, start=1):
        answer_key = f'{item["year"]}_{item["number"]}'
        user_answer = st.session_state.answers[answer_key]
        correct_answer = item.get("answer", latest_by_key[(item["year"], item["number"])]["answer"])
        if user_answer == correct_answer:
            correct_count += 1
        else:
            wrong_items.append({
                "exam_number": exam_number,
                "item": item,
                "user_answer": user_answer,
            })

    score = round(correct_count / total * 100, 1)
    st.success(f"점수: **{score}점** / 맞은 개수: **{correct_count}/{total}문항**")

    if wrong_items:
        st.subheader("오답 목록")
        for wrong in wrong_items:
            item = wrong["item"]
            st.write(
                f'❌ 시험 {wrong["exam_number"]}번 '
                f'({item["year"]}년 {item["number"]}번) '
                f'내 답: {wrong["user_answer"]}번 / 정답: {item.get("answer", latest_by_key[(item["year"], item["number"])]["answer"])}번'
            )
    else:
        st.balloons()
        st.write("전 문항 정답입니다!")

    st.subheader("전체 정답 확인")
    for exam_number, item in enumerate(st.session_state.exam, start=1):
        answer_key = f'{item["year"]}_{item["number"]}'
        source = f'{item["year"]}년 {item["number"]}번'
        st.write(
            f'시험 {exam_number}번 · {source}: '
            f'내 답 **{st.session_state.answers[answer_key]}번**, '
            f'정답 **{item.get("answer", latest_by_key[(item["year"], item["number"])]["answer"])}번**'
        )

    if st.button("새 랜덤 시험 만들기", use_container_width=True):
        st.session_state.exam = make_balanced_exam(pool, int(question_count))
        st.session_state.answers = {}
        st.session_state.submitted = False
        st.rerun()
