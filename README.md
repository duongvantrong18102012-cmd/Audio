# 3D Stereo Audio Processor

> A Python-based stereo spatial audio processor that transforms ordinary audio into a smooth moving stereo experience using two speakers.

**3D Stereo Audio Processor** là một chương trình Python dùng để xử lý file âm thanh và tạo hiệu ứng **stereo spatial movement** bằng cách điều khiển tín hiệu giữa **kênh trái (Left)** và **kênh phải (Right)**.

Mục tiêu của dự án là tạo cảm giác âm thanh đang **di chuyển trong không gian** khi phát qua hệ thống chỉ có hai loa stereo:

```text
LEFT SPEAKER                              RIGHT SPEAKER
     🔊                                         🔊
      \                                           /
       \                                         /
        \                                       /
         └────────── Virtual Sound ───────────┘
```

Ví dụ quỹ đạo:

```text
LEFT → CENTER → RIGHT → CENTER → LEFT
```

Thay vì chuyển kênh đột ngột, chương trình tạo ra một chuyển động liên tục và mượt:

```text
L 100%
   ↓
L 75%
   ↓
L 50%
   ↓
CENTER
   ↓
R 50%
   ↓
R 75%
   ↓
R 100%
```

---

## Table of Contents

* [Overview](#overview)
* [Features](#features)
* [How It Works](#how-it-works)
* [Signal Processing](#signal-processing)
* [Requirements](#requirements)
* [Installation](#installation)
* [FFmpeg](#ffmpeg)
* [Running the Application](#running-the-application)
* [User Interface](#user-interface)
* [Parameters](#parameters)
* [Movement Modes](#movement-modes)
* [Recommended Presets](#recommended-presets)
* [Supported Formats](#supported-formats)
* [Output](#output)
* [Project Structure](#project-structure)
* [Processing Pipeline](#processing-pipeline)
* [Technical Details](#technical-details)
* [Performance](#performance)
* [Limitations](#limitations)
* [Troubleshooting](#troubleshooting)
* [Development](#development)
* [Possible Future Improvements](#possible-future-improvements)
* [Use Cases](#use-cases)
* [Disclaimer](#disclaimer)
* [License](#license)

---

# Overview

Thông thường một file âm thanh stereo có hai kênh:

```text
Left  ───────────────► Left Speaker
Right ───────────────► Right Speaker
```

Dự án này lấy tín hiệu âm thanh và thay đổi phân bố năng lượng giữa hai kênh theo thời gian.

Ví dụ tại từng thời điểm:

```text
Time       Left        Right

0.0s       100%         0%
0.5s        75%        25%
1.0s        50%        50%
1.5s        25%        75%
2.0s         0%       100%
```

Sau đó quá trình có thể tiếp tục theo hướng ngược lại:

```text
RIGHT → CENTER → LEFT
```

Kết quả là người nghe có cảm giác nguồn âm thanh đang **di chuyển từ loa này sang loa kia**.

---

# Features

## Core Features

* Smooth stereo panning
* Left → Right → Left movement
* Center positioning
* Equal-power panning
* Continuous movement automation
* Adjustable movement speed
* Adjustable stereo depth
* Adjustable perceived distance
* Subtle front/back spatial cues
* Adjustable smoothing
* Output gain control
* WAV export
* FLAC export
* OGG export
* AIFF export
* MP3 export with FFmpeg
* MP3/M4A input through FFmpeg
* Simple graphical user interface
* Background processing
* Non-blocking UI during processing

---

# How It Works

## 1. Input

Người dùng chọn một file âm thanh:

```text
input.wav
```

hoặc:

```text
input.mp3
input.flac
input.ogg
input.m4a
```

Chương trình đọc file thành dữ liệu số:

```text
Audio File
    ↓
PCM Samples
    ↓
Floating Point Audio
```

---

## 2. Convert to Stereo

Nếu file đầu vào là mono:

```text
Mono
  ↓
Left + Right
```

Chương trình tạo hai kênh stereo.

Nếu file có nhiều hơn hai kênh, chương trình sử dụng hai kênh đầu tiên/giảm về stereo để đảm bảo pipeline xử lý tương thích với hệ thống hai loa.

---

## 3. Source Signal

Tín hiệu stereo được đưa về một source signal phù hợp với hiệu ứng chuyển động.

Mục đích là để nguồn âm thanh có thể được điều khiển như một vật thể đang di chuyển:

```text
Virtual Source
      ●
      │
      ├── Left Gain
      │
      └── Right Gain
```

---

# Signal Processing

## Equal-Power Panning

Một vấn đề của linear panning đơn giản là âm lượng cảm nhận có thể giảm khi nguồn âm thanh đi qua vị trí trung tâm.

Dự án sử dụng **equal-power panning**.

Với:

```text
pan = -1
```

nguồn âm thanh nằm hoàn toàn bên trái.

```text
LEFT  = 100%
RIGHT = 0%
```

Với:

```text
pan = 0
```

nguồn nằm ở giữa.

Với:

```text
pan = +1
```

nguồn nằm hoàn toàn bên phải.

Hệ số được tính theo:

```text
θ = (pan + 1) × π / 4

Left  = cos(θ)
Right = sin(θ)
```

Điều này tạo ra chuyển động stereo tự nhiên hơn.

---

# Movement

Chuyển động của nguồn âm thanh được biểu diễn bằng một giá trị:

```text
-1 ───────── 0 ───────── +1
LEFT        CENTER       RIGHT
```

Ví dụ:

```text
-1.0
 ↓
-0.75
 ↓
-0.50
 ↓
-0.25
 ↓
 0.0
 ↓
+0.25
 ↓
+0.50
 ↓
+0.75
 ↓
+1.0
```

Sau đó quá trình đảo chiều:

```text
+1.0 → 0.0 → -1.0
```

---

# Movement Smoothing

Nếu thay đổi pan trực tiếp theo từng bước, âm thanh có thể xuất hiện hiện tượng:

* zipper noise
* clicking
* abrupt movement
* unnatural transitions

Vì vậy chương trình sử dụng smoothing cho automation.

```text
Without smoothing:

L ──┐
    └──────── R

With smoothing:

L ───╮
     │
     ╰──────────╮
                ╰──── R
```

Điều này làm chuyển động liên tục hơn.

---

# Distance Simulation

Chương trình có tham số:

```text
Distance
```

Mục tiêu không phải mô phỏng khoảng cách vật lý chính xác, mà tạo ra **psychoacoustic cue** khiến nguồn âm thanh có cảm giác xa hơn.

Khi tăng khoảng cách:

1. Gain giảm.
2. High-frequency content giảm.
3. Tín hiệu trở nên mềm hơn.

Điều này dựa trên đặc điểm chung của âm thanh trong môi trường thực:

```text
Near source
    ↓
More detail
More high frequency
Higher level

Far source
    ↓
Less detail
Less high frequency
Lower level
```

---

# Front / Back Effect

Hai loa vật lý không thể tạo ra vị trí trước/sau thực sự chính xác chỉ bằng stereo panning.

Tuy nhiên chương trình bổ sung các cue nhỏ:

* inter-channel delay
* timing difference
* channel asymmetry
* frequency attenuation

để tạo thêm cảm giác không gian.

Đây là **psychoacoustic approximation**, không phải true 3D positional audio.

---

# Processing Pipeline

Pipeline tổng thể:

```text
                 ┌─────────────────┐
                 │   Input Audio   │
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │ Decode / Read   │
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │ Stereo Convert  │
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │ Source Signal   │
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │ Movement Curve  │
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │ Smooth Control  │
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │ Equal-Power Pan │
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │ Distance / EQ   │
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │ Front/Back Cue  │
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │ Peak Management │
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │ Output Stereo   │
                 └────────┬────────┘
                          │
                          ▼
                   output_3D.wav
```

---

# Requirements

## Operating System

Được thiết kế để chạy trên:

* Windows
* Linux
* macOS

Windows là môi trường được kiểm thử/nhắm tới thuận tiện nhất.

---

## Python

Khuyến nghị:

```text
Python 3.10+
```

Có thể hoạt động trên các phiên bản Python mới hơn nếu các dependency tương thích.

Kiểm tra Python:

```bash
python --version
```

hoặc trên Windows:

```bash
py --version
```

---

# Dependencies

Các thư viện Python chính:

```text
numpy
scipy
soundfile
pydub
```

Cài đặt:

```bash
pip install -r requirements.txt
```

hoặc:

```bash
py -m pip install -r requirements.txt
```

---

# FFmpeg

FFmpeg cần thiết nếu muốn sử dụng:

* MP3 input
* M4A input
* MP3 output
* M4A-related workflows

Kiểm tra FFmpeg:

```bash
ffmpeg -version
```

Nếu lệnh không tồn tại, hãy cài FFmpeg và thêm thư mục chứa `ffmpeg.exe` vào `PATH`.

Sau khi cài đặt:

```bash
ffmpeg -version
```

phải trả về thông tin phiên bản.

---

# Installation

Clone repository:

```bash
git clone https://github.com/YOUR_USERNAME/stereo-3d-audio-processor.git
```

Đi vào thư mục:

```bash
cd stereo-3d-audio-processor
```

Tạo virtual environment:

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Cài dependency:

```bash
python -m pip install -r requirements.txt
```

---

# Running the Application

Chạy:

```bash
python stereo_3d_audio.py
```

Windows:

```bash
py stereo_3d_audio.py
```

Sau đó giao diện chương trình sẽ xuất hiện.

---

# User Interface

Giao diện gồm:

```text
┌──────────────────────────────────────────┐
│       3D STEREO AUDIO PROCESSOR          │
├──────────────────────────────────────────┤
│                                          │
│ Input:  [ audio.wav            ] [Open]  │
│ Output: [ audio_3D.wav         ] [Save]  │
│                                          │
│ Movement Cycle      ███████░░░            │
│ Stereo Depth        ██████████            │
│ Distance            ██░░░░░░░░            │
│ Front / Back        ███░░░░░░░            │
│ Smoothing           ████░░░░░░            │
│ Output Gain         █████████░            │
│                                          │
│ Movement: [ sine ▼ ]                     │
│                                          │
│             [ PROCESS AUDIO ]             │
└──────────────────────────────────────────┘
```

---

# Parameters

## Movement Cycle

Xác định thời gian hoàn thành một chu kỳ chuyển động.

Ví dụ:

```text
4 seconds
```

có nghĩa là:

```text
LEFT → RIGHT → LEFT
```

trong khoảng thời gian được xác định bởi automation curve.

### Gợi ý

| Giá trị | Hiệu ứng       |
| ------: | -------------- |
|   1–2 s | Rất nhanh      |
|   3–4 s | Rõ ràng        |
|   5–8 s | Chậm, tự nhiên |
|   10+ s | Rất chậm       |

---

# Stereo Depth

Điều khiển mức độ di chuyển giữa hai loa.

```text
0.0
```

Nguồn gần như nằm ở center.

```text
0.5
```

Di chuyển trong phạm vi stereo trung bình.

```text
1.0
```

Di chuyển toàn bộ:

```text
LEFT ↔ RIGHT
```

---

# Distance

Điều chỉnh cảm giác khoảng cách.

```text
0.0
```

Nguồn gần.

```text
1.0
```

Nguồn xa hơn.

Không nên xem giá trị này là đơn vị mét.

Nó là một tham số hiệu ứng psychoacoustic.

---

# Front / Back

Điều chỉnh lượng cue dùng để tạo cảm giác không gian trước/sau.

Giá trị thấp:

```text
0.0 – 0.25
```

giữ âm thanh tự nhiên hơn.

Giá trị cao:

```text
0.5 – 1.0
```

hiệu ứng rõ hơn nhưng có thể làm thay đổi màu âm.

---

# Smoothing

Điều chỉnh độ mượt của chuyển động.

Giá trị thấp:

```text
Fast / responsive
```

Giá trị cao:

```text
Smooth / gradual
```

Nếu nghe thấy chuyển động bị giật, hãy tăng smoothing.

---

# Output Gain

Điều chỉnh gain đầu ra.

Chương trình cũng có bước peak management để hạn chế clipping.

Tuy nhiên người dùng vẫn nên kiểm tra output nếu sử dụng các hiệu ứng cực mạnh.

---

# Movement Modes

## Sine

```text
        RIGHT
          ●
       ╭──╮
     ╭─╯  ╰─╮
LEFT ●      ● LEFT
```

Đây là chế độ chuyển động mượt.

Phù hợp với:

* music
* ambience
* voice effects
* atmospheric audio
* cinematic effects

---

## Triangle

Chuyển động tuyến tính hơn:

```text
LEFT
  ●
   \
    \
     ● RIGHT
    /
   /
  ●
LEFT
```

Phù hợp khi muốn nguồn âm thanh di chuyển đều từ bên này sang bên kia.

---

# Recommended Presets

## Natural Movement

```text
Cycle:       6 s
Depth:       0.75
Distance:    0.10
Front/Back:  0.15
Smoothing:   0.08
Mode:        sine
```

Phù hợp với:

```text
Music
Ambient
Background audio
```

---

## Strong L/R Movement

```text
Cycle:       3 s
Depth:       1.0
Distance:    0.10
Front/Back:  0.20
Smoothing:   0.05
Mode:        sine
```

Hiệu ứng:

```text
LEFT → RIGHT → LEFT
```

rất rõ.

---

## Slow Spatial Movement

```text
Cycle:       8 s
Depth:       0.85
Distance:    0.20
Front/Back:  0.25
Smoothing:   0.12
Mode:        sine
```

Phù hợp với:

* cinematic audio
* ambient sound
* background music
* meditation-style audio

---

## Fast Movement

```text
Cycle:       1.5–2.5 s
Depth:       1.0
Distance:    0.05
Front/Back:  0.15
Smoothing:   0.03
Mode:        triangle
```

Hiệu ứng chuyển động mạnh:

```text
L → R → L → R → L
```

---

# Supported Formats

## Input

Native support through `soundfile`:

```text
WAV
FLAC
OGG
AIFF
```

Additional formats through FFmpeg/pydub:

```text
MP3
M4A
```

---

## Output

Có thể xuất:

```text
WAV
FLAC
OGG
AIFF
MP3
```

WAV được khuyến nghị nếu muốn giữ chất lượng xử lý tốt nhất.

---

# Why WAV Is Recommended

MP3 là codec lossy.

Nếu workflow là:

```text
MP3
 ↓
Processing
 ↓
MP3
```

sẽ có thêm một lần lossy encoding.

Khuyến nghị:

```text
Original
   ↓
WAV / FLAC
   ↓
Processing
   ↓
WAV / FLAC
```

Sau đó nếu cần phân phối:

```text
WAV
 ↓
MP3
```

---

# Project Structure

```text
stereo-3d-audio-processor/
│
├── stereo_3d_audio.py
│
├── requirements.txt
│
├── README.md
│
└── LICENSE
```

---

# Source Code Architecture

Các thành phần chính trong chương trình:

```text
read_audio()
```

Đọc file âm thanh.

```text
write_audio()
```

Xuất file.

```text
stereoize()
```

Đảm bảo tín hiệu đầu ra là stereo.

```text
resample_if_needed()
```

Điều chỉnh sample rate khi cần.

```text
smooth_position()
```

Tạo đường chuyển động.

```text
equal_power_pan()
```

Tính gain cho Left/Right.

```text
one_pole_smooth()
```

Làm mượt automation.

```text
fractional_delay()
```

Tạo delay phân số cho cue không gian.

```text
apply_highpass()
```

Loại bỏ thành phần DC/sub-bass cực thấp không cần thiết.

```text
process_audio()
```

Pipeline xử lý chính.

```text
App
```

Giao diện Tkinter.

---

# Technical Details

## Audio Representation

Âm thanh được xử lý dưới dạng:

```text
float32
```

với khoảng giá trị thông thường:

```text
-1.0 → +1.0
```

Điều này phù hợp với các phép tính DSP bằng NumPy/SciPy.

---

# Sample Rate

Chương trình giữ nguyên sample rate trong phần lớn trường hợp.

Các file sample rate quá thấp hoặc quá cao có thể được đưa về mức xử lý phù hợp.

Mục tiêu là cân bằng giữa:

* chất lượng
* tốc độ xử lý
* bộ nhớ
* khả năng tương thích

---

# DSP Components

Dự án sử dụng:

### NumPy

Cho:

* vectorized processing
* audio buffers
* gain calculation
* automation curves

### SciPy

Cho:

* filters
* resampling
* signal processing
* delay-related processing

### SoundFile

Cho:

* WAV
* FLAC
* OGG
* AIFF

### Pydub

Cho các format cần FFmpeg.

---

# Stereo Spatial Model

Mô hình hiện tại có thể hình dung:

```text
                   CENTER
                     ●
                  /     \
                /         \
              /             \
        LEFT ●---------------● RIGHT
```

Nguồn âm thanh có một vị trí ảo:

```text
position ∈ [-1, +1]
```

Trong đó:

```text
-1 = Left
 0 = Center
+1 = Right
```

---

# Two-Speaker Limitation

Một hệ thống chỉ có:

```text
Left Speaker
Right Speaker
```

không thể tái tạo đầy đủ trường âm thanh 3D vật lý.

Đặc biệt:

```text
Front
Back
Above
Below
Behind listener
```

không thể được xác định chính xác chỉ bằng hai loa thông thường.

Dự án sử dụng các đặc điểm psychoacoustic để tạo **ảo giác không gian**.

Do đó tên "3D" trong dự án đề cập tới **3D-like / spatial perception**, không có nghĩa là hệ thống định vị 3D vật lý chính xác.

---

# Stereo vs Binaural

## Stereo

```text
LEFT ───── Listener ───── RIGHT
```

Phù hợp với:

* speakers
* headphones
* TVs
* stereo systems

---

## Binaural / HRTF

Binaural sử dụng các đặc điểm liên quan đến:

* Interaural Time Difference (ITD)
* Interaural Level Difference (ILD)
* HRTF
* Head shadow
* Frequency shaping

Có thể tạo cảm giác:

```text
         FRONT
           ●
          /
LEFT ●───●───● RIGHT
          \
           ●
         BACK
```

Nhưng bản thân dự án hiện tại **không phải HRTF binaural renderer đầy đủ**.

---

# Performance

Chương trình sử dụng NumPy/SciPy để xử lý theo mảng thay vì vòng lặp Python cho phần lớn phép tính DSP.

Điều này giúp:

* giảm overhead
* xử lý nhanh hơn
* tận dụng native numerical routines

Tuy nhiên file dài và sample rate cao sẽ yêu cầu nhiều RAM hơn.

Ví dụ file stereo:

```text
48,000 samples/sec
×
2 channels
×
float32
```

sẽ tiêu thụ bộ nhớ theo độ dài file.

---

# Large Audio Files

Với file rất dài:

```text
1–2 hours
```

hoặc sample rate rất cao, việc xử lý toàn bộ file trong RAM có thể tốn nhiều bộ nhớ.

Một hướng phát triển trong tương lai là:

```text
Input
 ↓
Chunk 1
 ↓
Chunk 2
 ↓
Chunk 3
 ↓
...
 ↓
Output
```

thay vì:

```text
Input
 ↓
Entire file in RAM
 ↓
Process
 ↓
Output
```

---

# Troubleshooting

## `ModuleNotFoundError: numpy`

Cài dependency:

```bash
python -m pip install numpy
```

Hoặc toàn bộ:

```bash
python -m pip install -r requirements.txt
```

---

## MP3 không mở được

Cài FFmpeg.

Kiểm tra:

```bash
ffmpeg -version
```

Sau đó thử lại.

---

## MP3 export không hoạt động

Đảm bảo:

```text
pydub
FFmpeg
```

đều được cài đặt.

---

## Audio bị nhỏ

Tăng:

```text
Output Gain
```

hoặc giảm:

```text
Distance
```

---

## Chuyển động quá nhanh

Tăng:

```text
Movement Cycle
```

Ví dụ:

```text
3 s → 6 s
```

---

## Chuyển động bị giật

Tăng:

```text
Smoothing
```

---

## Hiệu ứng quá yếu

Tăng:

```text
Stereo Depth
```

lên:

```text
0.8–1.0
```

---

## Âm thanh bị méo

Thử:

```text
Output Gain ↓
Distance ↓
Front/Back ↓
```

và xuất sang WAV để kiểm tra trước.

---

# Development

Clone repository:

```bash
git clone https://github.com/YOUR_USERNAME/stereo-3d-audio-processor.git
```

Tạo branch:

```bash
git checkout -b feature/new-spatial-effect
```

Cài dependencies:

```bash
pip install -r requirements.txt
```

Chạy:

```bash
python stereo_3d_audio.py
```

Sau khi thay đổi code, kiểm tra:

* input mono
* input stereo
* WAV
* FLAC
* MP3
* short audio
* long audio
* low volume
* high volume
* movement extremes

---

# Possible Future Improvements

Các hướng phát triển có thể bao gồm:

## Advanced Motion Paths

Cho phép người dùng chọn:

```text
Left → Right
Right → Left
Circle
Ellipse
Figure-8
Random
Custom
```

---

## Custom Automation

Cho phép vẽ trực tiếp:

```text
Position
 1.0 |           ●
     |         /   \
 0.0 |───────●───────●──────
     |     /           \
-1.0 | ●
     +----------------------> Time
```

---

## Real-Time Preview

Cho phép nghe hiệu ứng ngay trong chương trình trước khi export.

---

## Waveform Viewer

Hiển thị:

```text
Amplitude
   │
   │  ╭╮     ╭──╮
   │ ╭╯╰╮   ╭╯  ╰╮
───┼─╯──╰───╯────╰──── Time
```

và overlay:

```text
Pan Position
```

---

## Spectrogram

Hiển thị phổ tần số:

```text
Frequency
   ↑
   │ █████
   │ ███████
   │ █████████
   └────────────────→ Time
```

---

## HRTF Mode

Một phiên bản nâng cao có thể bổ sung:

* HRTF datasets
* binaural rendering
* headphone mode
* true front/back cues

---

## Realtime Processing

Cho phép xử lý:

```text
Microphone
    ↓
Realtime DSP
    ↓
Stereo Spatial Effect
    ↓
Speakers
```

---

## GPU Acceleration

Một số pipeline DSP lớn có thể được tối ưu bằng:

* CUDA
* OpenCL
* GPU compute
* specialized DSP libraries

Tuy nhiên với stereo audio thông thường, CPU processing bằng NumPy/SciPy thường đã đủ.

---

# Use Cases

Dự án có thể được sử dụng để tạo:

### Music Effects

```text
Instrument
 ↓
Spatial Movement
```

### Ambient Audio

```text
Wind
Rain
Environment
 ↓
Stereo Movement
```

### Video

```text
Video Audio
 ↓
Spatial Processing
 ↓
Edited Audio
```

### Game Audio

Tạo hiệu ứng:

```text
Enemy
 ↓
Left → Right
```

hoặc:

```text
Object
 ↓
Right → Center → Left
```

### Sound Design

Có thể sử dụng làm một bước trong workflow:

```text
Source
 ↓
EQ
 ↓
Compression
 ↓
Spatial Movement
 ↓
Mastering
```

---

# Important Notes

## This is not a true 3D audio engine

Dự án hiện tại chủ yếu tạo:

```text
Stereo Spatial Illusion
```

không phải:

```text
Full 3D Positional Audio
```

Một hệ thống 3D hoàn chỉnh thường cần thêm:

* HRTF
* room modeling
* head tracking
* distance attenuation
* occlusion
* reverberation
* Doppler effect
* elevation modeling

---

# Audio Quality

Để có kết quả tốt nhất:

### Input

Khuyến nghị:

```text
WAV
24-bit
44.1 kHz / 48 kHz
```

hoặc:

```text
FLAC
```

### Output

Khuyến nghị:

```text
WAV
```

trong quá trình chỉnh sửa.

Chỉ encode sang:

```text
MP3
```

ở bước cuối nếu cần.

---

# Example Workflow

```text
original.wav
     │
     ▼
3D Stereo Audio Processor
     │
     ├── Cycle = 5s
     ├── Depth = 1.0
     ├── Distance = 0.15
     ├── Front/Back = 0.25
     ├── Smoothing = 0.08
     └── Mode = sine
     │
     ▼
original_3D.wav
```

Khi phát:

```text
LEFT SPEAKER                     RIGHT SPEAKER

     🔊                               🔊
      \                               /
       \                             /
        \                           /
         ←── Virtual Sound ───────→
```

Người nghe cảm nhận nguồn âm thanh di chuyển:

```text
LEFT
 ↓
CENTER
 ↓
RIGHT
 ↓
CENTER
 ↓
LEFT
```

---

# Roadmap

### v1.x

* [x] Stereo panning
* [x] Equal-power panning
* [x] Smooth movement
* [x] Distance simulation
* [x] Front/back cue
* [x] GUI
* [x] Multiple audio formats

### v2.x

* [ ] Real-time preview
* [ ] Waveform visualization
* [ ] Custom movement paths
* [ ] More movement modes
* [ ] Preset system
* [ ] Batch processing

### v3.x

* [ ] HRTF
* [ ] Binaural mode
* [ ] Headphone optimization
* [ ] Advanced spatialization
* [ ] Real-time spatial engine

---

# Contributing

Contributions are welcome.

Nếu muốn đóng góp:

1. Fork repository.
2. Tạo branch mới.
3. Implement thay đổi.
4. Test với nhiều loại audio.
5. Commit thay đổi.
6. Tạo Pull Request.

Ví dụ:

```bash
git checkout -b feature/custom-motion
```

---

# License

Đặt license của dự án tại:

```text
LICENSE
```

Nếu repository sử dụng MIT License, có thể thêm:

```text
MIT License
```

và nội dung license tương ứng vào file `LICENSE`.

---

# Credits

Built with:

* Python
* NumPy
* SciPy
* SoundFile
* Pydub
* FFmpeg
* Tkinter

---

# Final Notes

**3D Stereo Audio Processor** tập trung vào một mục tiêu đơn giản:

> Biến âm thanh thông thường thành âm thanh có cảm giác chuyển động không gian bằng hệ thống stereo hai loa.

Mô hình cốt lõi:

```text
                VIRTUAL SPACE

                    CENTER
                      ●
                    /   \
                  /       \
                /           \
        LEFT ●─────────────────● RIGHT
             🔊                 🔊

              L → C → R → C → L
```

Dự án ưu tiên:

```text
Smooth movement
      +
Stable stereo image
      +
Simple controls
      +
Low processing complexity
      +
High compatibility
```

thay vì cố gắng mô phỏng một hệ thống 3D vật lý vượt quá khả năng của chỉ hai loa.
