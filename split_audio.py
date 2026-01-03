import os
import sys
from pydub import AudioSegment
from pydub.silence import detect_silence

def split_audio_smart(file_path, segment_time=15, search_window=60, silence_thresh=-40, min_silence_len=500):
    """
    智能分割音频文件
    :param file_path: 输入文件路径
    :param segment_time: 目标切片时长（分钟）
    :param search_window: 在目标时长前多少秒开始寻找静音（秒）
    :param silence_thresh: 静音阈值（dBFS），低于此分贝视为静音
    :param min_silence_len: 被认定为静音的最短时长（毫秒）
    """
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        print(f"错误: 找不到文件 {file_path}")
        return

    print(f"正在加载音频: {file_path} ... (文件较大时可能需要几十秒)")
    try:
        audio = AudioSegment.from_file(file_path)
    except Exception as e:
        print(f"加载音频失败: {e}")
        return

    # 转换为单声道
    print("正在转换为单声道...")
    audio = audio.set_channels(1)

    # 基础参数计算
    segment_ms = segment_time * 60 * 1000       # 15分钟的毫秒数
    window_ms = search_window * 1000            # 回溯查找窗口的毫秒数
    total_len = len(audio)
    
    start = 0
    part_number = 1
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    
    while start < total_len:
        end = start + segment_ms
        
        # 如果剩余部分不足一个片段时长，直接取到最后
        if end >= total_len:
            end = total_len
            split_point = end
            print(f"处理最后一段: {base_name}-{part_number:03d}.mp3")
        else:
            # 定义搜索静音的区间： [15分钟 - 60秒, 15分钟]
            search_start = max(start, end - window_ms)
            search_chunk = audio[search_start:end]
            
            print(f"正在寻找分割点 (片段 {part_number})... 目标位置: {end/1000/60:.2f}分")

            # 检测静音区间
            # silence_thresh 默认为 -40dBFS，如果录音底噪大，可能需要调高到 -30 或 -25
            silences = detect_silence(search_chunk, 
                                      min_silence_len=min_silence_len, 
                                      silence_thresh=silence_thresh)
            
            if silences:
                # 找到最后一个静音区间（离15分钟最近的）
                last_silence = silences[-1]
                # 取静音区间的中点作为分割点
                silence_mid = last_silence[0] + (last_silence[1] - last_silence[0]) / 2
                split_point = search_start + silence_mid
                print(f"  -> 找到静音点，回溯了 {(end - split_point)/1000:.1f} 秒")
            else:
                # 如果没找到静音，强制在15分钟处分割
                split_point = end
                print("  -> 未在窗口内找到静音点，强制分割。")

        # 分割音频
        chunk = audio[start:int(split_point)]
        
        # 导出文件
        output_filename = f"{base_name}-{part_number:03d}.mp3"
        print(f"  -> 正在导出: {output_filename}")
        
        chunk.export(
            output_filename,
            format="mp3",
            bitrate="320k",
            parameters=["-ac", "1"] # 再次强制确保 ffmpeg 参数为单声道
        )
        
        # 更新下一次的起始点
        start = int(split_point)
        part_number += 1

    print("✅ 处理完成！")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python split_audio.py <音频文件路径>")
    else:
        # 你可以在这里调整参数，例如录音底噪大可以将 silence_thresh 改为 -30
        split_audio_smart(sys.argv[1], silence_thresh=-40)