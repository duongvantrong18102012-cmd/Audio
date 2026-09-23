import math
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import numpy as np
import soundfile as sf
from scipy import signal


SUPPORTED = (".wav", ".flac", ".ogg", ".aiff", ".aif", ".mp3", ".m4a")


def read_audio(path):
    """Read audio. soundfile handles WAV/FLAC/OGG/AIFF. MP3/M4A need ffmpeg."""
    try:
        data, sr = sf.read(path, always_2d=True, dtype="float32")
        return data, sr
    except Exception:
        # Fall back to pydub/ffmpeg for formats soundfile cannot decode.
        try:
            from pydub import AudioSegment
        except ImportError as e:
            raise RuntimeError(
                "Không đọc được file này. Với MP3/M4A, hãy cài FFmpeg và pydub."
            ) from e

        seg = AudioSegment.from_file(path)
        channels = seg.channels
        sr = seg.frame_rate
        samples = np.array(seg.get_array_of_samples())

        if channels > 1:
            samples = samples.reshape((-1, channels))
        else:
            samples = samples.reshape((-1, 1))

        scale = float(1 << (8 * seg.sample_width - 1))
        data = samples.astype(np.float32) / scale
        return data, sr


def write_audio(path, data, sr):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".wav", ".flac", ".ogg", ".aiff", ".aif"):
        sf.write(path, np.clip(data, -1.0, 1.0), sr)
        return

    # MP3/M4A export through pydub + ffmpeg.
    try:
        from pydub import AudioSegment
    except ImportError as e:
        raise RuntimeError("Xuất MP3/M4A cần pydub và FFmpeg.") from e

    pcm = (np.clip(data, -1.0, 1.0) * 32767.0).astype(np.int16)
    channels = pcm.shape[1]
    raw = pcm.tobytes()
    seg = AudioSegment(
        data=raw,
        sample_width=2,
        frame_rate=sr,
        channels=channels,
    )

    fmt = "mp3" if ext == ".mp3" else "mp4"
    seg.export(path, format=fmt, bitrate="256k")


def stereoize(data):
    """Convert mono/stereo/multichannel input to stereo."""
    if data.shape[1] == 1:
        x = data[:, 0]
        return np.column_stack((x, x))
    if data.shape[1] == 2:
        return data[:, :2]
    return data[:, :2].mean(axis=1, keepdims=True).repeat(2, axis=1)


def resample_if_needed(x, sr, target_sr=48000):
    if sr == target_sr:
        return x, sr
    gcd = math.gcd(sr, target_sr)
    up = target_sr // gcd
    down = sr // gcd
    y = signal.resample_poly(x, up, down, axis=0).astype(np.float32)
    return y, target_sr


def smooth_position(t, mode="sine"):
    """Position in [-1, 1]: -1 left, 0 center, +1 right."""
    if mode == "triangle":
        return 2.0 * np.abs(2.0 * (t - np.floor(t + 0.5))) - 1.0
    # Sine: starts at center, moves right, center, left, center.
    return np.sin(2.0 * np.pi * t)


def equal_power_pan(mono, pan):
    """
    Equal-power panning:
      pan=-1 => left
      pan=0  => center
      pan=+1 => right
    """
    theta = (pan + 1.0) * np.pi / 4.0
    left = np.cos(theta)
    right = np.sin(theta)
    return mono * left, mono * right


def one_pole_smooth(values, amount):
    """Smooth automation to prevent audible zippering."""
    if amount <= 0:
        return values

    out = np.empty_like(values)
    out[0] = values[0]
    alpha = float(np.clip(1.0 - amount, 0.001, 1.0))
    for i in range(1, len(values)):
        out[i] = out[i - 1] + alpha * (values[i] - out[i - 1])
    return out


def fractional_delay(x, delay_samples):
    """Linear fractional delay for one stereo channel."""
    n = len(x)
    idx = np.arange(n, dtype=np.float64) - delay_samples
    return np.interp(idx, np.arange(n, dtype=np.float64), x, left=0.0, right=0.0)


def apply_highpass(x, sr, hz=35):
    sos = signal.butter(2, hz, btype="highpass", fs=sr, output="sos")
    return signal.sosfilt(sos, x, axis=0).astype(np.float32)


