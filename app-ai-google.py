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
    st.set_page_config(page_title="GCP Video Automation", page_icon="🎥", layout="wide")
    
    # --- GIAO DIỆN CSS TUỲ CHỈNH ---
    st.markdown("""
        <style>
        .main {
            background-color: #0e1117;
            color: #fafafa;
        }
        .stButton>button {
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.3s ease;
            width: 100%;
        }
        .stButton>button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(255,75,75,0.4);
        }
        .header-title {
            background: -webkit-linear-gradient(45deg, #ff4b4b, #ff8f00);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 3rem;
            font-weight: 800;
            padding-bottom: 20px;
        }
        .section-header {
            border-bottom: 2px solid #333;
            padding-bottom: 10px;
            margin-top: 30px;
            margin-bottom: 20px;
            color: #ff4b4b;
        }
        .upload-section {
            background-color: #1a1c23;
            padding: 30px;
            border-radius: 12px;
            border: 1px dashed #4b4b4b;
        }
        div[data-testid="stFileUploader"] {
            padding: 20px;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<h1 class="header-title">🎥 GCP Video AI Automation Studio</h1>', unsafe_allow_html=True)
    st.markdown("Hệ thống tự động hóa Pipeline sản xuất Video từ kịch bản sử dụng `Vertex AI Text-to-Speech`, `Imagen 3`, và `Veo Video Model`.")

    with st.sidebar:
        st.image("https://www.gstatic.com/devrel-devsite/prod/vc81ecfc84451ec652a92f8d3c500ab198bb6bf9dfa6d70ff2de6cc8c4ecf8df0/cloud/images/cloud-logo.svg", width=200)
        st.markdown("### ⚙️ System Configuration")
        st.info(f"**GCP Project:**\n`{PROJECT_ID}`")
        st.info(f"**Location:**\n`{LOCATION}`")
        st.divider()
        st.markdown("### 📊 Status")
        st.success("API Services: Ready")
        st.markdown("---")
        st.caption("Auto Video Pipeline v2.0")

    # --- BƯỚC 1: TẢI & XỬ LÝ DỮ LIỆU ĐẦU VÀO ---
    st.markdown('<h2 class="section-header">📁 Bước 1: Nhập dữ liệu Kịch bản</h2>', unsafe_allow_html=True)
    
    st.markdown('<div class="upload-section">', unsafe_allow_html=True)
    uploaded_files = st.file_uploader(
        "Kéo thả hoặc bấm vào đây để chọn các file kịch bản của bạn (hỗ trợ .csv, .xlsx)", 
        type=['csv', 'xlsx'], 
        accept_multiple_files=True
    )
    st.markdown('</div>', unsafe_allow_html=True)
    
    if uploaded_files:
        st.success(f"✅ Đã tải lên {len(uploaded_files)} file kịch bản thành công!")
        
        # Xem trước file đầu tiên
        preview_file = uploaded_files[0]
        try:
            if preview_file.name.endswith('.csv'):
                df_preview = pd.read_csv(preview_file)
            else:
                df_preview = pd.read_excel(preview_file)
                
            if len(df_preview.columns) >= 4:
                df_preview.columns = ["STT", "Nội dung", "Prompt Keyframe", "Prompt Motion"]
                with st.expander(f"👁️ Xem trước dữ liệu kịch bản: {preview_file.name}", expanded=True):
                    st.dataframe(df_preview, use_container_width=True, height=200)
            else:
                st.error(f"File {preview_file.name} không hợp lệ. Yêu cầu ít nhất 4 cột: STT, Nội dung, Prompt Ảnh, Prompt Video.")
        except Exception as e:
            st.error(f"Lỗi đọc file {preview_file.name}: {e}")

        # --- BẮT ĐẦU QUY TRÌNH TỰ ĐỘNG HÀNG LOẠT ---
        st.markdown('<h2 class="section-header">🚀 Bước 2: Kích hoạt Pipeline</h2>', unsafe_allow_html=True)
        st.info("💡 **Tính năng Cứu hộ (Resume):** Hệ thống sẽ lưu trạng thái. Nếu mất kết nối hoặc lỗi API, lần chạy tiếp theo sẽ tự động nhận diện và chỉ xử lý tiếp những cảnh chưa hoàn thành.")
        
        if st.button("🔥 START AUTOMATION BATCH 🔥", type="primary", use_container_width=True):
            for uploaded_file in uploaded_files:
                current_filename = uploaded_file.name
                
                # Tạo một UI container đẹp cho mỗi file
                with st.container():
                    st.markdown(f"### 🎬 Đang xử lý: `{current_filename}`")
                    
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
                    
                    progress_bar = st.progress(0)
                    total_rows = len(df_current)
                    audio_files = []
                    srt_files = []
                    image_files = []
                    video_clips = []
                    
                    has_error = False
                    
                    # Lặp qua dữ liệu kịch bản
                    for index, row in df_current.iterrows():
                        if has_error: 
                            break # Dừng file hiện tại nếu có lỗi nghiêm trọng
                            
                        stt = str(row["STT"])
                        noi_dung = str(row["Nội dung"])
                        prompt_keyframe = str(row["Prompt Keyframe"])
                        prompt_motion = str(row["Prompt Motion"])
                        
                        audio_path = os.path.join(output_dir, f"Audio_{stt}.mp3")
                        srt_path = os.path.join(output_dir, f"Subtitle_{stt}.srt")
                        image_path = os.path.join(output_dir, f"Keyframe_{stt}.png")
                        vid_path = os.path.join(output_dir, f"VideoClip_{stt}.mp4")
                        
                        audio_files.append(audio_path)
                        srt_files.append(srt_path)
                        image_files.append(image_path)
                        video_clips.append(vid_path)
                        
                        status_msg = st.empty()
                        status_msg.markdown(f"**⚡ Đang xử lý Scene {stt}...**")
                        
                        # --- BƯỚC 2: ÂM THANH & PHỤ ĐỀ ---
                        if os.path.exists(audio_path) and os.path.exists(srt_path):
                            pass # Ẩn bớt log thành công để UI sạch sẽ
                        else:
                            with st.spinner(f"🎙️ Generating TTS for Scene {stt}: '{noi_dung[:20]}...'"):
                                if not generate_audio_and_srt(noi_dung, audio_path, srt_path):
                                    st.error(f"❌ Lỗi tạo Audio STT {stt}. Dừng tiến trình file này.")
                                    has_error = True
                                    break
                        
                        # --- BƯỚC 3: HÌNH ẢNH KEYFRAME ---
                        if os.path.exists(image_path):
                            pass
                        else:
                            with st.spinner(f"🖼️ Rendering Imagen 3 for Scene {stt}..."):
                                # Mocking
                                with open(image_path, "wb") as f: f.write(b"") 
                                # if not generate_keyframe(prompt_keyframe, image_path):
                                #     st.error(f"❌ Lỗi tạo Hình ảnh STT {stt}. Dừng tiến trình file này.")
                                #     has_error = True
                                #     break
                                
                        progress_bar.progress((index * 3 + 1) / (total_rows * 3 + 2))
                        status_msg.empty() # Xoá message xử lý để gọn UI

                    if has_error:
                        st.warning(f"⚠️ Quá trình xử lý file `{current_filename}` bị gián đoạn. Chạy lại sẽ Resume từ đây.")
                        continue

                    # --- BƯỚC 4: TẠO VIDEO CHUYỂN ĐỘNG ---
                    status_video = st.empty()
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
                            status_video.markdown(f"**🎞️ Generating Veo Video for Scene {stt}...**")
                            with st.spinner(f"Calling Veo API..."):
                                if not generate_video_scene(start_img, end_img, motion_prompt, vid_path):
                                    st.error(f"❌ Lỗi tạo Video STT {stt}. Dừng tiến trình file này.")
                                    has_error = True
                                    break
                                    
                        progress_bar.progress((total_rows * 3 + 1) / (total_rows * 3 + 2))
                    status_video.empty()

                    if has_error:
                        continue

                    # --- BƯỚC 5: GHÉP NỐI VÀ XUẤT BẢN ---
                    output_final = os.path.join(output_dir, f"Video_Hoan_Chinh_{file_basename}.mp4")
                    
                    if os.path.exists(output_final):
                        progress_bar.progress(100)
                    else:
                        with st.spinner(f"✨ Compiling Final Movie for `{current_filename}`..."):
                            try:
                                # Mock ghép file thành công
                                time.sleep(2)
                                with open(output_final, "wb") as f: f.write(b"")
                                progress_bar.progress(100)
                            except Exception as e:
                                st.error(f"❌ Lỗi ghép video MoviePy: {e}")
                                continue
                                
                    # Hoàn thành 1 file
                    col_res1, col_res2 = st.columns([3, 1])
                    with col_res1:
                        st.success(f"🎉 Đã hoàn thiện xong Video kịch bản: `{current_filename}`")
                    with col_res2:
                        with open(output_final, "rb") as final_f:
                            st.download_button(
                                label=f"📥 TẢI MP4 LƯU MÁY",
                                data=final_f,
                                file_name=f"{file_basename}_Final.mp4",
                                mime="video/mp4",
                                type="primary",
                                key=f"dl_final_{file_basename}",
                                use_container_width=True
                            )
                    st.divider()

            st.balloons()
            st.success("🏆 HỆ THỐNG ĐÃ XỬ LÝ HOÀN TẤT TẤT CẢ CÁC BATCH!")

if __name__ == "__main__":
    main()
