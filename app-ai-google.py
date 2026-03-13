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
PROJECT_ID = "project-5409ce36-126a-4d22-a43"
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
    st.set_page_config(page_title="GCP Video Automation", page_icon=":material/movie:", layout="wide")
    

    with st.sidebar:
        st.image("https://www.gstatic.com/devrel-devsite/prod/vc81ecfc84451ec652a92f8d3c500ab198bb6bf9dfa6d70ff2de6cc8c4ecf8df0/cloud/images/cloud-logo.svg", width=200)
        st.markdown("### :material/settings: System Configuration")
        st.info(f"**GCP Project:**\n`{PROJECT_ID}`")
        st.info(f"**Location:**\n`{LOCATION}`")
        st.divider()
        st.markdown("### :material/bar_chart: Status")
        st.success("API Services: Ready")
        st.markdown("---")
        st.caption("Auto Video Pipeline v2.0")

    # Ẩn danh sách file mặc định của file_uploader bằng CSS
    st.markdown("""
        <style>
            /* Cấu hình hiển thị danh sách file mặc định của Streamlit (5 file kèm thanh cuộn) */
            [data-testid="stFileUploaderDropzoneInstructions"] ~ div {
                max-height: 250px !important;
                overflow-y: auto !important;
            }
        </style>
    """, unsafe_allow_html=True)
    
    uploaded_files = st.file_uploader(
        "", 
        label_visibility="collapsed",
        type=['csv', 'xlsx'], 
        accept_multiple_files=True
    )

    # --- BẮT ĐẦU QUY TRÌNH TỰ ĐỘNG HÀNG LOẠT ---
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("START AUTOMATION BATCH", type="primary", use_container_width=True):
        if not uploaded_files:
            st.warning("Vui lòng tải lên ít nhất 1 file kịch bản trước khi chạy!")
        else:
            current_file_header = st.empty()
            table_placeholder = st.empty()
            st.markdown("<br><br>", unsafe_allow_html=True)
            final_results_placeholder = st.empty()
            final_results_data = []
            
            for uploaded_file in uploaded_files:
                current_filename = uploaded_file.name
                
                # Tạo một UI container đẹp cho mỗi file
                current_file_header.markdown(f":material/movie: **Đang xử lý kịch bản:** <span style='color:#28a745;'>{current_filename}</span>", unsafe_allow_html=True)
                    
                # 1. Đọc dữ liệu
                try:
                    # Đưa con trỏ file về 0 trước khi đọc
                    uploaded_file.seek(0)
                    df_current = pd.read_csv(uploaded_file) if current_filename.endswith('.csv') else pd.read_excel(uploaded_file)
                    if len(df_current.columns) < 4:
                        st.error(f"File {current_filename} không đủ 4 cột. Bỏ qua.")
                        continue
                    df_current.columns = ["STT", "Nội dung", "Prompt Keyframe", "Prompt Motion"]
                except Exception as e:
                    st.error(f"Lỗi đọc file {current_filename}: {e}")
                    continue
                    
                # 2. Tạo thư mục output riêng cho file này
                file_basename = os.path.splitext(current_filename)[0]
                output_dir = os.path.join("workspace_output", file_basename)
                os.makedirs(output_dir, exist_ok=True)
                    
                total_rows = int(len(df_current))
                audio_files = []
                srt_files = []
                image_files = []
                video_clips = []
                
                # Hiển thị hoàn toàn file ra bảng (không cột trạng thái)
                df_display = df_current.rename(columns={
                    "STT": "Scene",
                    "Prompt Keyframe": "Prompt Hình Ảnh (Keyframe)",
                    "Prompt Motion": "Prompt Video (Motion)"
                })
                table_placeholder.dataframe(df_display, use_container_width=True, hide_index=True)
                has_error = False

                # --- BƯỚC 1.5: GOM NỘI DUNG & TẠO AUDIO CHUNG ---
                full_text = " ".join([str(text) for text in df_current["Nội dung"].tolist() if str(text).strip()])
                audio_full_path = os.path.join(output_dir, f"Audio_Full_{file_basename}.mp3")
                srt_full_path = os.path.join(output_dir, f"Subtitle_Full_{file_basename}.srt")
                
                # Hiển thị UI kết quả Audio Full ngay bên dưới bảng
                st.markdown("<br>", unsafe_allow_html=True)
                audio_ui_container = st.container(border=True)
                with audio_ui_container:
                    st.markdown("##### :material/record_voice_over: TỔNG HỢP AUDIO VOICE-OVER")
                    col_text, col_media = st.columns([7, 3])
                    
                    with col_text:
                        st.text_area("Nội dung kịch bản gốc (Full Text):", full_text, height=210, disabled=True)
                        
                    with col_media:
                        media_placeholder_1 = st.empty()
                        media_placeholder_2 = st.empty()

                if os.path.exists(audio_full_path) and os.path.exists(srt_full_path):
                    pass
                else:
                    with st.spinner(f":material/mic: Generating Unified TTS for '{current_filename}'..."):
                        if not generate_audio_and_srt(full_text, audio_full_path, srt_full_path):
                            st.error(f":material/close: Lỗi tạo Audio chung cho kịch bản. Dừng tiến trình file này.")
                            has_error = True
                            continue # Bỏ qua file hiện tại

                # Hiển thị Audio Player và Nút Tải sau khi sinh xong (hoặc đã có sẵn)
                if not has_error and os.path.exists(audio_full_path) and os.path.exists(srt_full_path):
                    with media_placeholder_1.container(border=True):
                        st.markdown("**Bản nghe thử Audio**")
                        st.audio(audio_full_path)
                        with open(audio_full_path, "rb") as file:
                            st.download_button(
                                label=":material/download: Tải Audio (.mp3)",
                                data=file,
                                file_name=f"Audio_{file_basename}.mp3",
                                mime="audio/mp3",
                                use_container_width=True
                            )
                            
                    with media_placeholder_2.container(border=True):
                        st.markdown("**File Phụ đề Subtitle**")
                        with open(srt_full_path, "rb") as file:
                            st.download_button(
                                label=":material/download: Tải Phụ Đề (.srt)",
                                data=file,
                                file_name=f"Subtitle_{file_basename}.srt",
                                mime="text/plain",
                                use_container_width=True
                            )
                    
                # Lặp qua dữ liệu kịch bản để tạo Hình Ảnh
                for enum_idx, (index, row) in enumerate(df_current.iterrows()):
                    if has_error: 
                        break # Dừng file hiện tại nếu có lỗi nghiêm trọng
                            
                    stt = str(row["STT"])
                    noi_dung = str(row["Nội dung"])
                    prompt_keyframe = str(row["Prompt Keyframe"])
                    prompt_motion = str(row["Prompt Motion"])
                        
                    image_path = os.path.join(output_dir, f"Keyframe_{stt}.png")
                    vid_path = os.path.join(output_dir, f"VideoClip_{stt}.mp4")
                        
                    image_files.append(image_path)
                    video_clips.append(vid_path)
                        
                    # --- BƯỚC 3: HÌNH ẢNH KEYFRAME ---
                    if os.path.exists(image_path):
                        pass
                    else:
                        with st.spinner(f":material/image: Rendering Imagen 3 for Scene {stt}..."):
                            # Mocking
                            with open(image_path, "wb") as f: f.write(b"") 
                            # if not generate_keyframe(prompt_keyframe, image_path):
                            #     st.error(f":material/close: Lỗi tạo Hình ảnh STT {stt}. Dừng tiến trình file này.")
                            #     has_error = True
                            #     break
                                

                if has_error:
                    st.warning(f":material/warning: Quá trình xử lý file `{current_filename}` bị gián đoạn. Chạy lại sẽ Resume từ đây.")
                    continue
    
                # --- BƯỚC 4: TẠO VIDEO CHUYỂN ĐỘNG ---
                for i in range(len(image_files)):
                    if has_error: break
                    stt = df_current.iloc[i]["STT"]
                    start_img = image_files[i]
                    end_img = image_files[i+1] if i + 1 < len(image_files) else None 
                    motion_prompt = df_current.iloc[i]["Prompt Motion"]
                    vid_path = video_clips[i]
                        

                    if os.path.exists(vid_path):
                        pass
                    else:
                        with st.spinner(f"Calling Veo API..."):
                            if not generate_video_scene(start_img, end_img, motion_prompt, vid_path):
                                st.error(f":material/close: Lỗi tạo Video STT {stt}. Dừng tiến trình file này.")
                                has_error = True
                                break
                                    

                if has_error:
                    continue
    
                # --- BƯỚC 5: GHÉP NỐI VÀ XUẤT BẢN ---
                output_final = os.path.join(output_dir, f"Video_Hoan_Chinh_{file_basename}.mp4")
                    
                if os.path.exists(output_final):
                    pass
                else:
                    with st.spinner(f"Ghép nối Hình Ảnh 8s (Veo) và Audio Chung..."):
                        try:
                            # Mocking: Ở Bước ghép thực tế (sử dụng MoviePy):
                            # 1. Lấy AudioFileClip(audio_full_path) -> audio_duration (giây)
                            # 2. total_video_duration = len(video_clips) * 8 (vì mỗi clip Veo mặc định 8s)
                            # 3. Nếu total_video_duration < audio_duration:
                            #      -> Duplicate (Loop) các VideoClip cuối cho đến khi >= audio_duration
                            # 4. ghép concatenate_videoclips() cài audio=... và dùng .subclip(0, audio_duration) để khớp vừa vặn hình với tiếng.
                            
                            time.sleep(2)
                            with open(output_final, "wb") as f: f.write(b"")
                        except Exception as e:
                            st.error(f":material/close: Lỗi ghép video MoviePy: {e}")
                            continue
                                
                # Hoàn thành 1 file
                final_results_data.append({
                    "Tên Kịch Bản": current_filename,
                    "Trạng Thái": ":material/check_circle: Hoàn Thành Video",
                    "Đường Dẫn File (Local)": output_final
                })
                # Cập nhật lại khung dữ liệu kết quả tổng
                final_results_placeholder.dataframe(pd.DataFrame(final_results_data), use_container_width=True, hide_index=True)
    
            st.balloons()
            st.success(":material/workspace_premium: HỆ THỐNG ĐÃ XỬ LÝ HOÀN TẤT TẤT CẢ CÁC BATCH!")


if __name__ == "__main__":
    main()
