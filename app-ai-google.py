import streamlit as st
import google.generativeai as genai

# Giao diện trang web
st.title("Trợ lý AI siêu cấp của tôi 🤖")
st.write("Xin chào! Mình có thể giúp gì cho bạn hôm nay?")

# Lấy chìa khóa
API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=API_KEY)

# Sử dụng chính xác cái tên mà máy quét vừa tìm ra!
model = genai.GenerativeModel('gemini-2.5-flash')

# Ô nhập liệu và Nút bấm
cau_hoi = st.text_input("Bạn muốn hỏi gì nào?")

if st.button("Gửi cho AI"):
    if cau_hoi:
        with st.spinner('AI đang suy nghĩ...'):
            ket_qua = model.generate_content(cau_hoi)
            st.success("Đã có câu trả lời!")
            st.write("**Trợ lý nói:**")
            st.write(ket_qua.text)
    else:
        st.warning("Bạn chưa gõ chữ nào kìa!")
