import streamlit as st
import pandas as st_pandas # Gọi thủ thư pandas
import pandas as pd

st.set_page_config(page_title="Studio Phim AI", layout="wide")

st.title("🎬 Studio Phim AI Tự Động")
st.markdown("---")

# Đường link Google Sheets của bạn (Tạm thời tôi dùng một link mẫu của tôi)
# Lát nữa bạn sẽ thay link của bạn vào đây nhé!
link_google_sheet = "https://docs.google.com/spreadsheets/d/1DuS2mwaaUa98vfn6OIVauoawDswSUCXNijsVBDETTow/edit?usp=sharing"

# Mẹo nhỏ của lập trình viên: Biến link xem thành link tải dữ liệu thô (CSV) để Python dễ đọc
link_doc_du_lieu = link_google_sheet.replace("/edit?usp=sharing", "/export?format=csv")

st.subheader("📋 Danh sách kịch bản từ Google Sheets")

try:
    # Nhờ pandas đọc đường link và biến nó thành một bảng dữ liệu (gọi là dataframe)
    bang_kich_ban = pd.read_csv(link_doc_du_lieu)
    
    # Yêu cầu Streamlit hiển thị cái bảng đó lên web
    st.dataframe(bang_kich_ban)
    
except Exception as e:
    st.error(f"Ôi, không đọc được file rồi. Lỗi là: {e}")
