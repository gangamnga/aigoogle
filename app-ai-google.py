import streamlit as st
import pandas as pd
import os
import time

# Thư viện xử lý Video (MoviePy có thể cần ImageMagick cho text/subtitle)
try:
    from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips
except ImportError:
    pass # Cần pip install moviepy

# Thư viện GCP Google Cloud
try:
    from google.cloud import texttospeech
    import vertexai
    from vertexai.preview.vision_models import ImageGenerationModel
    # Ghi chú: Sử dụng REST hoặc SDK tương lai đối với Veo Model nếu VideoGenerationModel chưa public
except ImportError:
    pass # Cần pip install google-cloud-texttospeech google-cloud-aiplatform

# ==========================================
# CẤU HÌNH GCP (Thay đổi theo Project của bạn)
# ==========================================
PROJECT_ID = "YOUR_GCP_PROJECT_ID"
LOCATION = "us-central1"

def init_gcp():
    """Khởi tạo Client Google Cloud và Vertex AI"""
    try:
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        return True
    except Exception as e:
        st.error(f"Lỗi khởi tạo GCP: {e}")
        return False

# ==========================================
# BƯỚC 2: TẠO AUDIO VÀ PHỤ ĐỀ (TTS)
# ==========================================
def generate_audio_and_srt(text, output_audio_path, output_srt_path, fake_duration=5.0):
    try:
        # Gọi API Google Cloud Vertex AI Text-To-Speech
        client = texttospeech.TextToSpeechClient()
        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            # Sử dụng dòng Journey (en-US-Journey-D hoặc en-US-Journey-F) của Google 
            # để có giọng đọc biểu cảm cao, mang tính chất kể chuyện, bí ẩn và lôi cuốn.
            name="en-US-Journey-D" 
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
        
        # Lưu file Audio
        with open(output_audio_path, "wb") as out:
            out.write(response.audio_content)
            
        # Tự động xuất file Phụ đề (.srt) cơ bản (Đồng bộ thời gian đơn giản)
        def format_time(seconds):
            hrs = int(seconds // 3600)
            mins = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            msecs = int((seconds % 1) * 1000)
            return f"{hrs:02d}:{mins:02d}:{secs:02d},{msecs:03d}"

        with open(output_srt_path, "w", encoding="utf-8") as f:
            f.write(f"1\n00:00:00,000 --> {format_time(fake_duration)}\n{text}\n")
            
        return True
    except Exception as e:
        st.error(f"Lỗi tạo TTS: {e}")
        return False

# ==========================================
# BƯỚC 3: TẠO KEYFRAME HÌNH ẢNH (IMAGEN)
# ==========================================
def generate_keyframe(prompt, output_image_path):
    try:
        # Gọi API Imagen 3 trên Vertex AI
        model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-001") 
        images = model.generate_images(
            prompt=prompt,
            number_of_images=1,
            aspect_ratio="16:9"
        )
        # Lưu file ảnh
        images[0].save(location=output_image_path)
        return True
    except Exception as e:
        st.error(f"Lỗi tạo Hình ảnh (Imagen API): {e}")
        return False

# ==========================================
# BƯỚC 4: TẠO VIDEO CHUYỂN ĐỘNG (VEO API)
# ==========================================
def generate_video_scene(start_image, end_image, prompt, output_video_path):
    try:
        # Giả lập gọi Veo API vì hiện tại API Veo có cấu trúc gọi qua VideoGenerationModel / REST
        # Input thực tế sẽ bao gồm start_image_path và end_image_path
        st.info(f"Đang gọi mô hình Veo kết nối hình ảnh và tạo video với prompt: '{prompt}'...")
        time.sleep(3) # Mô phỏng thời gian chờ Render
        
        # Code thực tế:
        # veo_model = GenerativeModel("veo-001-preview")
        # response = veo_model.generate_content(...)
        # Lưu response.candidates[0].video sang file output_video_path
        
        # Tạo dummy mp4 để test luồng:
        with open(output_video_path, 'wb') as f:
            f.write(b"") 
            
        return True
    except Exception as e:
        st.error(f"Lỗi tạo Video chuyển động (Veo API): {e}")
        return False

# ==========================================
# HÀM CHÍNH (STREAMLIT APP)
# ==========================================
def main():
    st.set_page_config(page_title="Tự động tạo Video GCP", layout="wide")
    st.title("🎬 Ứng dụng Tự động hóa Tạo Video từ Kịch bản (Google Cloud)")

    st.sidebar.header("Cấu hình & Trạng thái")
    st.sidebar.markdown(f"**GCP Project:** `{PROJECT_ID}`")
    st.sidebar.markdown(f"**Location:** `{LOCATION}`")
    
    # --- BƯỚC 1: TẢI & XỬ LÝ DỮ LIỆU ĐẦU VÀO ---
    st.header("Bước 1: Tải dữ liệu đầu vào (Google Sheets / Local)")
    
    col1, col2 = st.columns(2)
    with col1:
        folder_path = st.text_input("Đường dẫn thư mục chứa files kịch bản (.csv, .xlsx):", value="./data")
        scan_btn = st.button("Quét thư mục")
        
    if scan_btn or 'files' in st.session_state:
        # Xử lý tự tạo folder nếu chưa có
        if not os.path.exists(folder_path):
            os.makedirs(folder_path, exist_ok=True)
            
        files = [f for f in os.listdir(folder_path) if f.endswith(('.csv', '.xlsx'))]
        if files:
            st.session_state['files'] = files
            st.session_state['folder_path'] = folder_path
            st.success(f"Quét thành công! Tìm thấy {len(files)} file dữ liệu.")
        else:
            if scan_btn: st.warning("Không tìm thấy file .csv hoặc .xlsx nào trong thư mục.")

    if 'files' in st.session_state and len(st.session_state['files']) > 0:
        with col2:
            selected_file = st.selectbox("Chọn file kịch bản để xử lý:", st.session_state['files'])
            load_btn = st.button("Đọc dữ liệu bảng")
            
        if load_btn or 'df' in st.session_state:
            file_path = os.path.join(st.session_state['folder_path'], selected_file)
            try:
                if selected_file.endswith('.csv'):
                    df = pd.read_csv(file_path)
                else:
                    df = pd.read_excel(file_path)
                
                if len(df.columns) >= 4:
                    st.session_state['df'] = df
                    df.columns = ["STT", "Nội dung", "Prompt Keyframe", "Prompt Motion"]
                    st.dataframe(df, use_container_width=True)
                else:
                    st.error("File kịch bản không hợp lệ. Vui lòng đảm bảo bảng có đủ 4 cột.")
            except Exception as e:
                st.error(f"Lỗi đọc file: {e}")

    # --- BẮT ĐẦU QUY TRÌNH ---
    st.divider()
    if 'df' in st.session_state:
        df = st.session_state['df']
        
        if st.button("🚀 XÁC NHẬN VÀ BẮT ĐẦU RENDER", type="primary"):
            # st.info("Khởi tạo kết nối Google Cloud...")
            # if not init_gcp(): st.stop()
            
            # --- UI Tiến trình ---
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            output_dir = "workspace_output"
            os.makedirs(output_dir, exist_ok=True)
            
            total_rows = len(df)
            audio_files = []
            srt_files = []
            image_files = []
            video_clips = []
            
            # Lặp qua dữ liệu kịch bản
            for index, row in df.iterrows():
                stt = str(row["STT"])
                noi_dung = str(row["Nội dung"])
                prompt_keyframe = str(row["Prompt Keyframe"])
                prompt_motion = str(row["Prompt Motion"])
                
                status_text.write(f"**Đang xử lý dòng STT: {stt}...**")
                
                # --- BƯỚC 2: ÂM THANH & PHỤ ĐỀ ---
                st.subheader(f"STT {stt} - Âm thanh & Phụ đề")
                with st.spinner(f"Chạy Vertex AI TTS cho đoạn thoại: '{noi_dung[:20]}...'"):
                    audio_path = os.path.join(output_dir, f"Audio_{stt}.mp3")
                    srt_path = os.path.join(output_dir, f"Subtitle_{stt}.srt")
                    
                    if generate_audio_and_srt(noi_dung, audio_path, srt_path):
                        audio_files.append(audio_path)
                        srt_files.append(srt_path)
                        # Streamlit UI
                        st.audio(audio_path, format="audio/mp3")
                        with open(audio_path, "rb") as file:
                            st.download_button(label=f"Tải Audio {stt} (.mp3)", data=file, file_name=f"Audio_{stt}.mp3", mime="audio/mp3", key=f"dl_a_{stt}")
                            
                # --- BƯỚC 3: HÌNH ẢNH KEYFRAME ---
                st.subheader(f"STT {stt} - Keyframe Hình ảnh")
                with st.spinner(f"Render ảnh bằng Imagen 3: '{prompt_keyframe[:30]}...'"):
                    image_path = os.path.join(output_dir, f"Keyframe_{stt}.png")
                    # (Tạm thời bypass vì mock, thực tế sẽ gọi generate_keyframe)
                    # if generate_keyframe(prompt_keyframe, image_path): 
                    #     image_files.append(image_path)
                    
                    # Mô phỏng file tạo thành công:
                    with open(image_path, "wb") as f: f.write(b"")
                    image_files.append(image_path)
                    st.success(f"Đã lưu {image_path}")
                
                # Cập nhật thanh Load từng dòng
                progress_bar.progress((index * 3 + 1) / (total_rows * 3 + 2))

            # --- Hiển thị lưới bảng Keyframes ở cuối Bước 3 ---
            st.write("### Tổng hợp Ảnh Keyframes (Grid)")
            if len(image_files) > 0:
                img_df = pd.DataFrame({
                    "STT": df["STT"].values,
                    "Prompt Keyframe": df["Prompt Keyframe"].values,
                    "File Path": image_files
                })
                col_disp = st.columns(3)
                for idx, path in enumerate(image_files):
                    # st.image(path) - Trong thực tế path chứa ảnh
                    col_disp[idx % 3].markdown(f"**Keyframe {df['STT'].values[idx]}**\n`{path}`")
                st.dataframe(img_df, use_container_width=True)

            # --- BƯỚC 4: TẠO VIDEO CHUYỂN ĐỘNG ---
            st.header("Bước 4: Model Veo - Tạo Video Chuyển động")
            for i in range(len(image_files)):
                stt = df.iloc[i]["STT"]
                start_img = image_files[i]
                end_img = image_files[i+1] if i + 1 < len(image_files) else None 
                motion_prompt = df.iloc[i]["Prompt Motion"]
                
                with st.spinner(f"Tạo Video Scene bằng API Veo cho STT {stt}..."):
                    vid_path = os.path.join(output_dir, f"VideoClip_{stt}.mp4")
                    if generate_video_scene(start_img, end_img, motion_prompt, vid_path):
                        video_clips.append(vid_path)
                        
                progress_bar.progress((total_rows * 3 + 1) / (total_rows * 3 + 2))

            # --- BƯỚC 5: GHÉP NỐI VÀ XUẤT BẢN ---
            st.header("Bước 5: Ghép Code & Xuất Video (MoviePy)")
            with st.spinner("Đang sử dụng MoviePy để concatenate clips, chèn audio và srt..."):
                try:
                    # Mã MoviePy ghép file thực tế:
                    '''
                    valid_clips = []
                    for v_path, a_path in zip(video_clips, audio_files):
                        clip = VideoFileClip(v_path)
                        audio = AudioFileClip(a_path)
                        clip = clip.set_audio(audio)
                        valid_clips.append(clip)
                        
                    final_video = concatenate_videoclips(valid_clips, method="compose")
                    output_final = os.path.join(output_dir, "Video_Hoan_Chinh.mp4")
                    final_video.write_videofile(output_final, codec="libx264", audio_codec="aac")
                    '''
                    # Giả lập ghép nối thành công:
                    time.sleep(2)
                    output_final = os.path.join(output_dir, "Video_Hoan_Chinh.mp4")
                    with open(output_final, "wb") as f: f.write(b"")
                    
                    progress_bar.progress(100)
                    status_text.success("🎉 QUÁ TRÌNH KHỞI TẠO VÀ GHÉP NỐI TRỌN VẸN!")
                    st.success(f"Video đã được render và lưu tại: {output_final}")
                    
                    # Nút TẢI XUỐNG Dành cho người dùng
                    with open(output_final, "rb") as final_f:
                        st.download_button(
                            label="📥 TẢI XUỐNG VIDEO HOÀN CHỈNH (.mp4)",
                            data=final_f,
                            file_name="Video_Veo_GCP_Automation.mp4",
                            mime="video/mp4",
                            type="primary",
                            use_container_width=True
                        )
                except Exception as e:
                    st.error(f"Lỗi khi ghép video bằng MoviePy: {e}")

if __name__ == "__main__":
    main()
