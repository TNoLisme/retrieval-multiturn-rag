import os
import sys
import pandas as pd

if sys.platform.startswith('win'):
    os.system('chcp 65001 > nul')
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    file_new = os.path.join(project_root, "data", "Kiem_tra_tri_thuc_VAS.xlsx")
    file_old = os.path.join(project_root, "data", "Kiem_tra_tri_thuc_VAS_old.xlsx")
    
    if not os.path.exists(file_new):
        print(f"File mới không tồn tại tại: {file_new}")
        return
    if not os.path.exists(file_old):
        print(f"File cũ không tồn tại tại: {file_old}")
        return
        
    print(f"Đang đọc file mới: {os.path.basename(file_new)}")
    df_new = pd.read_excel(file_new)
    print(f"Đang đọc file cũ: {os.path.basename(file_old)}")
    df_old = pd.read_excel(file_old)
    
    print("\n" + "=" * 50)
    print(" KẾT QUẢ SO SÁNH THÔNG TIN CHUNG (ĐÃ XỬ LÝ NAN)")
    print("=" * 50)
    print(f"Kích thước file cũ (VAS_old): {df_old.shape[0]} dòng, {df_old.shape[1]} cột")
    print(f"Kích thước file mới (VAS):     {df_new.shape[0]} dòng, {df_new.shape[1]} cột")
    
    cols_old = set(df_old.columns)
    cols_new = set(df_new.columns)
    
    print("\n1. So sánh Cột:")
    if cols_old == cols_new:
        print("  - Danh sách cột trùng khớp hoàn toàn.")
        print(f"  - Các cột: {list(df_new.columns)}")
    else:
        print(f"  - Cột chỉ có ở file cũ: {list(cols_old - cols_new)}")
        print(f"  - Cột chỉ có ở file mới: {list(cols_new - cols_old)}")
        
    print("\n2. So sánh Nội dung chi tiết:")
    if 'Nội dung Chunk' in df_new.columns and 'Nội dung Chunk' in df_old.columns:
        df_new_clean = df_new.copy()
        df_old_clean = df_old.copy()
        
        # Điền chuỗi rỗng vào các ô trống (NaN) để tránh lỗi so sánh NaN != NaN
        df_new_clean = df_new_clean.fillna("")
        df_old_clean = df_old_clean.fillna("")
        
        df_new_clean['Nội dung Clean'] = df_new_clean['Nội dung Chunk'].astype(str).str.strip().str.replace(r'\s+', ' ', regex=True)
        df_old_clean['Nội dung Clean'] = df_old_clean['Nội dung Chunk'].astype(str).str.strip().str.replace(r'\s+', ' ', regex=True)
        
        chunks_new = set(df_new_clean['Nội dung Clean'])
        chunks_old = set(df_old_clean['Nội dung Clean'])
        
        common_chunks = chunks_new.intersection(chunks_old)
        only_new = chunks_new - chunks_old
        only_old = chunks_old - chunks_new
        
        print(f"  - Số lượng Chunks trùng khớp hoàn toàn: {len(common_chunks)}")
        print(f"  - Số lượng Chunks chỉ có ở file mới:     {len(only_new)}")
        print(f"  - Số lượng Chunks chỉ có ở file cũ:      {len(only_old)}")
        
        # Kiểm tra sự khác biệt về Metadata thực tế của các chunk trùng khớp
        merged = pd.merge(df_old_clean, df_new_clean, on='Nội dung Clean', suffixes=('_old', '_new'))
        common_meta_cols = [c for c in df_new.columns if c not in ['Nội dung Chunk', 'Nội dung Clean', 'Độ dài (ký tự)']]
        
        diffs = []
        for col in common_meta_cols:
            col_old = f"{col}_old"
            col_new = f"{col}_new"
            if col_old in merged.columns and col_new in merged.columns:
                mismatches = merged[merged[col_old].astype(str) != merged[col_new].astype(str)]
                if not mismatches.empty:
                    diffs.append((col, len(mismatches), mismatches))
                    
        print("\n3. Kiểm tra tính đồng nhất Metadata thực tế:")
        if diffs:
            for col, count, mismatches_df in diffs:
                print(f"  - Cột '{col}': có {count} dòng bị khác biệt về giá trị metadata thực tế.")
                # Ví dụ cụ thể
                example = mismatches_df.iloc[0]
                print(f"    Ví dụ: Chunk '{example['Nội dung Clean'][:60]}...'")
                print(f"           Cũ: '{example[f'{col}_old']}' ➔ Mới: '{example[f'{col}_new']}'")
        else:
            print("  - Tuyệt vời! Các chunk trùng khớp có giá trị metadata hoàn toàn đồng nhất 100%.")
            
    else:
        print("  - Không tìm thấy cột 'Nội dung Chunk' ở một trong hai file để so khớp.")

if __name__ == "__main__":
    main()
