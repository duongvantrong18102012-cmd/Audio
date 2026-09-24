import math
import os
import subprocess
import tempfile
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import numpy as np
import soundfile as sf
from scipy import signal


# ============================================================
# CONFIG
# ============================================================

FFMPEG_PATH = r"C:\ffmpeg\bin\bin\ffmpeg.exe"
FFPROBE_PATH = r"C:\ffmpeg\bin\bin\ffprobe.exe"

SUPPORTED_INPUT = (
    ".wav",
    ".flac",
    ".ogg",
    ".aiff",
    ".aif",
    ".mp3",
    ".m4a",
)

SUPPORTED_OUTPUT = (
    ".wav",
    ".flac",
    ".ogg",
    ".mp3",
    ".m4a",
    ".aiff",
    ".aif",
)


# ============================================================
# FFMPEG
# ============================================================

def check_ffmpeg():
    """Check whether the configured FFmpeg executable exists."""
    if not os.path.isfile(FFMPEG_PATH):
        raise FileNotFoundError(
            "Không tìm thấy FFmpeg.\n\n"
            f"Đường dẫn đang được sử dụng:\n{FFMPEG_PATH}\n\n"
            "Hãy kiểm tra lại thư mục FFmpeg."
        )

    try:
        result = subprocess.run(
            [FFMPEG_PATH, "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

        if result.returncode != 0:
            raise RuntimeError("FFmpeg không thể khởi động.")

    except OSError as exc:
        raise RuntimeError(
            f"Không thể chạy FFmpeg:\n{FFMPEG_PATH}\n\n{exc}"
        ) from exc


def run_ffmpeg(args):
    """Run FFmpeg safely without opening a console window."""
    check_ffmpeg()

    command = [FFMPEG_PATH] + args

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except OSError as exc:
        raise RuntimeError(
            f"Không thể chạy FFmpeg:\n{FFMPEG_PATH}\n\n{exc}"
        ) from exc

    if result.returncode != 0:
        error_text = result.stderr.strip()

        if len(error_text) > 4000:
            error_text = error_text[-4000:]

        raise RuntimeError(
            "FFmpeg gặp lỗi.\n\n"
            f"{error_text}"
        )

    return result


# ============================================================
# AUDIO I/O
# ============================================================

def read_audio(path):
    """
    Read WAV/FLAC/OGG/AIFF directly with soundfile.

    MP3/M4A are decoded by FFmpeg into a temporary WAV.
    """

    path = str(path)
    ext = Path(path).suffix.lower()

    if ext in (".wav", ".flac", ".ogg", ".aiff", ".aif"):
        try:
            data, sr = sf.read(
                path,
                always_2d=True,
                dtype="float32",
            )
            return data, sr
        except Exception as exc:
            raise RuntimeError(
                f"Không thể đọc file âm thanh:\n{path}\n\n{exc}"
            ) from exc

    if ext in (".mp3", ".m4a"):
        with tempfile.TemporaryDirectory(prefix="stereo3d_") as temp_dir:
            temp_wav = os.path.join(temp_dir, "decoded.wav")

            run_ffmpeg([
                "-y",
                "-i",
                path,
                "-vn",
                "-ac",
                "2",
                "-ar",
                "48000",
                "-c:a",
                "pcm_s32le",
                temp_wav,
            ])

            try:
                data, sr = sf.read(
                    temp_wav,
                    always_2d=True,
                    dtype="float32",
                )
                return data, sr
            except Exception as exc:
                raise RuntimeError(
                    f"Không thể đọc dữ liệu âm thanh sau khi FFmpeg giải mã:\n\n{exc}"
                ) from exc

    raise ValueError(
        f"Định dạng đầu vào không được hỗ trợ: {ext}"
    )


def write_audio(path, data, sr):
    """
    Write normal lossless formats using soundfile.

    MP3/M4A are encoded by FFmpeg.
    """

    path = str(path)
    ext = Path(path).suffix.lower()

    if ext in (".wav", ".flac", ".ogg", ".aiff", ".aif"):
        try:
            sf.write(path, data, sr)
        except Exception as exc:
            raise RuntimeError(
                f"Không thể ghi file:\n{path}\n\n{exc}"
            ) from exc

        return

    if ext in (".mp3", ".m4a"):
        with tempfile.TemporaryDirectory(prefix="stereo3d_") as temp_dir:
            temp_wav = os.path.join(temp_dir, "processed.wav")

            try:
                sf.write(
                    temp_wav,
                    data,
                    sr,
                    subtype="PCM_16",
                )
            except Exception as exc:
                raise RuntimeError(
                    f"Không thể tạo WAV tạm:\n{exc}"
                ) from exc

            if ext == ".mp3":
                run_ffmpeg([
                    "-y",
                    "-i",
                    temp_wav,
                    "-c:a",
                    "libmp3lame",
                    "-q:a",
                    "2",
                    path,
                ])

            elif ext == ".m4a":
                run_ffmpeg([
                    "-y",
                    "-i",
                    temp_wav,
                    "-c:a",
                    "aac",
                    "-b:a",
                    "256k",
                    path,
                ])

        return

    raise ValueError(
        f"Định dạng đầu ra không được hỗ trợ: {ext}"
    )


# ============================================================
# AUDIO PROCESSING
# ============================================================

def stereoize(data):
    """Convert input to exactly two channels."""

    if data.ndim == 1:
        data = data[:, None]

    channels = data.shape[1]

    if channels == 1:
        return np.repeat(data, 2, axis=1)

    if channels == 2:
        return data[:, :2]

    # Multichannel:
    # Average the first two channels to create a stable stereo source.
    left = data[:, 0]
    right = data[:, 1]

    stereo = np.column_stack([
        left,
        right,
    ])

    return stereo


def resample_if_needed(data, sr, target_sr=48000):
    """High quality polyphase resampling."""

    if sr == target_sr:
        return data, sr

    gcd = math.gcd(int(sr), int(target_sr))

    up = target_sr // gcd
    down = sr // gcd

    result_channels = []

    for channel in range(data.shape[1]):
        resampled = signal.resample_poly(
            data[:, channel],
            up,
            down,
        )
        result_channels.append(resampled)

    length = min(len(x) for x in result_channels)

    result = np.column_stack([
        x[:length]
        for x in result_channels
    ])

    return result.astype(np.float32), target_sr


def smooth_position(position, smooth):
    """
    Smooth movement using a one-pole low-pass filter.

    smooth:
        0 = almost no smoothing
        1 = maximum smoothing
    """

    smooth = float(np.clip(smooth, 0.0, 1.0))

    if smooth <= 0.001:
        return position

    alpha = 0.01 + (1.0 - smooth) * 0.25

    result = np.empty_like(position)

    result[0] = position[0]

    for i in range(1, len(position)):
        result[i] = (
            alpha * position[i]
            + (1.0 - alpha) * result[i - 1]
        )

    return result


def triangle_wave(length, cycles):
    """Generate triangle wave in range -1..1."""

    if length <= 0:
        return np.empty(0, dtype=np.float32)

    t = np.arange(length, dtype=np.float64)

    phase = (t / length * cycles) % 1.0

    wave = 4.0 * np.abs(
        phase - np.floor(phase + 0.5)
    ) - 1.0

    return wave.astype(np.float32)


def sine_wave(length, cycles):
    """Generate sine movement in range -1..1."""

    if length <= 0:
        return np.empty(0, dtype=np.float32)

    t = np.arange(length, dtype=np.float64)

    phase = t / length * cycles

    wave = np.sin(
        phase * 2.0 * np.pi
    )

    return wave.astype(np.float32)


def equal_power_pan(position):
    """
    Equal-power stereo panning.

    position:
        -1 = left
         0 = center
        +1 = right
    """

    position = np.clip(position, -1.0, 1.0)

    angle = (position + 1.0) * np.pi / 4.0

    left = np.cos(angle)
    right = np.sin(angle)

    return left, right


def one_pole_smooth(signal_data, alpha):
    """Smooth a time-varying signal."""

    alpha = float(np.clip(alpha, 0.0001, 1.0))

    result = np.empty_like(signal_data)

    result[0] = signal_data[0]

    for i in range(1, len(signal_data)):
        result[i] = (
            alpha * signal_data[i]
            + (1.0 - alpha) * result[i - 1]
        )

    return result


def fractional_delay(signal_data, delay_samples):
    """
    Apply a fractional delay using linear interpolation.
    """

    n = len(signal_data)

    if n == 0:
        return signal_data.copy()

    positions = (
        np.arange(n, dtype=np.float64)
        - float(delay_samples)
    )

    positions = np.clip(
        positions,
        0,
        n - 1,
    )

    x = np.arange(n, dtype=np.float64)

    return np.interp(
        positions,
        x,
        signal_data,
    ).astype(np.float32)


def apply_highpass(data, sr, cutoff=28.0):
    """Remove extremely low frequencies."""

    if cutoff <= 0:
        return data

    nyquist = sr / 2.0

    if cutoff >= nyquist:
        return data

    sos = signal.butter(
        2,
        cutoff,
        btype="highpass",
        fs=sr,
        output="sos",
    )

    result = np.empty_like(data)

    for channel in range(data.shape[1]):
        result[:, channel] = signal.sosfilt(
            sos,
            data[:, channel],
        )

    return result


def apply_dynamic_lowpass(data, sr, cutoff_values):
    """
    Apply a slowly varying low-pass filter.

    To avoid expensive per-sample filtering, the cutoff
    is smoothed and converted into a stable average cutoff.
    """

    if len(data) == 0:
        return data

    cutoff_values = np.asarray(
        cutoff_values,
        dtype=np.float64,
    )

    cutoff_values = np.clip(
        cutoff_values,
        1000.0,
        sr * 0.45,
    )

    # Use a smoothed average cutoff.
    # This preserves performance on low-end CPUs.
    cutoff = float(
        np.percentile(
            cutoff_values,
            50,
        )
    )

    sos = signal.butter(
        2,
        cutoff,
        btype="lowpass",
        fs=sr,
        output="sos",
    )

    result = np.empty_like(data)

    for channel in range(data.shape[1]):
        result[:, channel] = signal.sosfilt(
            sos,
            data[:, channel],
        )

    return result


def process_audio(
    data,
    sr,
    cycle_seconds=8.0,
    depth=1.0,
    distance=0.0,
    front_back=0.0,
    smooth=0.35,
    output_gain=0.0,
    movement="Sine",
):
    """
    Main stereo spatial processing.

    This creates a stereo illusion using:
        - equal-power panning
        - distance attenuation
        - high-frequency attenuation
        - small inter-channel delay
        - front/back modulation
        - smooth movement

    It does NOT create true binaural/HRTF 3D audio.
    """

    data = stereoize(data).astype(np.float32)

    if len(data) == 0:
        return data

    # --------------------------------------------------------
    # Pre-clean
    # --------------------------------------------------------

    data = apply_highpass(
        data,
        sr,
        cutoff=28.0,
    )

    # Create mono source for controlled spatial placement.
    source = (
        data[:, 0] * 0.5
        + data[:, 1] * 0.5
    )

    source = source.astype(np.float32)

    n = len(source)

    # --------------------------------------------------------
    # Movement
    # --------------------------------------------------------

    cycle_seconds = max(
        0.1,
        float(cycle_seconds),
    )

    depth = float(
        np.clip(depth, 0.0, 1.0)
    )

    smooth = float(
        np.clip(smooth, 0.0, 1.0)
    )

    front_back = float(
        np.clip(front_back, -1.0, 1.0)
    )

    distance = float(
        np.clip(distance, 0.0, 1.0)
    )

    cycles = max(
        0.05,
        n / sr / cycle_seconds,
    )

    if movement.lower() == "triangle":
        raw_position = triangle_wave(
            n,
            cycles,
        )
    else:
        raw_position = sine_wave(
            n,
            cycles,
        )

    position = raw_position * depth

    position = smooth_position(
        position,
        smooth,
    )

    # --------------------------------------------------------
    # Panning
    # --------------------------------------------------------

    pan_left, pan_right = equal_power_pan(
        position
    )

    # Slight center compensation.
    pan_left = pan_left.astype(np.float32)
    pan_right = pan_right.astype(np.float32)

    # --------------------------------------------------------
    # Distance
    # --------------------------------------------------------

    # 0 = near
    # 1 = far

    distance_gain = (
        1.0
        - 0.38 * distance
    )

    # More distant sounds lose high frequency.
    near_cutoff = sr * 0.45
    far_cutoff = min(
        5000.0,
        sr * 0.35,
    )

    cutoff = (
        near_cutoff
        - (near_cutoff - far_cutoff) * distance
    )

    # --------------------------------------------------------
    # Front/back effect
    # --------------------------------------------------------

    # front_back:
    # -1 = more front
    # +1 = more back

    fb = front_back

    # Small delay for spatial impression.
    max_delay_ms = 5.0

    delay_amount = (
        abs(fb)
        * max_delay_ms
        / 1000.0
        * sr
    )

    if fb >= 0:
        # Back:
        # right channel receives slightly delayed signal.
        left_delay = 0.0
        right_delay = delay_amount
    else:
        # Front:
        # left channel receives slightly delayed signal.
        left_delay = delay_amount
        right_delay = 0.0

    left = fractional_delay(
        source,
        left_delay,
    )

    right = fractional_delay(
        source,
        right_delay,
    )

    # --------------------------------------------------------
    # Apply panning
    # --------------------------------------------------------

    left *= pan_left
    right *= pan_right

    # --------------------------------------------------------
    # Distance / front-back cues
    # --------------------------------------------------------

    left *= distance_gain
    right *= distance_gain

    if abs(fb) > 0.001:
        # Slight level asymmetry creates a subtle spatial cue.
        if fb > 0:
            left *= 1.0 - 0.035 * abs(fb)
            right *= 1.0 + 0.035 * abs(fb)
        else:
            left *= 1.0 + 0.035 * abs(fb)
            right *= 1.0 - 0.035 * abs(fb)

    output = np.column_stack([
        left,
        right,
    ]).astype(np.float32)

    # --------------------------------------------------------
    # Distance low-pass
    # --------------------------------------------------------

    if distance > 0.001:
        cutoff_values = np.full(
            n,
            cutoff,
            dtype=np.float32,
        )

        output = apply_dynamic_lowpass(
            output,
            sr,
            cutoff_values,
        )

    # --------------------------------------------------------
    # Output gain
    # --------------------------------------------------------

    gain_linear = 10.0 ** (
        float(output_gain) / 20.0
    )

    output *= gain_linear

    # --------------------------------------------------------
    # Soft peak normalization
    # --------------------------------------------------------

    peak = float(
        np.max(
            np.abs(output)
        )
    )

    if peak > 0.98:
        output *= 0.98 / peak

    output = np.clip(
        output,
        -1.0,
        1.0,
    )

    return output.astype(np.float32)


# ============================================================
# GUI
# ============================================================

class Stereo3DAudioApp:

    def __init__(self, root):
        self.root = root
        self.root.title(
            "3D Stereo Audio Processor"
        )

        self.root.geometry(
            "720x620"
        )

        self.root.minsize(
            680,
            580,
        )

        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()

        self.cycle = tk.DoubleVar(
            value=8.0
        )

        self.depth = tk.DoubleVar(
            value=1.0
        )

        self.distance = tk.DoubleVar(
            value=0.0
        )

        self.front_back = tk.DoubleVar(
            value=0.0
        )

        self.smooth = tk.DoubleVar(
            value=0.35
        )

        self.output_gain = tk.DoubleVar(
            value=0.0
        )

        self.movement = tk.StringVar(
            value="Sine"
        )

        self.status = tk.StringVar(
            value="Sẵn sàng."
        )

        self.progress_value = tk.DoubleVar(
            value=0.0
        )

        self.build_gui()

    # --------------------------------------------------------
    # GUI helpers
    # --------------------------------------------------------

    def build_gui(self):

        main = ttk.Frame(
            self.root,
            padding=16,
        )

        main.pack(
            fill="both",
            expand=True,
        )

        title = ttk.Label(
            main,
            text="3D Stereo Audio Processor",
            font=("Segoe UI", 18, "bold"),
        )

        title.pack(
            anchor="w",
            pady=(0, 4),
        )

        subtitle = ttk.Label(
            main,
            text=(
                "Tạo hiệu ứng âm thanh di chuyển "
                "trái ↔ phải bằng loa stereo."
            ),
        )

        subtitle.pack(
            anchor="w",
            pady=(0, 15),
        )

        # ----------------------------------------------------
        # Input
        # ----------------------------------------------------

        input_frame = ttk.LabelFrame(
            main,
            text="Âm thanh đầu vào",
            padding=10,
        )

        input_frame.pack(
            fill="x",
            pady=(0, 10),
        )

        ttk.Entry(
            input_frame,
            textvariable=self.input_path,
        ).pack(
            side="left",
            fill="x",
            expand=True,
            padx=(0, 8),
        )

        ttk.Button(
            input_frame,
            text="Chọn file",
            command=self.choose_input,
        ).pack(
            side="right",
        )

        # ----------------------------------------------------
        # Output
        # ----------------------------------------------------

        output_frame = ttk.LabelFrame(
            main,
            text="Âm thanh đầu ra",
            padding=10,
        )

        output_frame.pack(
            fill="x",
            pady=(0, 10),
        )

        ttk.Entry(
            output_frame,
            textvariable=self.output_path,
        ).pack(
            side="left",
            fill="x",
            expand=True,
            padx=(0, 8),
        )

        ttk.Button(
            output_frame,
            text="Lưu thành...",
            command=self.choose_output,
        ).pack(
            side="right",
        )

        # ----------------------------------------------------
        # Controls
        # ----------------------------------------------------

        controls = ttk.LabelFrame(
            main,
            text="Hiệu ứng 3D",
            padding=12,
        )

        controls.pack(
            fill="both",
            expand=True,
            pady=(0, 10),
        )

        self.add_slider(
            controls,
            "Chu kỳ di chuyển (giây)",
            self.cycle,
            1.0,
            30.0,
            0,
        )

        self.add_slider(
            controls,
            "Độ rộng L ↔ R",
            self.depth,
            0.0,
            1.0,
            1,
        )

        self.add_slider(
            controls,
            "Khoảng cách",
            self.distance,
            0.0,
            1.0,
            2,
        )

        self.add_slider(
            controls,
            "Front ↔ Back",
            self.front_back,
            -1.0,
            1.0,
            3,
        )

        self.add_slider(
            controls,
            "Độ mượt",
            self.smooth,
            0.0,
            1.0,
            4,
        )

        self.add_slider(
            controls,
            "Gain đầu ra (dB)",
            self.output_gain,
            -12.0,
            12.0,
            5,
        )

        # ----------------------------------------------------
        # Movement mode
        # ----------------------------------------------------

        movement_frame = ttk.Frame(
            controls
        )

        movement_frame.grid(
            row=6,
            column=0,
            columnspan=3,
            sticky="ew",
            pady=(10, 0),
        )

        ttk.Label(
            movement_frame,
            text="Kiểu chuyển động:",
        ).pack(
            side="left",
            padx=(0, 10),
        )

        ttk.Radiobutton(
            movement_frame,
            text="Sine",
            value="Sine",
            variable=self.movement,
        ).pack(
            side="left",
            padx=5,
        )

        ttk.Radiobutton(
            movement_frame,
            text="Triangle",
            value="Triangle",
            variable=self.movement,
        ).pack(
            side="left",
            padx=5,
        )

        # ----------------------------------------------------
        # Progress
        # ----------------------------------------------------

        progress_frame = ttk.Frame(
            main
        )

        progress_frame.pack(
            fill="x",
            pady=(0, 8),
        )

        self.progress = ttk.Progressbar(
            progress_frame,
            variable=self.progress_value,
            maximum=100,
        )

        self.progress.pack(
            fill="x",
        )

        ttk.Label(
            progress_frame,
            textvariable=self.status,
        ).pack(
            anchor="w",
            pady=(5, 0),
        )

        # ----------------------------------------------------
        # Process button
        # ----------------------------------------------------

        self.process_button = ttk.Button(
            main,
            text="TẠO ÂM THANH 3D",
            command=self.start_processing,
        )

        self.process_button.pack(
            fill="x",
            ipady=8,
        )

    def add_slider(
        self,
        parent,
        label,
        variable,
        minimum,
        maximum,
        row,
    ):

        ttk.Label(
            parent,
            text=label,
        ).grid(
            row=row,
            column=0,
            sticky="w",
            pady=7,
        )

        slider = ttk.Scale(
            parent,
            from_=minimum,
            to=maximum,
            variable=variable,
            orient="horizontal",
        )

        slider.grid(
            row=row,
            column=1,
            sticky="ew",
            padx=12,
            pady=7,
        )

        value_label = ttk.Label(
            parent,
            width=8,
        )

        value_label.grid(
            row=row,
            column=2,
            sticky="e",
            pady=7,
        )

        def update_value(*args):
            value = variable.get()

            if maximum <= 1.0:
                value_label.config(
                    text=f"{value:.2f}"
                )
            elif maximum <= 30:
                value_label.config(
                    text=f"{value:.1f}"
                )
            else:
                value_label.config(
                    text=f"{value:.1f}"
                )

        variable.trace_add(
            "write",
            update_value,
        )

        update_value()

        parent.columnconfigure(
            1,
            weight=1,
        )

    # --------------------------------------------------------
    # File selection
    # --------------------------------------------------------

    def choose_input(self):

        path = filedialog.askopenfilename(
            title="Chọn file âm thanh",
            filetypes=[
                (
                    "Audio files",
                    "*.wav *.flac *.ogg *.aiff *.aif *.mp3 *.m4a",
                ),
                (
                    "All files",
                    "*.*",
                ),
            ],
        )

        if not path:
            return

        self.input_path.set(path)

        input_file = Path(path)

        output_path = (
            input_file.parent
            / f"{input_file.stem}_3D.wav"
        )

        self.output_path.set(
            str(output_path)
        )

    def choose_output(self):

        path = filedialog.asksaveasfilename(
            title="Chọn file đầu ra",
            defaultextension=".wav",
            filetypes=[
                (
                    "WAV",
                    "*.wav",
                ),
                (
                    "FLAC",
                    "*.flac",
                ),
                (
                    "OGG",
                    "*.ogg",
                ),
                (
                    "MP3",
                    "*.mp3",
                ),
                (
                    "M4A",
                    "*.m4a",
                ),
                (
                    "AIFF",
                    "*.aiff",
                ),
            ],
        )

        if path:
            self.output_path.set(path)

    # --------------------------------------------------------
    # Processing
    # --------------------------------------------------------

    def start_processing(self):

        input_path = self.input_path.get().strip()
        output_path = self.output_path.get().strip()

        if not input_path:
            messagebox.showwarning(
                "Thiếu file",
                "Hãy chọn file âm thanh đầu vào.",
            )
            return

        if not os.path.isfile(input_path):
            messagebox.showerror(
                "Lỗi",
                "File đầu vào không tồn tại.",
            )
            return

        if not output_path:
            messagebox.showwarning(
                "Thiếu file",
                "Hãy chọn file đầu ra.",
            )
            return

        input_ext = Path(
            input_path
        ).suffix.lower()

        output_ext = Path(
            output_path
        ).suffix.lower()

        if input_ext not in SUPPORTED_INPUT:
            messagebox.showerror(
                "Định dạng không hỗ trợ",
                f"File đầu vào: {input_ext}",
            )
            return

        if output_ext not in SUPPORTED_OUTPUT:
            messagebox.showerror(
                "Định dạng không hỗ trợ",
                f"File đầu ra: {output_ext}",
            )
            return

        if os.path.abspath(input_path) == os.path.abspath(
            output_path
        ):
            messagebox.showerror(
                "Lỗi",
                "File đầu vào và đầu ra không được giống nhau.",
            )
            return

        self.process_button.config(
            state="disabled"
        )

        self.progress_value.set(0)

        self.status.set(
            "Đang xử lý..."
        )

        thread = threading.Thread(
            target=self.worker,
            args=(
                input_path,
                output_path,
            ),
            daemon=True,
        )

        thread.start()

    def worker(
        self,
        input_path,
        output_path,
    ):

        try:
            self.update_status(
                "Đang kiểm tra FFmpeg..."
            )

            check_ffmpeg()

            self.update_progress(
                5
            )

            self.update_status(
                "Đang đọc âm thanh..."
            )

            data, sr = read_audio(
                input_path
            )

            self.update_progress(
                20
            )

            self.update_status(
                f"Đang chuẩn hóa sample rate ({sr} Hz)..."
            )

            if sr < 32000 or sr > 96000:
                data, sr = resample_if_needed(
                    data,
                    sr,
                    48000,
                )

            self.update_progress(
                30
            )

            self.update_status(
                "Đang tạo hiệu ứng stereo 3D..."
            )

            processed = process_audio(
                data=data,
                sr=sr,
                cycle_seconds=self.cycle.get(),
                depth=self.depth.get(),
                distance=self.distance.get(),
                front_back=self.front_back.get(),
                smooth=self.smooth.get(),
                output_gain=self.output_gain.get(),
                movement=self.movement.get(),
            )

            self.update_progress(
                80
            )

            self.update_status(
                "Đang xuất file..."
            )

            output_parent = Path(
                output_path
            ).parent

            output_parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            write_audio(
                output_path,
                processed,
                sr,
            )

            self.update_progress(
                100
            )

            self.update_status(
                "Hoàn tất."
            )

            self.root.after(
                0,
                lambda: messagebox.showinfo(
                    "Hoàn tất",
                    "Đã tạo âm thanh 3D thành công.\n\n"
                    f"File:\n{output_path}",
                ),
            )

        except Exception as exc:

            error_message = str(exc)

            self.update_status(
                "Có lỗi xảy ra."
            )

            self.update_progress(
                0
            )

            self.root.after(
                0,
                lambda msg=error_message: messagebox.showerror(
                    "Lỗi",
                    msg,
                ),
            )

        finally:

            self.root.after(
                0,
                lambda: self.process_button.config(
                    state="normal"
                ),
            )

    def update_progress(self, value):

        self.root.after(
            0,
            lambda: self.progress_value.set(
                value
            ),
        )

    def update_status(self, text):

        self.root.after(
            0,
            lambda: self.status.set(
                text
            ),
        )


# ============================================================
# MAIN
# ============================================================

def main():

    root = tk.Tk()

    try:
        style = ttk.Style()

        if "vista" in style.theme_names():
            style.theme_use("vista")

    except Exception:
        pass

    app = Stereo3DAudioApp(root)

    root.mainloop()


if __name__ == "__main__":
    main()
