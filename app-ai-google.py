import pandas as pd
import sys
import io

# Đảm bảo in tiếng Việt không bị lỗi trên Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 1. Thay thế 'YOUR_SHEET_ID' bằng ID file Google Sheet công khai của bạn.
# (Bạn có thể lấy ID này trên thanh địa chỉ trình duyệt, nó nằm giữa phần '/d/' và '/edit')
sheet_id = '1h6bQjFVbyW-clHNGuaPmbNesZikkZC0OlPC_MZzxPeY' # Đây là một file Google Sheet mẫu để chạy thử

# 2. Thay đổi đường dẫn để tải trang dưới dạng file CSV
url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv'

print("Đang đọc dữ liệu từ Google Sheet...")

try:
    # 3. Dùng hàm read_csv của pandas để đọc dữ liệu thẳng từ đường dẫn web (URL)
    df = pd.read_csv(url)
    
    # 4. In ra 5 dòng đầu tiên để xem kết quả
    print("\n--- Dữ liệu đọc được thành công ---")
    print(df.head())
    
except Exception as e:
    print(f"\nCó lỗi xảy ra: {e}")
    print("Mẹo: Hãy chắc chắn rằng file Google Sheet của bạn đã được chia sẻ công khai (Anyone with the link).")
