import os
import sys

def batch_rename_prefix(folder_path, old_prefix, new_prefix):
    """
    批量将文件夹内以 old_prefix 开头的文件重命名为以 new_prefix 开头
    """
    # 1. 检查文件夹是否存在
    if not os.path.exists(folder_path):
        print(f"❌ 错误: 找不到文件夹 '{folder_path}'")
        return

    # 获取所有文件
    files = os.listdir(folder_path)
    count = 0

    print(f"📂 正在扫描: {folder_path}")
    print(f"🔄 规则: 将前缀 '{old_prefix}' 替换为 '{new_prefix}'\n")

    for filename in files:
        # 检查文件名是否以 [A] 开头
        if filename.startswith(old_prefix):
            # 构建新文件名
            # 逻辑：新前缀 + 原文件名去掉旧前缀长度后的剩余部分
            # 这样可以防止误伤文件名中间出现的相同字符
            rest_of_name = filename[len(old_prefix):] 
            new_filename = new_prefix + rest_of_name
            
            old_file_path = os.path.join(folder_path, filename)
            new_file_path = os.path.join(folder_path, new_filename)

            # 防止覆盖已存在的文件
            if os.path.exists(new_file_path):
                print(f"⚠️ 跳过: {new_filename} 已存在，防止覆盖。")
                continue

            try:
                os.rename(old_file_path, new_file_path)
                print(f"✅ 重命名: {filename} -> {new_filename}")
                count += 1
            except Exception as e:
                print(f"❌ 失败: {filename} ({e})")
    
    if count == 0:
        print("\n⚠️ 未找到匹配的文件。请检查路径或前缀是否正确。")
    else:
        print(f"\n🎉 完成！共重命名了 {count} 个文件。")

if __name__ == "__main__":
    # 检查参数数量
    if len(sys.argv) < 4:
        print("用法错误。请使用格式:")
        print('python rename_batch.py "[输入文件夹]" "[旧前缀A]" "[新前缀C]"')
        print('示例: python rename_batch.py "./audio" "TrackA" "FileA"')
    else:
        input_folder = sys.argv[1]
        prefix_a = sys.argv[2]
        prefix_c = sys.argv[3]
        
        batch_rename_prefix(input_folder, prefix_a, prefix_c)
