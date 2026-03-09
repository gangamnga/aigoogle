import streamlit as st
import google.generativeai as genai

# Giao diện trang web
st.title("Trợ lý AI siêu cấp của tôi 🤖")
st.write("Xin chào! Mình có thể giúp gì cho bạn hôm nay?")

# Mở két sắt lấy chìa khóa kết nối với Google AI
API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=API_KEY)

# Chọn bộ não AI (Gemini 1.5 Flash là phiên bản nhanh và thông minh)
model = genai.GenerativeModel('gemini-3.0-flash')

# Ô để bạn nhập câu hỏi
cau_hoi = st.text_input("Bạn muốn hỏi gì nào?")

# Nút bấm gửi câu hỏi
if st.button("Gửi cho AI"):
    if cau_hoi:
        # Hiển thị vòng xoay chờ đợi
        with st.spinner('AI đang suy nghĩ...'):
            # Gửi câu hỏi cho AI và nhận kết quả
            ket_qua = model.generate_content(cau_hoi)
            st.success("Đã có câu trả lời!")
            st.write("**Trợ lý nói:**")
            st.write(ket_qua.text)
    else:
        st.warning("Bạn chưa gõ chữ nào kìa!")
