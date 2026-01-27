import streamlit as st
import google.generativeai as genai
from PIL import Image
import json

# ==========================================
# [설정] 비밀 키 가져오기 (Streamlit 서버용)
# ==========================================
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    # 로컬에서 테스트할 때만 주석을 풀고 키를 넣으세요. (GitHub 올릴 땐 지우는 게 좋습니다)
    GOOGLE_API_KEY = "여기에_API_키를_넣으세요"

genai.configure(api_key=GOOGLE_API_KEY)

# -----------------------------------------------------------
# [모델 설정] 성능이 가장 좋은 'Gemini 1.5 Pro' 사용
# -----------------------------------------------------------
model_name = 'models/gemini-exp-1206'
model = genai.GenerativeModel(model_name)

def analyze_page(image):
    prompt = """
    당신은 수학 1타 강사입니다. 이미지 속의 **모든 문제**를 찾아서 채점하고, 
    각 문제마다 **숫자만 바꾼 유사문제(쌍둥이 문제)**를 하나씩 만들어주세요.

    다음 JSON 형식으로 정확하게 출력하세요:

    1. **problem_id**: 문제 번호
    2. **student_answer**: 학생 답 (없으면 "미기재")
    3. **grading**: "O"(정답), "X"(오답), "?"(판독불가)
    4. **why_wrong**: 틀린 이유 분석 (정답이면 칭찬)
    5. **solution**: 원본 문제의 정석 풀이
    6. **similar_problem**: 
       - **question**: 원본과 논리는 같고 숫자만 바꾼 새로운 문제
       - **answer**: 그 유사문제의 정답과 간단한 풀이

    Output Format (JSON Array):
    [
        {
            "problem_id": 1,
            "student_answer": "10",
            "grading": "X",
            "why_wrong": "계산 실수입니다.",
            "solution": "원래 풀이는...",
            "similar_problem": {
                "question": "어떤 수 x에 3을 더했더니... (새로운 문제)",
                "answer": "정답: 5 (풀이: x+3=8 이므로...)"
            }
        }
    ]
    """
    
    try:
        response = model.generate_content([prompt, image])
        text = response.text.replace("```json", "").replace("```", "").strip()
        
        if not text.startswith("["):
            start = text.find("[")
            end = text.rfind("]") + 1
            if start != -1 and end != -1:
                text = text[start:end]
            
        return json.loads(text)
    except Exception as e:
        return {"error": str(e)}

# ==========================================
# [화면 구성]
# ==========================================
st.set_page_config(page_title="수학과제도우미_by gfield", page_icon="📚", layout="wide")

st.title("📚 수학과제도우미_by gfield")
st.caption("채점부터 오답 분석, 유사문제 추천까지 한 번에!")

# 상태 저장을 위한 세션 초기화
if 'results' not in st.session_state:
    st.session_state['results'] = None

with st.sidebar:
    st.header("사용 방법")
    st.markdown("""
    1. **파일** 또는 **카메라** 탭 선택
    2. 문제집 사진 찍기
    3. **채점 시작** 클릭
    4. 결과 확인 후 **유사문제 도전** 클릭!
    """)

tab1, tab2 = st.tabs(["📁 파일 업로드", "📸 카메라로 찍기"])
image = None

with tab1:
    uploaded_file = st.file_uploader("이미지 파일", type=["jpg", "png", "jpeg"])
    if uploaded_file:
        image = Image.open(uploaded_file)

with tab2:
    camera_file = st.camera_input("문제집 찍기")
    if camera_file:
        image = Image.open(camera_file)

if image:
    st.image(image, caption='업로드된 문제집', use_container_width=True)
    
    if st.button("🚀 채점 및 분석 시작"):
        with st.spinner('Gemini 선생님이 채점하고 유사문제를 만들고 있습니다...'):
            st.session_state['results'] = analyze_page(image)

    if st.session_state['results']:
        results = st.session_state['results']
        
        if isinstance(results, dict) and "error" in results:
            st.error(f"오류 발생: {results['error']}")
        elif isinstance(results, list):
            st.markdown("---")
            st.markdown("### 📊 채점 결과")
            
            total = len(results)
            correct = sum(1 for r in results if r.get('grading') == 'O')
            score = int((correct / total) * 100) if total > 0 else 0
            
            col1, col2 = st.columns(2)
            col1.metric("점수", f"{score}점")
            col2.metric("정답률", f"{correct} / {total} 문제")
            
            st.divider()
            
            for res in results:
                icon = "✅" if res['grading'] == 'O' else ("❌" if res['grading'] == 'X' else "❓")
                
                with st.expander(f"{icon} 문제 {res['problem_id']}번 (학생 답: {res.get('student_answer')})", expanded=(res['grading']=='X')):
                    
                    if res['grading'] == 'X':
                        st.markdown(f":red[**⚠️ 왜 틀렸을까?**] {res.get('why_wrong')}")
                    else:
                        st.markdown(f":green[**👍 훌륭해요!**] {res.get('why_wrong')}")
                    
                    st.info(f"**📝 정석 풀이:** {res.get('solution')}")
                    
                    st.markdown("---")
                    with st.expander("🎯 이 문제와 비슷한 유사문제 풀어보기 (클릭)"):
                        sim_prob = res.get('similar_problem', {})
                        if sim_prob:
                            st.write(f"**Q. {sim_prob.get('question')}**")
                            with st.expander("👀 정답 및 풀이 확인"):
                                st.write(sim_prob.get('answer'))
                        else:
                            st.write("유사문제를 생성하지 못했습니다.")
        else:
            st.error("분석 결과 형식이 올바르지 않습니다. 다시 시도해주세요.")