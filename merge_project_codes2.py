import os
import argparse
import sys
from collections import defaultdict

"""
python merge_project_codes2.py --scan "/home/rakuse-06/Workspace/UnrealEngine-5.7.3-release/" --o /home/rakuse-06/Workspace/dics.ini
python merge_project_codes2.py --merge "/home/rakuse-06/Workspace/UnrealEngine-5.7.3-release/" --in_ini /home/rakuse-06/Workspace/dics.ini \
                               --o /home/rakuse-06/Unreal_merged \
                                -i "/home/rakuse-06/Workspace/UnrealEngine-5.7.3-release/Engine/Source/ThirdParty/" \
                                   "/home/rakuse-06/Workspace/UnrealEngine-5.7.3-release/Engine/Source/Runtime/" \
                                   "/home/rakuse-06/Workspace/UnrealEngine-5.7.3-release/Engine/Source/ThirdParty/ICU/icu4c-64_1/source/test"
"""

# ==========================================
# 配置常量
# ==========================================
DEFAULT_EXTENSIONS = [
    ".py", ".java", ".c", ".cpp", ".h", ".js", 
    ".ts", ".html", ".css", ".md", ".sh", ".xml", ".kt", 
    ".uproject", ".ini", ".json", ".txt", ".ush", ".tps",
    ".usf", ".hlsl", ".cs", ".uplugin"
]
DEFAULT_IGNORES = [
    ".git", ".idea", ".vscode", "__pycache__", 
    "node_modules", "build", "dist", "venv", ".gradle", "test",
    "target", "Binaries", "Intermediate", "Saved", "DerivedDataCache"
]
OTHERS_FILENAME = "Others.txt"

# ==========================================
# 核心功能类
# ==========================================

