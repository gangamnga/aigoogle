import streamlit as st
import pandas as pd
import time

st.set_page_config(page_title="Studio Phim AI", layout="wide")
st.title("🎬 Studio Phim AI Tự Động")

danh_sach_link_goc = st.text_area("Dán danh sách link Google Sheets vào đây:", height=100)
nut_bam = st.button("🚀 Bắt đầu sản xuất!")

if nut_bam and danh_sach_link_goc:
    danh_sach_link = danh_sach_link_goc.split('\n')
    
    for stt, link in enumerate(danh_sach_link):
        if link.strip() == "": continue
            
        st.markdown(f"### 🎞️ Đang làm Phim số {stt + 1}")
        link_doc_du_lieu = link.replace("/edit?usp=sharing", "/export?format=csv")
        
        try:
            # 1. Đọc bảng dữ liệu
            bang_kich_ban = pd.read_csv(link_doc_du_lieu)
            st.dataframe(bang_kich_ban)
            
            # 2. Bắt đầu Trạm 2: Xử lý hình ảnh
            st.write("🎨 Đang chuẩn bị kịch bản hình ảnh...")
            
            # Trích xuất lệnh vẽ ở phân cảnh đầu tiên (dòng số 0)
            lenh_ve_anh_canh_1 = bang_kich_ban["Prompt Hình ảnh (Keyframe)"].iloc[0]
            
            st.info(f"Đang vẽ cảnh 1 với lệnh: {lenh_ve_anh_canh_1}")
            
            with st.spinner('AI đang vẽ...'):
                time.sleep(2) # Chờ 2 giây mô phỏng thời gian AI vẽ
                
                # Vì chúng ta chưa cài thẻ ngân hàng, ta vẫn dùng ảnh đóng thế, 
                # nhưng chú thích bên dưới ảnh sẽ là câu lệnh thật từ Google Sheets của bạn!
                anh_mau = "https://images.unsplash.com/photo-1614730321146-b6fa6a46bcb4?q=80&w=1000"
                st.image(anh_mau, caption=f"Kịch bản AI nhận được: {lenh_ve_anh_canh_1}")
                
        except Exception as e:
            st.error(f"❌ Lỗi: {e}")
