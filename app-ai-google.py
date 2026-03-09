import streamlit as st

# Cài đặt trang web rộng ra hết màn hình
st.set_page_config(page_title="Studio Phim AI", layout="wide")

# --- KHU VỰC 1: MENU BÊN HÔNG (SIDEBAR) ---
with st.sidebar:
    st.header("⚙️ Bảng Điều Khiển")
    st.write("Chỉnh sửa thông số cho phim của bạn.")
    phong_cach = st.selectbox("Phong cách nghệ thuật:", ["Điện ảnh 3D", "Hoạt hình Anime", "Vẽ chì", "Cyberpunk"])
    ti_le = st.radio("Tỉ lệ khung hình:", ["16:9 (Ngang)", "9:16 (Dọc)", "1:1 (Vuông)"])
    st.info("💡 Mẹo: Chọn phong cách trước khi viết kịch bản.")

# --- KHU VỰC 2: MÀN HÌNH CHÍNH ---
st.title("🎬 Studio Phim AI Tự Động")
st.markdown("---") # Đường kẻ ngang phân cách

# Chia làm 2 cột: Cột trái (Nhập liệu) - Cột phải (Hiển thị)
cot_trai, cot_phai = st.columns(2)

with cot_trai:
    st.subheader("📝 1. Viết Kịch Bản")
    # Khung nhập chữ to và rộng hơn
    kich_ban = st.text_area("Mô tả cảnh quay của bạn:", height=200, placeholder="Ví dụ: Một phi hành gia đang đi bộ trên sao Hỏa...")
    nut_bam = st.button("🚀 Bấm Máy Tạo Ảnh!")

with cot_phai:
    st.subheader("📺 2. Màn Hình Chiếu")
    if nut_bam:
        if kich_ban:
            st.success("Đang xử lý kịch bản...")
            # Tạm thời dùng 1 bức ảnh mẫu để "đóng thế" trong lúc chờ nối API thật
            anh_mau = "https://images.unsplash.com/photo-1614730321146-b6fa6a46bcb4?q=80&w=1000"
            st.image(anh_mau, caption=f"Đã áp dụng phong cách: {phong_cach}")
        else:
            st.warning("Đạo diễn ơi, chưa có kịch bản!")
    else:
        st.info("Chờ lệnh từ đạo diễn...")