class CodeMerger:
    def __init__(self, root_dir, extensions, ignores):
        self.root_dir = os.path.abspath(root_dir)
        self.extensions = extensions

        # --- 关键修复：将忽略列表拆分为“名称匹配”和“路径匹配” ---
        self.ignore_names = set()
        self.ignore_paths = set()
        
        for item in ignores:
            item = item.strip()
            # 移除路径末尾的斜杠，避免匹配失败
            item = item.rstrip(os.sep)
            
            # 判断逻辑：如果包含路径分隔符，或者是一个绝对路径，则视为“路径匹配”
            if os.sep in item or os.path.isabs(item):
                # 转换为绝对路径进行存储
                if os.path.isabs(item):
                    abs_p = os.path.normpath(item)
                else:
                    # 如果是相对路径，则将其基于 root_dir 转为绝对路径
                    abs_p = os.path.normpath(os.path.abspath(os.path.join(self.root_dir, item)))
                self.ignore_paths.add(abs_p)
            else:
                # 否则视为纯文件夹名（如 .git）
                self.ignore_names.add(item)
        
        # 调试输出
        print(f"工作目录: {self.root_dir}")
        if self.ignore_names:
            print(f"全局忽略名称: {', '.join(self.ignore_names)}")
        if self.ignore_paths:
            print(f"路径忽略列表 ({len(self.ignore_paths)}个):")
            for p in self.ignore_paths:
                print(f"  - {p}")
        print("-" * 30)

    def _should_ignore(self, current_root, dir_name):
        """
        判断是否忽略该目录
        current_root: 当前遍历到的父目录绝对路径
        dir_name: 文件夹名称
        """
        # 1. 检查纯名称 (例如 "Intermediate")
        if dir_name in self.ignore_names:
            return True
        
        # 2. 检查绝对路径
        # 构造当前目录的完整绝对路径
        full_dir_path = os.path.normpath(os.path.join(current_root, dir_name))
        
        # 精确匹配：如果当前路径在忽略列表中
        if full_dir_path in self.ignore_paths:
            return True
            
        # 注意：不需要检查 "是否是忽略路径的子目录"，
        # 因为 os.walk 的 dirs[:] 机制会直接阻止进入父级忽略目录，
        # 所以子目录根本不会被遍历到。
        
        return False

    def _is_target_file(self, filename):
        return any(filename.endswith(ext) for ext in self.extensions)

    def scan_to_ini(self, output_ini_path):
        """
        Step 1: 扫描目录并生成层级化的 INI 文件
        """
        layers = defaultdict(list)
        
        print("正在扫描目录结构...")
        # 遍历目录
        for root, dirs, _ in os.walk(self.root_dir):
            # 过滤忽略目录
            dirs[:] = [d for d in dirs if not self._should_ignore(root, d)]
            
            rel_path = os.path.relpath(root, self.root_dir)
            if rel_path == ".":
                depth = 1 # 根目录视为第一层（或者叫layer0，按用户习惯）
            else:
                # 计算路径分隔符的数量来确定深度
                depth = rel_path.count(os.sep) + 2

            # 统一使用 Linux 风格路径分隔符写入 INI，便于跨平台阅读
            normalized_path = "./" + rel_path.replace("\\", "/")
            if rel_path == ".":
                normalized_path = "."
                
            layers[depth].append(normalized_path)

        # 写入文件
        try:
            with open(output_ini_path, 'w', encoding='utf-8') as f:
                f.write("[root]\n")
                f.write(f"{self.root_dir}\n\n")
                
                # 按层级排序输出
                sorted_layers = sorted(layers.keys())
                for layer in sorted_layers:
                    f.write(f"[layer{layer}]\n")
                    # 同一层级按字母序排序
                    for path in sorted(layers[layer]):
                        f.write(f"{path}\n")
                    f.write("\n")
            print(f"扫描完成。配置文件已生成至: {output_ini_path}")
        except IOError as e:
            print(f"错误: 无法写入 INI 文件。{e}")
            sys.exit(1)

    def _parse_ini(self, ini_path):
        """
        解析 INI 文件，提取合并规则。
        返回: (merge_rules_dict, parse_success)
        """
        merge_targets = []
        
        if not os.path.exists(ini_path):
            print(f"错误: 找不到 INI 文件: {ini_path}")
            sys.exit(1)

        with open(ini_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 识别被标记的行 (以 ## 开头)
                if line.startswith("##"):
                    # 去掉 ## 并清理空格
                    raw_path = line[2:].strip()
                    if raw_path:
                        # 规范化路径
                        norm_path = os.path.normpath(raw_path)
                        merge_targets.append(norm_path)
        
        # 排序规则：路径长的排前面 (Most Specific First)
        # 这样确保子目录优先被匹配
        merge_targets.sort(key=lambda x: len(x), reverse=True)
        return merge_targets

    def _get_file_content(self, file_path, rel_path):
        """读取并格式化文件内容"""
        lines_buffer = []
        lines_buffer.append(f"[{rel_path}]\n")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content_lines = f.readlines()
        except UnicodeDecodeError:
            try:
                # 降级尝试
                with open(file_path, 'r', encoding='latin-1') as f:
                    content_lines = f.readlines()
            except Exception:
                return [f"ERROR: 无法读取文件 {rel_path}\n\n"]

        for idx, line in enumerate(content_lines):
            line_num = idx + 1
            if line_num > 99999:
                print(f"致命错误: 文件 {rel_path} 超过 99999 行，无法格式化。")
                sys.exit(1)
            
            # 格式：00001    内容
            formatted = f"{line_num:05d}    {line.rstrip()}\n"
            lines_buffer.append(formatted)
        
        lines_buffer.append("\n\n") # 文件间空行
        return lines_buffer

    def merge_files(self, ini_path, output_dir):
        """
        Step 3: 根据 INI 规则执行合并
        """
        targets = self._parse_ini(ini_path)
        
        # 准备输出缓冲区: key=输出文件名, value=内容列表
        output_buffers = defaultdict(list)
        
        # 确保输出目录存在
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        print("正在扫描并合并代码...")
        
        file_count = 0

        for root, dirs, files in os.walk(self.root_dir):
            # -----------------------------------------------------------
            # 关键点：在 Merge 阶段同样执行过滤
            # 如果用户在 Step 3 加了 -i tests，这里会直接将 tests 目录移除
            # 即使 INI 里写了 ## ./tests，os.walk 也不会进入，因此不会生成文件
            # -----------------------------------------------------------
            dirs[:] = [d for d in dirs if not self._should_ignore(root, d)]
            
            for filename in files:
                if not self._is_target_file(filename):
                    continue

                abs_path = os.path.join(root, filename)
                # 获取相对于扫描根目录的路径
                rel_path_from_root = os.path.relpath(abs_path, self.root_dir)
                
                # 判定归属
                # 检查当前文件的目录路径是否以某个 target 开头
                # 这里的逻辑是：rel_path_from_root 的目录部分是否匹配 targets
                file_dir = os.path.dirname(rel_path_from_root)
                # 统一为 ./ 形式以匹配 INI 中的写法
                check_path = os.path.join(".", file_dir) 
                if file_dir == "": check_path = "."

                target_filename = OTHERS_FILENAME
                
                for target_path in targets:
                    # 将 target 路径 (如 ./Denman1) 和当前文件路径比较
                    # 使用 os.path.commonpath 比较健壮，或者简单的字符串前缀
                    # 这里我们需要标准化比较
                    target_norm = os.path.normpath(target_path)
                    check_norm = os.path.normpath(check_path)
                    
                    # 如果 target_norm 是 check_norm 的前缀 (或者是同一目录)
                    # 比如 check_norm 是 Denman1/src, target 是 Denman1
                    if check_norm == target_norm or \
                       check_norm.startswith(target_norm + os.sep):
                        
                        # 找到了归属 (因为targets已经按长度降序，第一个匹配的就是最深的)
                        # 生成文件名: ./Denman1/src -> Denman1_src.txt
                        # 去掉开头的 ./ 或 .
                        clean_name = target_norm
                        if clean_name.startswith("." + os.sep):
                            clean_name = clean_name[2:]
                        elif clean_name == ".":
                            clean_name = "Root"
                        
                        safe_name = clean_name.replace(os.sep, "_") + ".txt"
                        target_filename = safe_name
                        break
                
                # 读取并添加内容
                formatted_lines = self._get_file_content(
                    abs_path, rel_path_from_root
                )
                output_buffers[target_filename].extend(formatted_lines)
                file_count += 1

        # 写入磁盘
        print("\n正在写入文件...")
        for filename, content in output_buffers.items():
            if not content:
                continue # 跳过空内容
            
            out_path = os.path.join(output_dir, filename)
            try:
                with open(out_path, 'w', encoding='utf-8') as f:
                    f.writelines(content)
                print(f"  [OK] {filename} ({len(content)} lines)")
            except IOError as e:
                print(f"  [ERROR] 无法写入 {filename}: {e}")

        print("-" * 30)
        print(f"处理完成。共扫描到 {file_count} 个有效代码文件。")

# ==========================================
# 主程序入口
# ==========================================

def main():
    parser = argparse.ArgumentParser(description="代码合并工具 (Scan & Merge)")
    
    # 模式选择 (互斥)
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--scan", metavar="DIR", help="扫描模式：指定要扫描的源目录")
    mode_group.add_argument("--merge", metavar="DIR", help="合并模式：指定要读取的源目录")

    # 通用参数
    parser.add_argument("--o", "-o", required=True, metavar="PATH", 
                        help="输出路径 (扫描模式下为ini文件，合并模式下为输出文件夹)")

    parser.add_argument("--in_ini", dest="ini_file", metavar="FILE",
                        help="合并模式必须：指定输入的ini配置文件")
    
    # 筛选参数
    parser.add_argument("--extensions", "-e", nargs="+", default=DEFAULT_EXTENSIONS,
                        help="指定要合并的文件扩展名 (e.g. -e .py .java)")

    # 关键修改：此参数在 scan 和 merge 模式下均有效
    parser.add_argument("--ignored_directories", "-i", nargs="+", default=DEFAULT_IGNORES,
                        help="指定要忽略的目录名 (e.g. -i test build)")

    args = parser.parse_args()

    # 初始化处理类
    # 注意：如果是 scan 模式，root 是 args.scan；merge 模式则是 args.merge
    root_dir = args.scan if args.scan else args.merge
    
    # 检查根目录
    if not os.path.isdir(root_dir):
        print(f"错误: 目录 '{root_dir}' 不存在。")
        sys.exit(1)

    # 实例化类：这里会传入命令行指定的 ignores，覆盖默认值
    merger = CodeMerger(root_dir, args.extensions, args.ignored_directories)

    if args.scan:
        # 扫描模式
        merger.scan_to_ini(args.o)
    
    elif args.merge:
        # 合并模式检查
        if not args.ini_file:
            print("错误: 合并模式 (--merge) 需要通过 --in_ini 指定配置文件。")
            sys.exit(1)
            
        merger.merge_files(args.ini_file, args.o)

if __name__ == "__main__":
    main()
