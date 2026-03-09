import streamlit as st
import google.generativeai as genai

st.title("Studio Phim AI 🎬 - Trạm 1: Tạo Hình")

# Lấy chìa khóa
API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=API_KEY)

# Ô nhập kịch bản
kich_ban = st.text_input("Nhập mô tả hình ảnh (VD: Một phi hành gia trên sao Hỏa):")

if st.button("Bấm máy chụp!"):
    if kich_ban:
        with st.spinner('Đang vẽ ảnh...'):
            try:
                # Gọi bộ não tạo ảnh mà máy quét của bạn đã tìm thấy
                model = genai.GenerativeModel('gemini-3.1-flash-image-preview')
                
                # Ra lệnh tạo ảnh
                ket_qua = model.generate_content(kich_ban)
                
                # Streamlit hỗ trợ hiển thị ảnh rất dễ dàng
                st.success("Tạo hình hoàn tất!")
                # Tùy thuộc vào cách Google trả về dữ liệu ảnh, chúng ta sẽ hiển thị nó
                # Nếu API trả về ảnh trực tiếp, ta sẽ dùng st.image()
                st.write(ket_qua.text) # Tạm thời in ra phản hồi để xem máy chủ trả về định dạng gì
                
            except Exception as e:
                st.error(f"Báo cáo đạo diễn, có lỗi xảy ra: {e}")
    else:
        st.warning("Đạo diễn chưa đưa kịch bản kìa!")
