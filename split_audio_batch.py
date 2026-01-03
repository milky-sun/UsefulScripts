import os
import sys
from pydub import AudioSegment
from pydub.silence import detect_silence

# 定义支持的音频格式，避免尝试处理非音频文件
SUPPORTED_EXTENSIONS = ('.mp3', '.wav', '.m4a', '.flac', '.ogg', '.wma')

def split_audio_smart(file_path, output_dir, segment_time=15, search_window=60, silence_thresh=-40, min_silence_len=500):
    """
    单个文件的智能分割逻辑
    """
    base_name_with_ext = os.path.basename(file_path)
    base_name = os.path.splitext(base_name_with_ext)[0]
    
    print(f"\n[正在处理文件]: {base_name_with_ext}")
    print(f" -> 加载中... (大文件需等待)")

    try:
        audio = AudioSegment.from_file(file_path)
    except Exception as e:
        print(f"❌ 加载失败 {base_name_with_ext}: {e}")
        return

    # 转换为单声道
    audio = audio.set_channels(1)

    # 基础参数
    segment_ms = segment_time * 60 * 1000
    window_ms = search_window * 1000
    total_len = len(audio)
    
    start = 0
    part_number = 1
    
    while start < total_len:
        end = start + segment_ms
        
        # 最后一段的处理
        if end >= total_len:
            end = total_len
            split_point = end
        else:
            # 寻找静音点
            search_start = max(start, end - window_ms)
            search_chunk = audio[search_start:end]
            
            silences = detect_silence(search_chunk, 
                                      min_silence_len=min_silence_len, 
                                      silence_thresh=silence_thresh)
            
            if silences:
                last_silence = silences[-1]
                silence_mid = last_silence[0] + (last_silence[1] - last_silence[0]) / 2
                split_point = search_start + silence_mid
                print(f" -> 片段 {part_number}: 找到静音点，优化切分。")
            else:
                split_point = end
                print(f" -> 片段 {part_number}: 未找到静音，强制切分。")

        # 切割并导出
        chunk = audio[start:int(split_point)]
        
        # 构造输出文件名 A-001.mp3
        output_filename = f"{base_name}-{part_number:03d}.mp3"
        output_path = os.path.join(output_dir, output_filename)
        
        chunk.export(
            output_path,
            format="mp3",
            bitrate="320k",
            parameters=["-ac", "1"]
        )
        print(f"    已生成: {output_filename}")
        
        start = int(split_point)
        part_number += 1
    
    print(f"✅ 文件 {base_name_with_ext} 处理完毕。")

def process_folder(input_folder, output_folder):
    # 1. 检查输入目录
    if not os.path.exists(input_folder):
        print(f"错误: 输入文件夹 '{input_folder}' 不存在。")
        return

    # 2. 创建输出目录 (如果不存在)
    if not os.path.exists(output_folder):
        print(f"输出文件夹不存在，正在创建: {output_folder}")
        os.makedirs(output_folder, exist_ok=True)

    # 3. 获取所有文件并过滤
    all_files = os.listdir(input_folder)
    audio_files = [f for f in all_files if f.lower().endswith(SUPPORTED_EXTENSIONS)]
    
    if not audio_files:
        print("在输入文件夹中没有找到支持的音频文件。")
        return

    total_files = len(audio_files)
    print(f"==========================================")
    print(f"发现 {total_files} 个音频文件，准备开始处理...")
    print(f"输入: {input_folder}")
    print(f"输出: {output_folder}")
    print(f"==========================================\n")

    # 4. 循环处理
    for index, filename in enumerate(audio_files):
        file_path = os.path.join(input_folder, filename)
        print(f"--- 进度 ({index + 1}/{total_files}) ---")
        
        # 调用分割函数
        split_audio_smart(file_path, output_folder)

    print("\n==========================================")
    print("🎉 所有任务全部完成！")
    print("==========================================")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法错误。请使用格式:")
        print('python split_audio_batch.py "/输入文件夹路径" "/输出文件夹路径"')
    else:
        input_dir = sys.argv[1]
        output_dir = sys.argv[2]
        
        # 如果静音检测不准确，可以在这里调整 silence_thresh (例如 -30)
        process_folder(input_dir, output_dir)