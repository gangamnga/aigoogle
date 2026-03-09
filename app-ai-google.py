import streamlit as st

# Mở rộng toàn bộ trang web
st.set_page_config(page_title="AI Movie Studio", layout="wide")

# 1. Tạo Menu bên hông (Sidebar)
with st.sidebar:
    st.header("⚙️ Cài đặt Studio")
    st.write("Bảng điều khiển các thông số của phim.")
    phong_cach = st.selectbox("Chọn phong cách:", ["Điện ảnh (Cinematic)", "Hoạt hình 3D", "Tranh vẽ tay"])
    
# 2. Tiêu đề chính
st.title("🎬 Studio Phim AI Siêu Cấp")

# 3. Chia màn hình thành 2 cột (Cột trái to bằng cột phải)
cot_trai, cot_phai = st.columns(2)

with cot_trai:
    st.subheader("📝 1. Kịch bản Hình Ảnh")
    # Thay text_input bằng text_area để khung nhập liệu to hơn
    kich_ban = st.text_area("Nhập chi tiết cảnh quay của bạn:", height=150, placeholder="Ví dụ: Một phi hành gia đang đi bộ trên sao Hỏa lúc hoàng hôn...")
    nut_bam = st.button("Bấm máy 🎥")

with cot_phai:
    st.subheader("🖼️ 2. Màn hình xem trước")
    if nut_bam:
        if kich_ban:
            st.info(f"Đang vẽ ảnh theo phong cách: {phong_cach}...")
            # Dùng "diễn viên đóng thế" - một đường link ảnh có sẵn trên mạng
            anh_mau = "https://images.unsplash.com/photo-1614730321146-b6fa6a46bcb4?q=80&w=1000"
            st.image(anh_mau, caption=f"Kịch bản: {kich_ban}")
        else:
            st.warning("Đạo diễn chưa đưa kịch bản kìa!")
    else:
        st.write("Chờ lệnh từ đạo diễn...")
