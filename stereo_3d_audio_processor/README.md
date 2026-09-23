# 3D Stereo Audio Processor

Chương trình Python tạo hiệu ứng stereo chuyển động giữa hai loa:
- Left -> Center -> Right -> Center -> Left
- Equal-power panning
- Điều chỉnh tốc độ/chu kỳ
- Điều chỉnh độ rộng L/R
- Khoảng cách giả lập bằng gain + low-pass
- Front/Back cue bằng delay nhẹ
- Làm mượt chuyển động để tránh tiếng "nhảy" giữa hai loa
- Hỗ trợ WAV/FLAC/OGG/AIFF; MP3/M4A đọc/xuất cần FFmpeg

## Cài đặt

```bash
py -m pip install -r requirements.txt
```

Để MP3/M4A hoạt động, cài FFmpeg và đảm bảo `ffmpeg.exe` nằm trong PATH.

## Chạy

```bash
py stereo_3d_audio.py
```

## Thiết lập gợi ý

- Chu kỳ 4 giây: âm thanh đi L -> R -> L tương đối rõ.
- Chu kỳ 6–8 giây: chuyển động chậm, dễ nghe.
- Độ rộng 1.0: chạy hết từ loa trái sang loa phải.
- Khoảng cách 0.0–0.25: giữ tiếng rõ.
- Front/Back 0.15–0.35: tạo chút cảm giác không gian mà không làm méo tiếng quá nhiều.
- `sine`: chuyển động mượt.
- `triangle`: chuyển động đều hơn.

Lưu ý: với chỉ hai loa vật lý, đây là hiệu ứng stereo/psychoacoustic, không phải vị trí 3D thật như hệ thống nhiều loa hoặc HRTF binaural.
