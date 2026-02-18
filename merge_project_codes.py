"""
基本运行（合并默认类型的代码文件,使用默认的忽略列表）：
python merge_project_codes.py -s ./my_project -o ./output.txt

自定义忽略特定的文件夹（例如忽略 tests 和 docs 文件夹）：
python merge_project_codes.py -s ./my_project -o ./output.txt -i tests docs temp_folder

指定后缀并忽略特定目录：
python merge_project_codes.py -s ./src -o ./merged.txt -e .py -i __pycache__ migrations

python merge_project_codes.py -s ./SonarBanana -o ./SonarBanana.txt -e .kt .rs .toml .kts .properties -i build
"""
import os
import argparse
import sys

def parse_arguments():
    """
    解析命令行参数。
    """
    parser = argparse.ArgumentParser(description="将指定目录下的代码文件合并为一个文本文件。")
    
    parser.add_argument(
        "--source_directory", "-s",
        required=True,
        help="需要遍历的源目录路径。"
    )
    
    parser.add_argument(
        "--output_file", "-o",
        required=True,
        help="合并后的输出文件路径（例如：merged_code.txt）。"
    )
    
    parser.add_argument(
        "--extensions", "-e",
        nargs="+",
        default=[".py", ".java", ".c", ".cpp", ".h", ".js", ".ts", ".html", ".css", ".md"],
        help="需要合并的文件后缀列表（例如：.py .cpp）。默认为常见代码文件。"
    )

    parser.add_argument(
        "--ignored_directories", "-i",
        nargs="+",
        default=[".git", ".gradle", ".kotlin", ".idea", ".vscode", "__pycache__", "node_modules", "build", "gradle", ".cago", "dist", "target", "venv"],
        help="需要忽略的文件夹名称列表。程序将不会进入这些文件夹。"
    )
    
    return parser.parse_args()

def get_file_content_with_formatting(file_path, relative_path):
    """
    读取单个文件内容并按指定格式格式化。
    
    格式要求：
    第一行：相对路径
    后续行：第N行    代码内容
    """
    formatted_lines = []
    
    # 添加文件路径头信息
    formatted_lines.append(f"{relative_path}\n")
    
    try:
        # 尝试以 UTF-8 读取
        with open(file_path, 'r', encoding='utf-8') as source_file:
            lines = source_file.readlines()
    except UnicodeDecodeError:
        try:
            # 备用方案：尝试以 Latin-1 读取（通常能读取所有字节流，虽然非ASCII字符可能乱码，但不会崩溃）
            # 或者您可以根据实际情况修改为 'gbk'
            print(f"警告: 文件 {file_path} 不是 UTF-8 编码，尝试使用 latin-1 读取。")
            with open(file_path, 'r', encoding='latin-1') as source_file:
                lines = source_file.readlines()
        except Exception as reading_error:
            print(f"错误: 无法读取文件 {file_path}。原因: {reading_error}")
            return None

    # 遍历每一行进行格式化
    for index, line_content in enumerate(lines):
        # 行号从1开始
        line_number = index + 1
        # 去除行末尾的换行符，防止写入时产生双重换行，稍后手动添加
        clean_content = line_content.rstrip('\n')
        # 格式：第N行 + 4个空格 + 内容
        formatted_line = f"第{line_number}行    {clean_content}\n"
        formatted_lines.append(formatted_line)
    
    # 在文件结束添加一个分隔符或空行，便于阅读
    formatted_lines.append("\n\n")
    
    return formatted_lines

def merge_code_files(source_directory, output_file_path, allowed_extensions, ignored_directories):
    """
    主逻辑：遍历目录并写入合并文件。
    """
    # 转换为绝对路径以确保处理正确
    abs_source_directory = os.path.abspath(source_directory)

    # 将忽略列表转换为集合，提高查找效率
    ignored_directories_set = set(ignored_directories)
    
    # 统计信息
    processed_file_count = 0
    
    try:
        # 使用 'w' 模式打开输出文件，如果有旧文件则覆盖
        with open(output_file_path, 'w', encoding='utf-8') as output_file:
            
            # os.walk 递归遍历目录
            # topdown=True 是默认值，但在修改 dirs 时必须显式依赖此行为
            for root, dirs, files in os.walk(abs_source_directory, topdown=True):

                # -------------------------------------------------
                # 关键修改：过滤掉不需要遍历的目录
                # 必须使用切片赋值 (dirs[:]) 来原地修改列表
                # 这样 os.walk 在下一次迭代时就会跳过被移除的目录
                # -------------------------------------------------
                dirs[:] = [d for d in dirs if d not in ignored_directories_set]

                for filename in files:
                    # 检查文件后缀
                    if not any(filename.endswith(ext) for ext in allowed_extensions):
                        continue
                    
                    full_file_path = os.path.join(root, filename)
                    
                    # 获取相对于源目录的路径
                    relative_path = os.path.relpath(full_file_path, start=abs_source_directory)
                    
                    # 获取格式化后的内容
                    formatted_content = get_file_content_with_formatting(full_file_path, relative_path)
                    
                    if formatted_content:
                        output_file.writelines(formatted_content)
                        processed_file_count += 1
                        print(f"已处理: {relative_path}")
                        
    except IOError as io_error:
        print(f"致命错误: 无法写入输出文件 {output_file_path}。原因: {io_error}")
        sys.exit(1)
        
    print("-" * 30)
    print(f"合并完成！共处理了 {processed_file_count} 个文件。")
    print(f"忽略的目录名称: {', '.join(ignored_directories)}")
    print(f"输出文件位于: {os.path.abspath(output_file_path)}")

if __name__ == "__main__":
    args = parse_arguments()
    
    # 校验源目录是否存在
    if not os.path.isdir(args.source_directory):
        print(f"错误: 源目录 '{args.source_directory}' 不存在。")
        sys.exit(1)
        
    merge_code_files(
        args.source_directory,
        args.output_file,
        args.extensions,
        args.ignored_directories
    )
