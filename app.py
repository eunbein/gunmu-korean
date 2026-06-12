import io
import json
import random
from collections import defaultdict
from pathlib import Path

import fitz
import streamlit as st

st.set_page_config(
    page_title="군무원 9급 국어 기출 랜덤",
    page_icon="📚",
    layout="wide",
)

ROOT = Path(__file__).parent
QUESTIONS_PATH = ROOT / "questions.json"


@st.cache_data
def load_questions():
    return json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))


@st.cache_resource
def open_pdf(year: int):
    return fitz.open(ROOT / f"{year}.pdf")


@st.cache_data(show_spinner=False)
def render_page(year: int, page_number: int, zoom: float = 1.8):
    doc = open_pdf(year)
    page = doc.load_page(page_number - 1)
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    return pix.tobytes("png")


def make_exam(pool, count):
    return random.sample(pool, k=count)


def reset_exam():
    st.session_state.exam = None
    st.session_state.answers = {}
    st.session_state.submitted = False


for key, value in {
    "exam": None,
    "answers": {},
    "submitted": False,
}.items():
    if key not in st.session_state:
        st.session_state[key] = value


questions = load_questions()

st.title("📚 군무원 9급 국어 기출 랜덤 문제")
st.caption(
    "2020~2025년 원본 PDF 페이지를 그대로 보여 줍니다. "
    "지문·한자·옛한글·밑줄·보기의 누락이나 임의 변형을 막기 위한 방식입니다."
)

with st.sidebar:
    st.header("시험 설정")

    years = st.multiselect(
        "출제 연도",
        options=list(range(2020, 2026)),
        default=list(range(2020, 2026)),
    )

    filtered = [q for q in questions if q["year"] in years]

    count = st.number_input(
        "출제 문항 수",
        min_value=1,
        max_value=min(150, len(filtered)) if filtered else 1,
        value=min(25, len(filtered)) if filtered else 1,
        step=1,
    )

    show_source = st.checkbox("연도와 원래 문항 번호 표시", value=True)

    if st.button("새 시험 만들기", type="primary", use_container_width=True):
        if not filtered:
            st.error("출제 연도를 하나 이상 선택해 주세요.")
        else:
            st.session_state.exam = make_exam(filtered, int(count))
            st.session_state.answers = {}
            st.session_state.submitted = False
            st.rerun()

    if st.button("초기화", use_container_width=True):
        reset_exam()
        st.rerun()

if st.session_state.exam is None:
    st.info("왼쪽에서 출제 연도와 문항 수를 고른 뒤 **새 시험 만들기**를 눌러 주세요.")
    st.stop()

# Group selected questions by year and source page to avoid repeating the same page image.
page_groups = defaultdict(list)
for item in st.session_state.exam:
    for page in item["pages"]:
        page_groups[(item["year"], page)].append(item["number"])

display_map = {}
for index, item in enumerate(st.session_state.exam, start=1):
    display_map[(item["year"], item["number"])] = index

# Show source pages in chronological order; within each page show only selected question answer boxes.
for (year, page), q_numbers in sorted(page_groups.items()):
    unique_qs = sorted(set(q_numbers))
    st.divider()
    title = f"{year}년 원본 {page}쪽"
    if show_source:
        title += " · 이번 시험 대상: " + ", ".join(f"{n}번" for n in unique_qs)
    st.subheader(title)

    st.image(
        render_page(year, page),
        use_container_width=True,
        caption=f"{year}년 국어 원본 PDF {page}쪽",
    )

    for q_no in unique_qs:
        # Q23 (2023) is displayed on pages 5 and 6; answer box should appear only once.
        if year == 2023 and q_no == 23 and page != 6:
            continue

        display_no = display_map[(year, q_no)]
        key = f"{year}_{q_no}"

        st.markdown(f"### 시험 {display_no}번")
        if show_source:
            st.caption(f"원문: {year}년 {q_no}번")

        answer = st.radio(
            f"시험 {display_no}번 답 선택",
            options=[1, 2, 3, 4],
            format_func=lambda x: f"{x}번",
            index=None,
            horizontal=True,
            key=f"radio_{key}",
            disabled=st.session_state.submitted,
            label_visibility="collapsed",
        )
        if answer is not None:
            st.session_state.answers[key] = answer

st.divider()
total = len(st.session_state.exam)
answered = len(st.session_state.answers)
st.write(f"답안 작성: **{answered}/{total}문항**")

if not st.session_state.submitted:
    if st.button("답안 제출", type="primary", use_container_width=True):
        if answered < total:
            st.warning(f"아직 {total - answered}문항을 풀지 않았습니다.")
        else:
            st.session_state.submitted = True
            st.rerun()
else:
    st.success("답안을 제출했습니다.")
    st.info(
        "이 전체 연도 원본 보존판은 우선 150문항 출제와 지문 보존을 완성한 버전입니다. "
        "정답표를 검증해 연결하기 전까지는 자동 채점을 하지 않습니다."
    )

    st.subheader("내가 선택한 답")
    for index, item in enumerate(st.session_state.exam, start=1):
        key = f'{item["year"]}_{item["number"]}'
        st.write(
            f'시험 {index}번 · {item["year"]}년 {item["number"]}번 '
            f'→ **{st.session_state.answers.get(key)}번**'
        )

    if st.button("새 랜덤 시험 만들기", use_container_width=True):
        st.session_state.exam = make_exam(filtered, int(count))
        st.session_state.answers = {}
        st.session_state.submitted = False
        st.rerun()
