import streamlit as st
import google.generativeai as genai

st.title("Máy quét tìm AI 🔍")
st.write("Đang kiểm tra xem chìa khóa của bạn mở được những bộ não nào...")

try:
    # Lấy chìa khóa
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)

    # Quét danh sách
    danh_sach = []
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            danh_sach.append(m.name)
            
    # Hiển thị kết quả
    if danh_sach:
        st.success("TÌM THẤY RỒI! Đây là danh sách các tên mã chuẩn xác 100% dành riêng cho bạn:")
        for ten in danh_sach:
            st.write(f"- `{ten}`")
    else:
        st.error("Chìa khóa của bạn hợp lệ nhưng không tìm thấy bộ não nào.")
        
except Exception as e:
    st.error(f"Cảnh báo lỗi từ Google: {e}")
