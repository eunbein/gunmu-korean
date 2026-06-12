import json
import random
from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="군무원 9급 국어 기출",
    page_icon="📚",
    layout="wide",
)

DATA_PATH = Path("questions.json")


@st.cache_data
def load_groups():
    with DATA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def make_exam(groups, target_count):
    """공통 지문 묶음을 유지하며 목표 문항 수만큼 출제합니다."""
    groups = groups.copy()
    random.shuffle(groups)

    selected = []
    count = 0

    for group in groups:
        size = len(group["questions"])
        if count + size <= target_count:
            selected.append(group)
            count += size
        if count == target_count:
            break

    # 테스트 데이터처럼 전체 문항이 목표 수보다 적을 때
    return selected


def reset_exam():
    st.session_state.exam = None
    st.session_state.answers = {}
    st.session_state.submitted = False


for key, default in {
    "exam": None,
    "answers": {},
    "submitted": False,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


groups = load_groups()

st.title("📚 군무원 9급 국어 기출 랜덤 문제")
st.caption("현재 파일은 Streamlit 연결을 확인하기 위한 시험용 버전입니다.")

with st.sidebar:
    st.header("시험 설정")

    years = sorted({group["year"] for group in groups})
    selected_years = st.multiselect(
        "출제 연도",
        years,
        default=years,
    )

    total_available = sum(
        len(group["questions"])
        for group in groups
        if group["year"] in selected_years
    )

    question_count = st.number_input(
        "출제 문항 수",
        min_value=1,
        max_value=max(total_available, 1),
        value=min(3, max(total_available, 1)),
        step=1,
    )

    if st.button("새 시험 만들기", type="primary", use_container_width=True):
        filtered = [
            group for group in groups
            if group["year"] in selected_years
        ]
        st.session_state.exam = make_exam(filtered, int(question_count))
        st.session_state.answers = {}
        st.session_state.submitted = False
        st.rerun()

    if st.button("초기화", use_container_width=True):
        reset_exam()
        st.rerun()


if st.session_state.exam is None:
    st.info("왼쪽에서 설정한 뒤 **새 시험 만들기**를 눌러 주세요.")
    st.stop()


display_no = 1
question_keys = []

for group in st.session_state.exam:
    st.divider()

    passage = group.get("passage", "").strip()
    if passage:
        st.markdown("#### 공통 지문")
        st.info(passage)

    for q in group["questions"]:
        q_key = f'{group["group_id"]}_{q["number"]}'
        question_keys.append(q_key)

        st.markdown(f"### {display_no}. {q['question']}")

        selected = st.radio(
            f"{display_no}번 답안",
            options=list(range(1, len(q["choices"]) + 1)),
            format_func=lambda n, choices=q["choices"]: choices[n - 1],
            index=None,
            key=f"radio_{q_key}",
            disabled=st.session_state.submitted,
            label_visibility="collapsed",
        )

        if selected is not None:
            st.session_state.answers[q_key] = selected

        display_no += 1


st.divider()
answered = len(st.session_state.answers)
total = len(question_keys)
st.write(f"답안 작성: **{answered}/{total}문항**")

if not st.session_state.submitted:
    if st.button("답안 제출", type="primary", use_container_width=True):
        st.session_state.submitted = True
        st.rerun()
else:
    st.success("답안이 제출되었습니다.")
    st.caption(
        "이 시험용 버전은 아직 정답표가 연결되지 않아 채점하지 않습니다. "
        "앱 배포가 정상적으로 되는지 먼저 확인하는 단계입니다."
    )