def process_audio(
    data,
    sr,
    cycle_seconds=4.0,
    depth=1.0,
    distance=0.0,
    front_back=0.25,
    smooth=0.08,
    movement="sine",
    output_gain=0.95,
):
    """
    Create a stereo moving-source effect.

    depth: 0..1, amount of left/right travel.
    distance: 0..1, perceived distance via volume + high-frequency damping.
    front_back: 0..1, subtle inter-channel delay/EQ asymmetry.
    """
    x = stereoize(data).astype(np.float32)

    # Work from a mono-compatible source to make movement obvious.
    source = x.mean(axis=1)
    source = apply_highpass(source[:, None], sr, 28)[:, 0]

    n = len(source)
    time = np.arange(n, dtype=np.float64) / sr

    # Continuous L-R-L position.
    cycles = time / max(cycle_seconds, 0.1)
    raw_pan = smooth_position(cycles, movement)
    raw_pan *= float(np.clip(depth, 0.0, 1.0))

    # Smooth the automation.
    smooth_factor = float(np.clip(smooth, 0.001, 0.5))
    pan = one_pole_smooth(raw_pan.astype(np.float32), smooth_factor)

    # Equal-power stereo panning.
    theta = (pan + 1.0) * np.pi / 4.0
    left_gain = np.cos(theta)
    right_gain = np.sin(theta)

    # Distance: lower volume and soften highs as distance increases.
    d = float(np.clip(distance, 0.0, 1.0))
    distance_gain = 1.0 - 0.38 * d
    y_left = source * left_gain * distance_gain
    y_right = source * right_gain * distance_gain

    # Subtle pseudo-front/back cues:
    # - small opposing delays
    # - mild stereo-dependent high-frequency filtering
    fb = float(np.clip(front_back, 0.0, 1.0))
    max_delay_ms = 3.5 * fb

    delay_l = (1.0 - pan) * 0.5 * max_delay_ms
    delay_r = (1.0 + pan) * 0.5 * max_delay_ms

    # Use a representative average delay for efficient processing.
    # Pan-dependent delay is approximated by two small variable-delay bands.
    avg_l = float(np.mean(delay_l)) * sr / 1000.0
    avg_r = float(np.mean(delay_r)) * sr / 1000.0

    if avg_l > 0.01:
        y_left = fractional_delay(y_left, avg_l)
    if avg_r > 0.01:
        y_right = fractional_delay(y_right, avg_r)

    # Distance-dependent low-pass.
    cutoff = max(2500.0, 18000.0 - 11000.0 * d)
    cutoff = min(cutoff, sr * 0.45)
    sos = signal.butter(2, cutoff, btype="lowpass", fs=sr, output="sos")
    y_left = signal.sosfilt(sos, y_left).astype(np.float32)
    y_right = signal.sosfilt(sos, y_right).astype(np.float32)

    out = np.column_stack((y_left, y_right)).astype(np.float32)

    # Gentle peak normalization, preserving dynamics.
    peak = float(np.max(np.abs(out))) if out.size else 0.0
    if peak > 1e-7:
        target = float(np.clip(output_gain, 0.1, 1.0))
        out *= min(1.0, target / peak)

    return np.clip(out, -1.0, 1.0)


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("3D Stereo Audio Processor")
        self.root.geometry("760x640")
        self.root.minsize(700, 600)

        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.cycle = tk.DoubleVar(value=4.0)
        self.depth = tk.DoubleVar(value=1.0)
        self.distance = tk.DoubleVar(value=0.15)
        self.front_back = tk.DoubleVar(value=0.25)
        self.smooth = tk.DoubleVar(value=0.08)
        self.gain = tk.DoubleVar(value=0.95)
        self.mode = tk.StringVar(value="sine")
        self.status = tk.StringVar(value="Chọn file âm thanh để bắt đầu.")

        self.build_ui()

    def build_ui(self):
        pad = {"padx": 14, "pady": 7}

        title = ttk.Label(
            self.root,
            text="3D STEREO AUDIO PROCESSOR",
            font=("Segoe UI", 18, "bold"),
        )
        title.pack(pady=(18, 4))

        desc = ttk.Label(
            self.root,
            text="Tạo chuyển động âm thanh L → R → L bằng 2 loa stereo",
        )
        desc.pack(pady=(0, 15))

        frm = ttk.Frame(self.root)
        frm.pack(fill="x", **pad)

        ttk.Label(frm, text="File đầu vào:").grid(row=0, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.input_path).grid(
            row=0, column=1, sticky="ew", padx=8
        )
        ttk.Button(frm, text="Chọn...", command=self.choose_input).grid(row=0, column=2)
        frm.columnconfigure(1, weight=1)

        ttk.Label(frm, text="File đầu ra:").grid(row=1, column=0, sticky="w", pady=8)
        ttk.Entry(frm, textvariable=self.output_path).grid(
            row=1, column=1, sticky="ew", padx=8
        )
        ttk.Button(frm, text="Lưu...", command=self.choose_output).grid(row=1, column=2)

        sep = ttk.Separator(self.root)
        sep.pack(fill="x", padx=14, pady=10)

        settings = ttk.LabelFrame(self.root, text="Điều khiển hiệu ứng")
        settings.pack(fill="x", padx=14, pady=5)

        self.add_scale(settings, "Chu kỳ di chuyển (giây)", self.cycle, 0.5, 20.0, 0)
        self.add_scale(settings, "Độ rộng L ↔ R", self.depth, 0.0, 1.0, 1)
        self.add_scale(settings, "Khoảng cách", self.distance, 0.0, 1.0, 2)
        self.add_scale(settings, "Front / Back", self.front_back, 0.0, 1.0, 3)
        self.add_scale(settings, "Độ mượt chuyển động", self.smooth, 0.001, 0.5, 4)
        self.add_scale(settings, "Output gain", self.gain, 0.1, 1.0, 5)

        ttk.Label(settings, text="Quỹ đạo:").grid(
            row=6, column=0, sticky="w", padx=10, pady=8
        )
        combo = ttk.Combobox(
            settings,
            textvariable=self.mode,
            values=("sine", "triangle"),
            state="readonly",
            width=18,
        )
        combo.grid(row=6, column=1, sticky="w", padx=10, pady=8)

        info = ttk.Label(
            self.root,
            text=(
                "sine: chuyển động mềm, tự nhiên.  "
                "triangle: chạy đều L → R → L."
            ),
            foreground="#555",
        )
        info.pack(padx=14, pady=5)

        self.progress = ttk.Progressbar(self.root, mode="indeterminate")
        self.progress.pack(fill="x", padx=14, pady=12)

        ttk.Button(
            self.root,
            text="PROCESS AUDIO",
            command=self.start_processing,
        ).pack(ipadx=30, ipady=10, pady=8)

        ttk.Label(
            self.root,
            textvariable=self.status,
            wraplength=700,
            foreground="#444",
        ).pack(padx=14, pady=10)

    def add_scale(self, parent, label, variable, lo, hi, row):
        ttk.Label(parent, text=label).grid(
            row=row, column=0, sticky="w", padx=10, pady=6
        )
        scale = ttk.Scale(
            parent,
            from_=lo,
            to=hi,
            variable=variable,
            orient="horizontal",
        )
        scale.grid(row=row, column=1, sticky="ew", padx=10, pady=6)
        value = ttk.Label(parent, textvariable=variable, width=8)
        value.grid(row=row, column=2, padx=10)
        parent.columnconfigure(1, weight=1)

    def choose_input(self):
        path = filedialog.askopenfilename(
            title="Chọn file âm thanh",
            filetypes=[
                ("Audio", "*.wav *.flac *.ogg *.aiff *.aif *.mp3 *.m4a"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.input_path.set(path)
            base, _ = os.path.splitext(path)
            self.output_path.set(base + "_3D.wav")

    def choose_output(self):
        path = filedialog.asksaveasfilename(
            title="Lưu audio đã xử lý",
            defaultextension=".wav",
            filetypes=[
                ("WAV", "*.wav"),
                ("FLAC", "*.flac"),
                ("OGG", "*.ogg"),
                ("MP3", "*.mp3"),
                ("AIFF", "*.aiff"),
            ],
        )
        if path:
            self.output_path.set(path)

    def start_processing(self):
        if not self.input_path.get():
            messagebox.showwarning("Thiếu file", "Hãy chọn file đầu vào.")
            return
        if not self.output_path.get():
            messagebox.showwarning("Thiếu file", "Hãy chọn nơi lưu file đầu ra.")
            return

        self.progress.start(10)
        self.status.set("Đang xử lý âm thanh...")
        threading.Thread(target=self.worker, daemon=True).start()

    def worker(self):
        try:
            data, sr = read_audio(self.input_path.get())
            # Keep processing efficient while using a high-quality sample rate.
            if sr < 32000:
                data, sr = resample_if_needed(data, sr, 48000)
            elif sr > 96000:
                data, sr = resample_if_needed(data, sr, 48000)

            out = process_audio(
                data,
                sr,
                cycle_seconds=self.cycle.get(),
                depth=self.depth.get(),
                distance=self.distance.get(),
                front_back=self.front_back.get(),
                smooth=self.smooth.get(),
                movement=self.mode.get(),
                output_gain=self.gain.get(),
            )
            write_audio(self.output_path.get(), out, sr)

            self.root.after(
                0,
                lambda: self.done(
                    f"Hoàn tất. File đã lưu tại:\n{self.output_path.get()}"
                ),
            )
        except Exception as e:
            self.root.after(0, lambda: self.fail(str(e)))

    def done(self, msg):
        self.progress.stop()
        self.status.set(msg)
        messagebox.showinfo("Hoàn tất", msg)

    def fail(self, msg):
        self.progress.stop()
        self.status.set("Có lỗi khi xử lý.")
        messagebox.showerror("Lỗi", msg)


if __name__ == "__main__":
    root = tk.Tk()
    try:
        from tkinter import TclError
        root.tk.call("tk", "scaling", 1.0)
    except Exception:
        pass
    App(root)
    root.mainloop()
