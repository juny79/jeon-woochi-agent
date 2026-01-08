import streamlit as st
from src.llm.client import SolarClient
from src.agent.persona_prompt import JeonWoochiPersona

def launch_ui(api_key: str):
    st.title("🧙‍♂️ 환생한 전우치의 명상소")
    st.subheader("마음의 도를 닦으러 오셨구려.")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 대화 내역 표시
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 사용자 입력
    if prompt := st.chat_input("무엇이 궁금하오?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 전우치 응답 (임시 로직)
        client = SolarClient(api_key=api_key)
        system_msg = {"role": "system", "content": JeonWoochiPersona.SYSTEM_PROMPT}
        user_msgs = st.session_state.messages[-5:] # 최근 5턴 기억
        
        with st.chat_message("assistant"):
            response = client.generate([system_msg] + user_msgs)
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})