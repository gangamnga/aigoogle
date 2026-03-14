import streamlit as st
import pandas as pd
import os
import time
import mutagen
from mutagen.mp3 import MP3
from PIL import Image, ImageDraw, ImageFont
import subprocess

# --- Thư viện GCP Google Cloud ---
try:
    from google.cloud import texttospeech
    import vertexai
    from vertexai.preview.vision_models import ImageGenerationModel
    from google import genai
    from google.genai import types
except ImportError:
    pass # Cần: pip install google-cloud-texttospeech google-cloud-aiplatform google-genai

# ==========================================
# CẤU HÌNH GCP
# ==========================================
# Gán trực tiếp file chìa khóa trong code (Không cần cài biến môi trường Windows)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(os.getcwd(), "gcp-key.json")
PROJECT_ID = "video-ai-490214"
LOCATION = "us-central1"

def init_gcp():
    """Khởi tạo Client Google Cloud và Vertex AI"""
    try:
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        return True
    except Exception as e:
        st.error(f"Lỗi khởi tạo GCP: {e}")
        return False

def generate_audio_and_srt(script_lines, output_audio_path, output_srt_path):
    try:
        text = " ".join(script_lines)
        # Gọi API Google Cloud Vertex AI Text-To-Speech
        client = texttospeech.TextToSpeechClient()
        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
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
            
        # Đọc độ dài file mp3 thực tế
        audio = MP3(output_audio_path)
        total_duration = audio.info.length
        
        # Xuất file Phụ đề (.srt) chia tỷ lệ thời gian theo số ký tự
        def format_time(seconds):
            hrs = int(seconds // 3600)
            mins = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            msecs = int((seconds % 1) * 1000)
            return f"{hrs:02d}:{mins:02d}:{secs:02d},{msecs:03d}"

        total_chars = sum(len(line) for line in script_lines)
        current_time = 0.0
        
        with open(output_srt_path, "w", encoding="utf-8") as f:
            for i, line in enumerate(script_lines):
                if total_chars == 0:
                    line_duration = 0
                else:
                    line_duration = (len(line) / total_chars) * total_duration
                
                start_time = current_time
                end_time = current_time + line_duration
                
                f.write(f"{i + 1}\n")
                f.write(f"{format_time(start_time)} --> {format_time(end_time)}\n")
                f.write(f"{line.strip()}\n\n")
                
                current_time = end_time
            
        return True
    except Exception as e:
        # Ghi log rõ ràng lý do 500 Error
        print(f"--- TTS API ERROR ---")
        st.session_state.global_logs.append(("error", f"Lỗi tạo TTS: {str(e)}"))
        return False

def generate_image(prompt, output_path, max_retries=3):
    try:
        model = ImageGenerationModel.from_pretrained("imagen-4.0-generate-001")
    except Exception as e:
        try:
            st.session_state.global_logs.append(("error", f"Lỗi nạp Model Imagen: {str(e)}"))
        except: pass
        return False
        
    for attempt in range(max_retries):
        try:
            response = model.generate_images(
                prompt=prompt,
                number_of_images=1,
                aspect_ratio="9:16"
            )
            response[0].save(output_path)
            return True
        except Exception as e:
            error_msg = str(e)
            if attempt < max_retries - 1:
                wait_time = 20 * (attempt + 1) # 20s, 40s
                print(f"--- IMAGEN API ERROR/RATE LIMIT, RETRYING {attempt+1}/{max_retries} IN {wait_time}s ---")
                try:
                    st.session_state.global_logs.append(("warning", f"Google API Quá tải/Từ chối, đợi {wait_time}s rồi thử lại lần {attempt+1}..."))
                except: pass
                time.sleep(wait_time)
            else:
                print(f"--- IMAGEN API ERROR FINAL ---")
                try:
                    st.session_state.global_logs.append(("error", f"Lỗi tạo Ảnh sau {max_retries} lần thử: {error_msg}"))
                except: pass
                
                # Tự động tạo ảnh Đỏ báo lỗi để thế chỗ (giữ nguyên đường dẫn lưu file)
                try:
                    img = Image.new('RGB', (1080, 1920), color = (255, 238, 240))
                    d = ImageDraw.Draw(img)
                    # Vẽ viền đỏ
                    d.rectangle([(0,0), (1079, 1919)], outline=(255, 75, 75), width=20)
                    img.save(output_path)
                    return False # False để UI biết là lỗi, nhưng file thực tế vẫn được tạo
                except:
                    return False
    return False

def generate_video_clip(prompt, start_img_path, end_img_path, output_mp4_path):
    try:
        # Khởi tạo Client GenAI cho Vertex AI
        client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
        
        # Đọc files thành Bytes
        with open(start_img_path, "rb") as f:
            start_bytes = f.read()
            
        end_bytes = None
        if end_img_path and os.path.exists(end_img_path):
            with open(end_img_path, "rb") as f:
                end_bytes = f.read()
                
        # Cấu hình Start Image
        source = types.Image(imageBytes=start_bytes, mimeType="image/png")
        
        # Cấu hình tham số Video Config
        config_args = {"aspect_ratio": "9:16", "duration_seconds": 8, "person_generation": "ALLOW_ADULT"}
        if end_bytes:
            config_args["last_frame"] = types.Image(imageBytes=end_bytes, mimeType="image/png")
            
        config = types.GenerateVideosConfig(**config_args)
        
        # Gửi Request lên Google Veo
        st.session_state.global_logs.append(("info", f"Đang gửi request tạo Video tới Veo 3.1 cho File: {os.path.basename(output_mp4_path)}..."))
        # Gửi Request lên Google Veo
        operation = client.models.generate_videos(
            model='veo-3.1-generate-001',
            prompt=prompt,
            image=source,
            config=config
        )
        
        # Chờ kết quả trả về (Polling Loop)
        st.session_state.global_logs.append(("warning", f"Đang xếp hàng chờ Video {os.path.basename(output_mp4_path)}. Thường mất 2-4 phút/clip..."))
        while not operation.done:
            time.sleep(15)
            # GenAI SDK expects the operation object, not the name string
            operation = client.operations.get(operation)
            
        # Kiểm tra API Lỗi Backend
        if operation.error:
            st.session_state.global_logs.append(("error", f"Lỗi từ Veo API Backend: {operation.error.message}"))
            return False
            
        # Download file kết quả về máy (Lấy trực tiếp từ Byte trả về của Google)
        video_data = operation.result.generated_videos[0].video
        if video_data.video_bytes:
            with open(output_mp4_path, "wb") as f:
                f.write(video_data.video_bytes)
            st.session_state.global_logs.append(("info", f"Tạo Video thành công. Đã lưu tại: {os.path.basename(output_mp4_path)}"))
            return output_mp4_path
        elif video_data.uri and video_data.uri.startswith("gs://"):
            from google.cloud import storage
            storage_client = storage.Client(project=PROJECT_ID)
            
            # Phân tách gs://bucket_name/path/to/file
            gs_path = video_data.uri.replace("gs://", "")
            bucket_name = gs_path.split("/")[0]
            blob_name = gs_path[len(bucket_name)+1:]
            
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            
            st.session_state.global_logs.append(("info", f"Đang tải Video từ Cloud Storage ({video_data.uri})..."))
            blob.download_to_filename(output_mp4_path)
            
            st.session_state.global_logs.append(("info", f"Tạo Video thành công. Đã tải về: {os.path.basename(output_mp4_path)}"))
            return output_mp4_path
        else:
            st.session_state.global_logs.append(("error", f"Video trống không có nội dung hoặc URI."))
            return False
            
    except Exception as e:
        import traceback
        error_msg = str(e)
        st.session_state.global_logs.append(("error", f"Lỗi ném request Video API: {error_msg} | {traceback.format_exc()}"))
        return False

# Gọi khởi tạo ở mức Global ngay khi app chạy
init_gcp()

st.set_page_config(layout="wide", page_title="Automation Grid UI", page_icon=":material/dashboard:")

# ==========================================
# KHỞI TẠO STATE & HÀM ĐIỀU KHIỂN
# ==========================================
if 'is_running' not in st.session_state:
    st.session_state.is_running = False
if 'is_paused' not in st.session_state:
    st.session_state.is_paused = False
if 'has_started' not in st.session_state:
    st.session_state.has_started = False
if 'global_logs' not in st.session_state:
    st.session_state.global_logs = []
if 'output_dir_path' not in st.session_state:
    st.session_state.output_dir_path = os.path.join(os.getcwd(), "workspace_output")
if 'force_rerun' not in st.session_state:
    st.session_state.force_rerun = False

def click_start():
    if not st.session_state.has_started:
        st.session_state.global_logs = []
    st.session_state.is_running = True
    st.session_state.is_paused = False
    st.session_state.has_started = True
    st.session_state.force_rerun = True

def click_pause():
    st.session_state.is_paused = True
    st.session_state.is_running = False
    st.session_state.force_rerun = True

st.markdown("""
<style>
    /* Google Material Symbols */
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');
    
    .section-title {
        font-size: 1.1rem;
        font-weight: bold;
        color: #333;
        margin-bottom: 15px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .material-symbols-outlined {
        color: #555;
    }
    
    /* Subtle container styling */
    [data-testid="stVerticalBlock"] {
        gap: 1rem;
    }
    
    /* Chỉnh Pagination Component */
    div.stButton > button {
        width: 100%;
        height: 40px;
    }
    
    /* Bảng Section 3 hiển thị Wrapping Text toàn phần */
    .custom-wrapped-table {
        width: 100%;
        border-collapse: collapse;
        font-family: inherit;
        font-size: 14px;
        background-color: white;
    }
    .custom-wrapped-table th {
        background-color: #f8f9fa;
        color: #333;
        font-weight: 600;
        text-align: left !important;
        padding: 12px;
        border: 1px solid #e9ecef;
    }
    .custom-wrapped-table td {
        padding: 12px;
        border: 1px solid #e9ecef;
        vertical-align: top;
        word-wrap: break-word;
        white-space: pre-wrap; /* Giữ lại ngắt dòng của nội dung */
    }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center;'>Video AI Automation</h1>", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

# ----------------- HÀNG 1 (Cao 360px) -----------------
# Cột 1 (1/2 width) chứa Section 1
# Cột 2 (1/2 width) chứa Section 2 
r1_col1, r1_col2 = st.columns([1, 1])

with r1_col1:
    # --- SECTION 1: Tải file lên (Cao 360px) ---
    with st.container(height=360, border=True):
        st.markdown("<div class='section-title'><span class='material-symbols-outlined'>upload_file</span>Upload Files</div>", unsafe_allow_html=True)
        uploaded_files = st.file_uploader("Drag and drop files here", accept_multiple_files=True, label_visibility="collapsed")
        
with r1_col2:
    # --- SECTION 2: Thư mục & Controls (Cao 360px) ---
    with st.container(height=360, border=True):
        st.markdown("<div class='section-title'><span class='material-symbols-outlined'>folder_open</span>Configuration</div>", unsafe_allow_html=True)
        st.text_input("Output Directory", value=st.session_state.output_dir_path, disabled=True, label_visibility="collapsed")
        
        if st.button("Select Folder", icon=":material/download:", use_container_width=True, disabled=st.session_state.has_started):
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            folder_path = filedialog.askdirectory(master=root, initialdir=st.session_state.output_dir_path)
            root.destroy()
            if folder_path:
                st.session_state.output_dir_path = folder_path
                st.rerun()
                
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.session_state.is_running:
            st.button("PROCESSING...", icon=":material/sync:", type="secondary", use_container_width=True, disabled=True)
        elif st.session_state.is_paused:
            st.button("RESUME AUTOMATION", icon=":material/play_arrow:", type="primary", use_container_width=True, on_click=click_start)
        else:
            st.button("START AUTOMATION", icon=":material/play_arrow:", type="primary", use_container_width=True, on_click=click_start)
            
        st.button("PAUSE", icon=":material/pause:", type="secondary", use_container_width=True, disabled=not st.session_state.is_running, on_click=click_pause)

# ----------------- GLOBAL LOGGER SCOPE -----------------
# Khởi tạo Placeholder toàn cục (trước khi vào vòng lặp xử lý logic)
progress_bar_ph = None
succ_text_ph = None
fail_text_ph = None
global_logs_ph = None

def render_global_logs():
    if global_logs_ph is not None:
        with global_logs_ph.container():
            for log_type, msg in st.session_state.global_logs:
                if log_type == "error": st.error(msg)
                elif log_type == "warning": st.warning(msg)
                elif log_type == "success": st.success(msg)
                elif log_type == "info": st.info(msg)

def add_log(log_type, msg):
    st.session_state.global_logs.append((log_type, msg))
    if global_logs_ph is not None:
        render_global_logs()

# ----------------- HÀNG 2 (Cao 800px) -----------------
# Cột 1 (1/2) chứa Section 5 (Background Logs)
# Cột 2 (1/2) chứa Section 4 (Processing Progress)
r2_col1, r2_col2 = st.columns([1, 1])

with r2_col1:
    # --- SECTION 5: Log tiến trình chạy ngầm (Cao 800px) ---
    with st.container(height=800, border=True):
        st.markdown("<div class='section-title'><span class='material-symbols-outlined'>terminal</span>Background Logs</div>", unsafe_allow_html=True)
        global_logs_ph = st.empty()
        global_logs_ph.caption("Background execution logs will appear here...")
            
        # Hiển thị log hiện tại (nếu có sau khi pause/resume)
        if st.session_state.global_logs:
            render_global_logs()

with r2_col2:
    # --- SECTION 4: Tên file & Tiến trình (Cao 800px) ---
    with st.container(height=800, border=True):
        st.markdown("<div class='section-title'><span class='material-symbols-outlined'>monitoring</span>Processing Progress</div>", unsafe_allow_html=True)
        
        progress_bar_ph = st.empty()
        progress_bar_ph.progress(0, text="Ready to process...")
        
        c_succ, c_fail = st.columns(2)
        with c_succ:
            succ_text_ph = st.empty()
            succ_text_ph.success("Completed files: 0")
        with c_fail:
            fail_text_ph = st.empty()
            fail_text_ph.error("Failed files: 0")
# ----------------- HÀNG 3 (Cao 1216px) -----------------
# Cột 1 (3/4) chứa Section 3 (Dataframe)
# Cột 2 (1/4) chứa Section 6 & 7 xếp chồng lên nhau
r3_col1, r3_col2 = st.columns([3, 1])

with r3_col1:
    # --- SECTION 3: Nội dung File 4 cột (Cao 1216px) ---
    with st.container(height=1216, border=True):
        if 'current_filename' not in st.session_state:
            st.session_state.current_filename = ""
            
        file_title_html = f"<span style='position: absolute; left: 50%; transform: translateX(-50%); color: #555; font-weight: normal; font-size: 1rem;'>{st.session_state.current_filename}</span>" if st.session_state.current_filename else ""
        st.markdown(f"<div class='section-title' style='position: relative;'><span class='material-symbols-outlined'>table_view</span>Script Data Contents {file_title_html}</div>", unsafe_allow_html=True)
            
        # Mặc định bảng rỗng nếu chưa có data trong session state
        if 'current_df' not in st.session_state:
            st.session_state.current_df = pd.DataFrame(columns=["Shot ID", "Script Line", "Keyframe Image Prompt", "Image-to-Video Motion Prompt"])
            
        df = st.session_state.current_df
        
        # --- LOGIC PHÂN TRANG GIAO DIỆN ---
        if 'current_page' not in st.session_state:
            st.session_state.current_page = 1
            
        ROWS_PER_PAGE = 9
        total_rows = len(df)
        total_pages = (total_rows - 1) // ROWS_PER_PAGE + 1 if total_rows > 0 else 1
        
        # Lấy dữ liệu của trang hiện tại
        start_idx = (st.session_state.current_page - 1) * ROWS_PER_PAGE
        end_idx = start_idx + ROWS_PER_PAGE
        df_page = df.iloc[start_idx:end_idx]
        
        # Hiển thị bảng dạng HTML tĩnh để wrap text (giãn chiều cao hàng)
        table_html = df_page.to_html(
            index=False,
            escape=True, # Tránh injection mã HTML độc trong kịch bản
            classes="custom-wrapped-table",
            justify="left",
            border=0
        )
        st.markdown(table_html, unsafe_allow_html=True)
        
        # Thanh điều hướng phân trang (Chỉ hiện khi có nhiều hơn 1 trang)
        if total_pages > 1:
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Tính toán phân bổ cột sao cho cụm căn giữa hợp lý
            # Có N nút (Prev, Next, và các số trang) -> dùng list comprehension chia cột
            num_buttons = int(total_pages) + 2
            
            # Dùng 1 cột rỗng 2 bển để đẩy nút vào giữa (Padding)
            cols = st.columns([2] + [1]*num_buttons + [2])
            
            # Nút Prev
            with cols[1]:
                if st.button("‹ Prev", disabled=(st.session_state.current_page == 1), use_container_width=True):
                    st.session_state.current_page -= 1
                    st.rerun()
                    
            # Các nút số trang
            for i in range(1, int(total_pages) + 1):
                with cols[i + 1]:
                    # Nút đang được chọn làm Type="primary" (Màu nổi)
                    btn_type = "primary" if i == st.session_state.current_page else "secondary"
                    if st.button(str(i), type=btn_type, use_container_width=True):
                        st.session_state.current_page = i
                        st.rerun()
                        
            # Nút Next
            with cols[total_pages + 2]:
                if st.button("Next ›", disabled=(st.session_state.current_page == total_pages), use_container_width=True):
                    st.session_state.current_page += 1
                    st.rerun()

with r3_col2:
    # --- SECTION 6: Kịch bản Voiceover (Cao 600px) ---
    with st.container(height=600, border=True):
        st.markdown("<div class='section-title'><span class='material-symbols-outlined'>record_voice_over</span>Voiceover</div>", unsafe_allow_html=True)
        if 'current_voiceover' not in st.session_state:
            st.session_state.current_voiceover = "Waiting for script data..."
        st.text_area("Voiceover Text", st.session_state.current_voiceover, height=450, label_visibility="collapsed", disabled=True)

    # --- SECTION 7: Kịch bản SRT (Cao 600px) ---
    with st.container(height=600, border=True):
        st.markdown("<div class='section-title'><span class='material-symbols-outlined'>subtitles</span>SRT</div>", unsafe_allow_html=True)
        
        # Tạo placeholders cho Audio và SRT để có thể cập nhật ngay lập tức từ Phase 2
        st.session_state.audio_ph = st.empty()
        st.session_state.srt_ph = st.empty()
        
        # Hiển thị trình phát Audio nếu có
        if 'current_audio' in st.session_state and st.session_state.current_audio and os.path.exists(st.session_state.current_audio):
            st.session_state.audio_ph.audio(st.session_state.current_audio, format="audio/mp3")
            srt_area_height = 370  # Thu gọn chiều cao text area để nhường chỗ cho Audio player
        else:
            srt_area_height = 450
            
        if 'current_srt' not in st.session_state:
             st.session_state.current_srt = "Waiting for subtitle generation..."
        st.session_state.srt_ph.text_area("SRT Text", st.session_state.current_srt, height=srt_area_height, label_visibility="collapsed", disabled=True)


# ----------------- HÀNG 3 (Cao 800px) -----------------
# Toàn màn hình (4/4) chứa Section 8
with st.container(height=800, border=True):
    st.markdown("<div class='section-title'><span class='material-symbols-outlined'>image</span>Keyframe Images (From Col 3)</div>", unsafe_allow_html=True)
    
    if 'current_df' in st.session_state and not st.session_state.current_df.empty:
        df_len = len(st.session_state.current_df)
        st.session_state.image_placeholders = []
        
        # Wrapping logic: 12 items per row max
        for row_start in range(0, df_len, 12):
            if row_start > 0:
                st.markdown("<br>", unsafe_allow_html=True)
            cols = st.columns(12)
            batch_len = min(12, df_len - row_start)
            for j in range(batch_len):
                col = cols[j]
                i = row_start + j
                with col:
                    ph = st.empty()
                    if 'current_images' in st.session_state and i < len(st.session_state.current_images):
                        if st.session_state.current_images[i] == "ERROR":
                            ph.markdown(f"<div style='aspect-ratio: 9/16; background-color: #ffeef0; border: 1px dashed #ff4b4b; border-radius: 4px; display: flex; align-items: center; justify-content: center; width: 100%;'><span class='material-symbols-outlined' style='color: #ff4b4b; font-size: 32px;'>broken_image</span><br/><span style='color: #ff4b4b; font-size: 12px; font-weight: bold;'>{i+1}</span></div>", unsafe_allow_html=True)
                        else:
                            ph.image(st.session_state.current_images[i], use_container_width=True)
                    else:
                        ph.markdown(f"<div style='aspect-ratio: 9/16; border: 1px dashed #dcdcdc; border-radius: 4px; display: flex; align-items: center; justify-content: center; width: 100%;'><span style='color: #dcdcdc; font-size: 24px; font-weight: bold;'>{i+1}</span></div>", unsafe_allow_html=True)
                    st.session_state.image_placeholders.append(ph)
    else:
        st.markdown("<p style='color: gray; font-style: italic; font-size: 14px;'>Waiting for data to generate AI images... Upload a script to begin.</p>", unsafe_allow_html=True)


# ----------------- HÀNG 4 (Cao 800px) -----------------
# Toàn màn hình (4/4) chứa Section 9
with st.container(height=800, border=True):
    st.markdown("<div class='section-title'><span class='material-symbols-outlined'>movie</span>Video Scenes (From Col 4)</div>", unsafe_allow_html=True)
    
    if 'current_df' in st.session_state and not st.session_state.current_df.empty:
        df_len = len(st.session_state.current_df)
        st.session_state.video_placeholders = []
        
        # Wrapping logic: 12 items per row max
        for row_start in range(0, df_len, 12):
            if row_start > 0:
                st.markdown("<br>", unsafe_allow_html=True)
            cols = st.columns(12)
            batch_len = min(12, df_len - row_start)
            for j in range(batch_len):
                col = cols[j]
                i = row_start + j
                with col:
                    ph = st.empty()
                    if 'current_videos' in st.session_state and i < len(st.session_state.current_videos):
                        if st.session_state.current_videos[i] == "ERROR":
                            ph.markdown(f"<div style='aspect-ratio: 9/16; background-color: #ffeef0; border: 1px dashed #ff4b4b; border-radius: 4px; display: flex; align-items: center; justify-content: center; width: 100%;'><span class='material-symbols-outlined' style='color: #ff4b4b; font-size: 32px;'>error</span><br/><span style='color: #ff4b4b; font-size: 12px; font-weight: bold;'>Video {i+1} Lỗi</span></div>", unsafe_allow_html=True)
                        else:
                            # User specifically requested NO text, only the raw video/image. 
                            with ph.container():
                                st.video(st.session_state.current_videos[i])
                    else:
                        if i + 1 < df_len:
                            ph.markdown(f"<div style='aspect-ratio: 9/16; border: 1px dashed #dcdcdc; border-radius: 4px; display: flex; align-items: center; justify-content: center; width: 100%;'><span style='color: #dcdcdc; font-size: 16px; font-weight: bold;'>{i+1} + {i+2}</span></div>", unsafe_allow_html=True)
                        else:
                            ph.markdown(f"<div style='aspect-ratio: 9/16; border: 1px dashed #dcdcdc; border-radius: 4px; display: flex; align-items: center; justify-content: center; width: 100%;'><span style='color: #dcdcdc; font-size: 16px; font-weight: bold;'>{i+1} (End)</span></div>", unsafe_allow_html=True)
                    st.session_state.video_placeholders.append(ph)
    else:
        st.markdown("<p style='color: gray; font-style: italic; font-size: 14px;'>Waiting for data to generate videos... Upload a script to begin.</p>", unsafe_allow_html=True)

st.markdown("<hr><p style='text-align: center; color: gray; font-size: 14px;'>© 2026 Video AI Automation - Version 1.0</p>", unsafe_allow_html=True)

# ==========================================
# VÒNG LẶP XỬ LÝ CHÍNH
# ==========================================
if st.session_state.is_running and uploaded_files:
    # Lấy file đầu tiên trong danh sách (chỉ xử lý 1 file tại 1 thời điểm)
    current_file = uploaded_files[0]
    
    # Cập nhật state tên file hiện tại để UI Section 3 render
    st.session_state.current_filename = current_file.name
    
    # Kiểm tra nếu file đã được xử lý hoặc đang được xử lý
    if 'processed_files' not in st.session_state:
        st.session_state.processed_files = {}
    
    status = st.session_state.processed_files.get(current_file.name)
    
    # --- PHASE 1: NẠP DỮ LIỆU & RENDER UI TRƯỚC ---
    if status is None:
        st.session_state.processed_files[current_file.name] = "processing_ui"
        
        # Đọc file
        try:
            df_current = pd.read_csv(current_file) if current_file.name.endswith('.csv') else pd.read_excel(current_file)
            if df_current.shape[1] < 4: raise ValueError("File Excel/CSV phải có đủ ít nhất 4 cột.")
            df_current = df_current.iloc[:, :4] 
            df_current.columns = ["Shot ID", "Script Line", "Keyframe Image Prompt", "Image-to-Video Motion Prompt"]
            
            # Reset UI States
            st.session_state.current_page = 1
            st.session_state.current_df = df_current
            
            # TRÍCH XUẤT TEXT NGAY TẠI PHASE 1 ĐỂ UI RENDER GẤP SECTION 6:
            script_lines = [str(text) for text in df_current["Script Line"].tolist() if str(text).strip()]
            full_text = " ".join(script_lines)
            st.session_state.current_voiceover = full_text
            st.session_state.current_script_lines = script_lines # Lưu tạm để API Phase 2 dùng
            
            st.session_state.current_srt = "Waiting for subtitle generation..."
            st.session_state.current_audio = None
            st.session_state.current_images = [] # Reset danh sách ảnh
            
            add_log("success", f"Đã chuẩn bị xong dữ liệu cho file: {current_file.name}")
            progress_bar_ph.progress(0.2, text=f"Đang chuẩn bị text: {current_file.name}")
            
        except Exception as e:
            add_log("error", f"Lỗi nạp file {current_file.name}: {e}")
            st.session_state.processed_files[current_file.name] = "failed"
            if 'failed_count' not in st.session_state: st.session_state.failed_count = 0
            st.session_state.failed_count += 1
            fail_text_ph.error(f"Failed files: {st.session_state.failed_count}")
            st.session_state.is_running = False
            
        st.rerun() # Bắt buộc vẽ lại bảng ra UI trước

    # --- PHASE 2: GỌI API NẶNG (BLOCKED) ---
    elif status == "processing_ui":
        st.session_state.processed_files[current_file.name] = "processing_api"
        
        try:
            df_current = st.session_state.current_df
            file_basename = os.path.splitext(current_file.name)[0]
            file_output_dir = os.path.join(st.session_state.output_dir_path, file_basename)
            os.makedirs(file_output_dir, exist_ok=True)
            
            # Trích xuất lại dữ liệu đã lưu từ Phase 1 để gọi API
            script_lines = st.session_state.current_script_lines
            progress_bar_ph.progress(0.4, text=f"Đang sinh Audio (TTS): {current_file.name}")
            
            # Tạm dừng 0.1s để UI kịp chớp text -> Gọi API
            time.sleep(0.1)
            
            audio_full_path = os.path.join(file_output_dir, f"{file_basename}.mp3")
            srt_full_path = os.path.join(file_output_dir, f"{file_basename}.srt")
            
            tts_success = generate_audio_and_srt(script_lines, audio_full_path, srt_full_path)
            
            if tts_success:
                st.session_state.current_audio = audio_full_path
                try:
                    with open(srt_full_path, "r", encoding="utf-8") as f:
                        st.session_state.current_srt = f.read()
                except:
                    st.session_state.current_srt = "Could not read generated SRT file."
                
                # Cập nhật UI ngay lập tức thông qua placeholder
                if 'audio_ph' in st.session_state and 'srt_ph' in st.session_state:
                    st.session_state.audio_ph.audio(st.session_state.current_audio, format="audio/mp3")
                    st.session_state.srt_ph.text_area("SRT Text", st.session_state.current_srt, height=370, label_visibility="collapsed", disabled=True)
                
                add_log("success", f"Đã sinh xong Audio & SRT cho file: {current_file.name}")
            else:
                add_log("error", f"Thất bại khi sinh TTS (API 500) cho: {current_file.name}")
                st.session_state.current_srt = "Error generating TTS/SRT."
                raise Exception("Lỗi gọi Google Cloud API (TTS)")
            
            # --- PHASE 3: SINH HÌNH ẢNH (IMAGEN 4) ---
            add_log("info", f"Bắt đầu sinh {len(df_current)} Hình ảnh Keyframe bằng Imagen 4 cho file: {current_file.name}")
            
            for idx, row in df_current.iterrows():
                prompt = row["Keyframe Image Prompt"]
                if not str(prompt).strip():
                    st.session_state.current_images.append(None)
                    continue
                
                img_filename = f"{idx+1:02d}.png"
                img_path = os.path.join(file_output_dir, img_filename)
                
                progress = 0.6 + (0.3 * (idx / len(df_current)))
                progress_bar_ph.progress(progress, text=f"Đang sinh Ảnh {idx+1}/{len(df_current)}...")
                
                img_success = generate_image(prompt, img_path)
                
                if img_success and os.path.exists(img_path):
                    st.session_state.current_images.append(img_path)
                    # Bắn ảnh thẳng lên giao diện qua Placeholder (Không cần rerun toàn trang)
                    if 'image_placeholders' in st.session_state and idx < len(st.session_state.image_placeholders):
                        st.session_state.image_placeholders[idx].image(img_path, use_container_width=True)
                else:
                    # Giao diện UI sẽ hiện Bảng Đỏ báo lỗi
                    st.session_state.current_images.append("ERROR")
                    add_log("error", f"Thất bại sinh ảnh thứ {idx+1}")
                    if 'image_placeholders' in st.session_state and idx < len(st.session_state.image_placeholders):
                        st.session_state.image_placeholders[idx].markdown(f"<div style='aspect-ratio: 9/16; background-color: #ffeef0; border: 1px dashed #ff4b4b; border-radius: 4px; display: flex; align-items: center; justify-content: center; width: 100%;'><span class='material-symbols-outlined' style='color: #ff4b4b; font-size: 32px;'>broken_image</span><br/><span style='color: #ff4b4b; font-size: 12px; font-weight: bold;'>{idx+1}</span></div>", unsafe_allow_html=True)
                        
                # Delay 15s để tránh Vertex AI Quota Rate Limit (RPM)
                time.sleep(15)
                
                     
            add_log("success", f"Đã sinh xong Keyframe Images cho file: {current_file.name}")
            
            # --- PHASE 4: SINH VIDEO (VEO 3.1) ---
            add_log("info", f"Bắt đầu sinh {len(df_current)} đoạn Video bằng Veo 3.1 cho file: {current_file.name}")
            if 'current_videos' not in st.session_state:
                st.session_state.current_videos = []
                
            for idx, row in df_current.iterrows():
                try:
                    prompt = row["Motion Prompt (Optional)"]
                    if pd.isna(prompt) or not str(prompt).strip():
                        prompt = "Motion."
                    else:
                        prompt = str(prompt).strip()
                except KeyError:
                    prompt = "Motion." # Fallback trong trường hợp cột bị đổi tên hoặc không tồn tại

                
                # Xác định Frame
                start_img_path = None
                end_img_path = None
                
                if idx < len(st.session_state.current_images):
                    start_img_path = st.session_state.current_images[idx]
                if idx + 1 < len(st.session_state.current_images):
                    end_img_path = st.session_state.current_images[idx + 1]
                    
                if not start_img_path or start_img_path == "ERROR":
                    st.session_state.current_videos.append("ERROR")
                    continue
                if end_img_path == "ERROR":
                    end_img_path = None # Nếu frame tiếp theo hỏng, coi như không có frame cuối
                    
                video_filename = f"{idx+1:02d}.mp4"
                video_output_path = os.path.join(file_output_dir, video_filename)
                
                progress = 0.9 + (0.1 * (idx / len(df_current)))
                progress_bar_ph.progress(progress, text=f"Đang sinh Video {idx+1}/{len(df_current)}...")
                
                # Gọi Veo API
                video_url = generate_video_clip(prompt, start_img_path, end_img_path, video_output_path)
                
                if video_url:
                    st.session_state.current_videos.append(video_url)
                    # Cập nhật UI thật bằng link GCS 
                    if 'video_placeholders' in st.session_state and idx < len(st.session_state.video_placeholders):
                        with st.session_state.video_placeholders[idx].container():
                            st.video(video_url)
                else:
                    st.session_state.current_videos.append("ERROR")
                    if 'video_placeholders' in st.session_state and idx < len(st.session_state.video_placeholders):
                        st.session_state.video_placeholders[idx].markdown(f"<div style='aspect-ratio: 9/16; background-color: #ffeef0; border: 1px dashed #ff4b4b; border-radius: 4px; display: flex; align-items: center; justify-content: center; width: 100%;'><span class='material-symbols-outlined' style='color: #ff4b4b; font-size: 32px;'>error</span><br/><span style='color: #ff4b4b; font-size: 12px; font-weight: bold;'>Video {idx+1} Lỗi</span></div>", unsafe_allow_html=True)
                        
            add_log("success", f"Đã sinh xong toàn bộ Video cho file: {current_file.name}")
            
            # --- PHASE 6: HOÀN THIỆN VIDEO (FFMPEG) ---
            add_log("info", f"Bắt đầu ghép Video, Audio và Phụ đề thành File hoàn chỉnh...")
            progress_bar_ph.progress(0.95, text=f"Đang biên dịch File Video Cuối...")
            
            # 1. Tạo file videos.txt để FFmpeg concat
            concat_list_path = os.path.join(file_output_dir, "videos.txt")
            valid_videos = [v for v in st.session_state.current_videos if v and v != "ERROR" and os.path.exists(v)]
            
            if not valid_videos:
                add_log("error", "Không có Video thành công nào để ghép.")
                raise Exception("Trống thư viện Video.")
                
            with open(concat_list_path, 'w', encoding='utf-8') as f:
                for video_path in valid_videos:
                    # FFmpeg requires forward slashes or escaped backslashes for text file paths
                    safe_path = video_path.replace('\\', '/')
                    f.write(f"file '{safe_path}'\n")
                    
            # 2. Định nghĩa tên Video cuối
            master_video_name = os.path.splitext(current_file.name)[0] + "_Final.mp4"
            master_video_path = os.path.join(file_output_dir, master_video_name)
            
            audio_path = st.session_state.current_audio
            srt_path = st.session_state.current_srt_file if 'current_srt_file' in st.session_state else os.path.join(file_output_dir, "subtitle.srt")
            
            # 3. Chạy lệnh FFmpeg ghép file
            try:
                # Dùng phức hợp filter `-vf subtitles...` kèm escape Windows Path cho SRT
                safe_srt_path = srt_path.replace('\\', '\\\\').replace(':', '\\:')
                
                ffmpeg_cmd = [
                    "ffmpeg", "-y",
                    "-f", "concat", "-safe", "0", "-i", concat_list_path, # Đầu vào chuỗi video
                    "-i", audio_path,                                     # Đầu vào master audio
                    "-c:v", "libx264", "-c:a", "aac",                     # Chuẩn nén
                    "-vf", f"subtitles='{safe_srt_path}'",                # Hardsub
                    "-shortest",                                          # Cắt Audio/Video cho bằng nhau
                    master_video_path
                ]
                
                subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                add_log("success", f"Video Final đã được tạo thành công: {master_video_name}")
                st.session_state.global_logs.append(("success", f"👉 Sẵn sàng tại: {master_video_path}"))
            except Exception as e:
                add_log("error", f"Tiến trình FFmpeg ghép file gặp lỗi: {str(e)}")
            
            # Đánh dấu thành công và gom số liệu
            st.session_state.processed_files[current_file.name] = "success"
            
            if 'completed_count' not in st.session_state: st.session_state.completed_count = 0
            st.session_state.completed_count += 1
            succ_text_ph.success(f"Completed files: {st.session_state.completed_count}")
            progress_bar_ph.progress(1.0, text=f"Hoàn thành: {current_file.name}")
            time.sleep(1)
            
        except Exception as e:
            error_msg = str(e).encode('utf-8', 'ignore').decode('utf-8')
            add_log("error", f"Lỗi xử lý file {current_file.name}: {error_msg}")
            st.session_state.processed_files[current_file.name] = "failed"
            if 'failed_count' not in st.session_state: st.session_state.failed_count = 0
            st.session_state.failed_count += 1
            fail_text_ph.error(f"Failed files: {st.session_state.failed_count}")
            st.session_state.is_running = False
            
        st.rerun()

    # --- KẾT THÚC CHU TRÌNH ---
    if not uploaded_files or all(status in ["success", "failed"] for status in st.session_state.processed_files.values()):
        st.session_state.is_running = False
        st.session_state.force_rerun = True
