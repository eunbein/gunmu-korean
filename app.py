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
    """선택 연도별 문항 수의 차이가 최대 1이 되도록 출제합니다."""
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

    selected_keys = {
        (item["year"], item["number"])
        for item in selected
    }
    remaining = [
        item for item in items
        if (item["year"], item["number"]) not in selected_keys
    ]

    if len(selected) < count:
        selected.extend(
            random.sample(remaining, count - len(selected))
        )

    random.shuffle(selected)
    return selected


for key, default in {
    "exam": None,
    "answers": {},
    "submitted": False,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


items = load_items()

st.title("📚 군무원 9급 국어 기출 랜덤 문제")
st.caption(
    "2020~2025년 총 150문항에서 연도별로 골고루 출제합니다. "
    "문제·선지와 공통 지문은 원본 PDF 그대로 표시됩니다."
)

with st.sidebar:
    st.header("시험 설정")

    selected_years = st.multiselect(
        "출제 연도",
        options=list(range(2020, 2026)),
        default=list(range(2020, 2026)),
    )

    pool = [
        item for item in items
        if item["year"] in selected_years
    ]

    maximum = max(1, len(pool))
    question_count = st.number_input(
        "출제 문항 수",
        min_value=1,
        max_value=maximum,
        value=min(25, maximum),
        step=1,
    )

    show_source = st.checkbox(
        "원래 연도·문항 번호 표시",
        value=False,
    )

    if st.button(
        "새 시험 만들기",
        type="primary",
        use_container_width=True,
    ):
        if not pool:
            st.error("출제 연도를 하나 이상 선택해 주세요.")
        else:
            st.session_state.exam = make_balanced_exam(
                pool,
                int(question_count),
            )
            st.session_state.answers = {}
            st.session_state.submitted = False
            st.rerun()

    if st.button("초기화", use_container_width=True):
        st.session_state.exam = None
        st.session_state.answers = {}
        st.session_state.submitted = False
        st.rerun()


if st.session_state.exam is None:
    st.info(
        "왼쪽에서 설정한 뒤 **새 시험 만들기**를 눌러 주세요."
    )
    st.stop()


for exam_number, item in enumerate(
    st.session_state.exam,
    start=1,
):
    st.divider()
    st.markdown(f"## 시험 {exam_number}번")

    if show_source:
        st.caption(
            f'원문: {item["year"]}년 {item["number"]}번'
        )

    # A question belonging to a common passage always receives that passage.
    if item.get("passage_crops"):
        st.markdown("#### 지문")
        for crop in item["passage_crops"]:
            st.image(
                crop_image(item["year"], crop),
                use_container_width=True,
            )

    st.markdown("#### 문제")
    for crop in item["question_crops"]:
        st.image(
            crop_image(item["year"], crop),
            use_container_width=True,
        )

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
    if st.button(
        "답안 제출",
        type="primary",
        use_container_width=True,
    ):
        if answered < total:
            st.warning(
                f"아직 {total - answered}문항을 풀지 않았습니다."
            )
        else:
            st.session_state.submitted = True
            st.rerun()
else:
    st.success("답안을 제출했습니다.")
    st.subheader("내가 선택한 답")

    for exam_number, item in enumerate(
        st.session_state.exam,
        start=1,
    ):
        answer_key = f'{item["year"]}_{item["number"]}'
        source = (
            f' · {item["year"]}년 {item["number"]}번'
            if show_source else ""
        )
        st.write(
            f'시험 {exam_number}번{source}: '
            f'**{st.session_state.answers[answer_key]}번**'
        )

    if st.button(
        "새 랜덤 시험 만들기",
        use_container_width=True,
    ):
        st.session_state.exam = make_balanced_exam(
            pool,
            int(question_count),
        )
        st.session_state.answers = {}
        st.session_state.submitted = False
        st.rerun()
