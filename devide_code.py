"""
python devide_code.py --input Unreal_Merged.txt --trunk 5
"""
import os
import argparse
import sys
import math

def parse_arguments():
    parser = argparse.ArgumentParser(description="将合并后的代码大文件均分为 N 个小文件。")
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="输入的大文件路径 (例如: merged_all.txt)"
    )
    parser.add_argument(
        "--trunk", "-t",
        type=int,
        required=True,
        help="需要分割成的份数 (例如: 3)"
    )
    return parser.parse_args()

def find_file_boundaries(lines):
    """
    寻找所有合法的文件开始边界。
    依据：行首为 '[' 且上一行为空行（或文件开头）。
    返回一个包含行号索引的列表。
    """
    boundaries = [0] # 第0行始终是起始点
    total_lines = len(lines)
    
    for i in range(1, total_lines):
        line = lines[i]
        # 简单的启发式规则：如果一行以 '[' 开头，且大概率是文件头
        # 之前的脚本生成的格式是： [path/to/file]
        if line.startswith("["):
            # 检查是否真的是文件头（比如后面有换行符），且通常前一行是空行
            # 这里宽松一点，只要是 '[' 开头就视为潜在分割点
            boundaries.append(i)
            
    boundaries.append(total_lines) # 添加文件末尾作为最后的边界
    return boundaries

def find_closest(sorted_list, target):
    """
    在有序列表中找到最接近 target 的数值。
    """
    # 如果列表为空
    if not sorted_list:
        return 0
    
    # 使用简单的遍历查找（对于几十万行代码的边界列表，性能足够）
    closest_val = sorted_list[0]
    min_diff = abs(target - closest_val)
    
    for val in sorted_list:
        diff = abs(target - val)
        if diff < min_diff:
            min_diff = diff
            closest_val = val
        # 优化：因为列表是有序的，如果 diff 开始变大，说明已经过了最优解
        if diff > min_diff:
            break
            
    return closest_val

def split_file(input_path, trunk_count):
    # 1. 读取所有内容
    if not os.path.exists(input_path):
        print(f"错误: 文件 {input_path} 不存在。")
        sys.exit(1)

    print(f"正在读取文件: {input_path} ...")
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        print("警告: UTF-8 读取失败，尝试 Latin-1...")
        with open(input_path, 'r', encoding='latin-1') as f:
            lines = f.readlines()

    total_lines = len(lines)
    print(f"文件总行数: {total_lines}")

    if total_lines == 0:
        print("错误: 文件为空。")
        sys.exit(1)

    # 2. 找到所有合法的“文件头”位置
    boundaries = find_file_boundaries(lines)
    
    # 3. 计算理想的切割点
    # 例如：100行分3份，理想点是 33.3, 66.6
    split_indices = [0]
    ideal_chunk_size = total_lines / trunk_count
    
    current_start_boundary_index = 0 # 指向 boundaries 列表的索引
    
    for i in range(1, trunk_count):
        ideal_target = i * ideal_chunk_size
        
        # 在 boundaries 列表中找到最接近 ideal_target 的行号
        # 这是一个关键点：我们只能在 boundaries 里面选位置
        best_split_line = find_closest(boundaries, ideal_target)
        
        # 防止重复切分（如果文件太小，trunk太大，可能多个trunk指向同一个位置）
        if best_split_line > split_indices[-1]:
            split_indices.append(best_split_line)
    
    split_indices.append(total_lines)

    # 去重并排序（防止 edge case）
    split_indices = sorted(list(set(split_indices)))

    # 4. 执行写入
    base_name, ext = os.path.splitext(input_path)
    
    print("-" * 30)
    # 实际切分的文件数可能少于 trunk (例如文件很少但trunk很大)
    actual_parts = len(split_indices) - 1
    
    for i in range(actual_parts):
        start_line = split_indices[i]
        end_line = split_indices[i+1]
        
        # 构造新文件名： filename-1.txt, filename-2.txt
        output_filename = f"{base_name}-{i+1}{ext}"
        
        chunk_lines = lines[start_line:end_line]
        
        if not chunk_lines:
            continue
            
        try:
            with open(output_filename, 'w', encoding='utf-8') as f_out:
                f_out.writelines(chunk_lines)
            
            print(f"生成: {output_filename}")
            print(f"      范围: {start_line+1}行 - {end_line}行 (共 {len(chunk_lines)} 行)")
            
        except IOError as e:
            print(f"错误: 无法写入 {output_filename}: {e}")

    print("-" * 30)
    print("分割完成。")

if __name__ == "__main__":
    args = parse_arguments()
    split_file(args.input, args.trunk)
