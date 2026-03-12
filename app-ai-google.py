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
            selected_file = st.selectbox("Xem trước dữ liệu của file:", st.session_state['files'])
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

    # --- BẮT ĐẦU QUY TRÌNH TỰ ĐỘNG HÀNG LOẠT ---
    st.divider()
    if 'files' in st.session_state and len(st.session_state['files']) > 0:
        st.write("### 🚀 Tiến trình tạo Video tự động")
        st.info("Hệ thống sẽ xử lý lần lượt từng file trong thư mục. Cơ chế thông minh: 'Lỗi đến đâu, làm lại đến đó'. Các file/bước đã hoàn thành sẽ tự động bị bỏ qua nếu chạy lại.")
        
        if st.button("XÁC NHẬN XỬ LÝ TOÀN BỘ THƯ MỤC", type="primary"):
            for current_file in st.session_state['files']:
                st.markdown(f"## 🎬 Đang xử lý kịch bản: `{current_file}`")
                file_path = os.path.join(st.session_state['folder_path'], current_file)
                
                # 1. Đọc dữ liệu
                try:
                    df_current = pd.read_csv(file_path) if current_file.endswith('.csv') else pd.read_excel(file_path)
                    if len(df_current.columns) < 4:
                        st.error(f"File {current_file} không đủ 4 cột. Bỏ qua.")
                        continue
                    df_current.columns = ["STT", "Nội dung", "Prompt Keyframe", "Prompt Motion"]
                except Exception as e:
                    st.error(f"Lỗi đọc file {current_file}: {e}")
                    continue
                
                # 2. Tạo thư mục output riêng cho file này
                file_basename = os.path.splitext(current_file)[0]
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
                    
                    st.write(f"**⚡ Đang xử lý STT {stt}...**")
                    
                    # --- BƯỚC 2: ÂM THANH & PHỤ ĐỀ ---
                    if os.path.exists(audio_path) and os.path.exists(srt_path):
                        st.success(f"✔️ Đã có Audio & Subtitle cho STT {stt}. Bỏ qua...")
                    else:
                        with st.spinner(f"Chạy Vertex AI TTS: '{noi_dung[:20]}...'"):
                            if not generate_audio_and_srt(noi_dung, audio_path, srt_path):
                                st.error(f"❌ Lỗi tạo Audio STT {stt}. Dừng tiến trình file này.")
                                has_error = True
                                break
                    
                    # --- BƯỚC 3: HÌNH ẢNH KEYFRAME ---
                    if os.path.exists(image_path):
                        st.success(f"✔️ Đã có Hình ảnh cho STT {stt}. Bỏ qua...")
                    else:
                        with st.spinner(f"Render ảnh Imagen 3: '{prompt_keyframe[:30]}...'"):
                            # (Tạm thời mock, thực tế sẽ gọi generate_keyframe)
                            with open(image_path, "wb") as f: f.write(b"") # Mocking
                            # if not generate_keyframe(prompt_keyframe, image_path):
                            #     st.error(f"❌ Lỗi tạo Hình ảnh STT {stt}. Dừng tiến trình file này.")
                            #     has_error = True
                            #     break
                            
                    progress_bar.progress((index * 3 + 1) / (total_rows * 3 + 2))

                if has_error:
                    st.warning(f"⚠️ Quá trình xử lý file `{current_file}` bị gián đoạn. Lần sau chạy lại sẽ tiếp tục từ bước bị lỗi.")
                    continue

                # --- BƯỚC 4: TẠO VIDEO CHUYỂN ĐỘNG ---
                st.write(f"**🎬 Tạo Video Chuyển động cho `{current_file}`**")
                for i in range(len(image_files)):
                    if has_error: break
                    stt = df_current.iloc[i]["STT"]
                    start_img = image_files[i]
                    end_img = image_files[i+1] if i + 1 < len(image_files) else None 
                    motion_prompt = df_current.iloc[i]["Prompt Motion"]
                    vid_path = video_clips[i]
                    
                    if os.path.exists(vid_path):
                        st.success(f"✔️ Đã có Video Clip cho STT {stt}. Bỏ qua...")
                    else:
                        with st.spinner(f"Tạo Video Scene bằng API Veo cho STT {stt}..."):
                            if not generate_video_scene(start_img, end_img, motion_prompt, vid_path):
                                st.error(f"❌ Lỗi tạo Video STT {stt}. Dừng tiến trình file này.")
                                has_error = True
                                break
                                
                    progress_bar.progress((total_rows * 3 + 1) / (total_rows * 3 + 2))

                if has_error:
                    st.warning(f"⚠️ Quá trình xử lý file `{current_file}` bị gián đoạn ở bước tạo Video.")
                    continue

                # --- BƯỚC 5: GHÉP NỐI VÀ XUẤT BẢN ---
                st.write(f"**🎞️ Ghép & Xuất Video cho `{current_file}`**")
                output_final = os.path.join(output_dir, f"Video_Hoan_Chinh_{file_basename}.mp4")
                
                if os.path.exists(output_final):
                    st.success(f"✔️ File `{output_final}` đã hoàn thành từ trước. Không cần ghép lại.")
                    progress_bar.progress(100)
                else:
                    with st.spinner("Đang sử dụng MoviePy để concatenate các cảnh..."):
                        try:
                            # Mock ghép file thành công
                            time.sleep(2)
                            with open(output_final, "wb") as f: f.write(b"")
                            
                            progress_bar.progress(100)
                            st.success(f"🎉 Khởi tạo và ghép nối trọn vẹn kịch bản `{current_file}`!")
                        except Exception as e:
                            st.error(f"❌ Lỗi khi ghép video bằng MoviePy: {e}")
                            continue
                            
                # Nút tải xuống hiển thị ngay trên UI khi xong 1 file
                with open(output_final, "rb") as final_f:
                    st.download_button(
                        label=f"📥 TẢI XUỐNG VIDEO ({file_basename}.mp4)",
                        data=final_f,
                        file_name=f"{file_basename}_Final.mp4",
                        mime="video/mp4",
                        type="primary",
                        key=f"dl_final_{file_basename}"
                    )
                    
            st.balloons()
            st.success("✅ ĐÃ XỬ LÝ XONG TOÀN BỘ CÁC FILE TRONG THƯ MỤC!")

if __name__ == "__main__":
    main()
