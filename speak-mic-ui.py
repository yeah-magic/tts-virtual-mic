#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
speak-mic-ui.py —— 文字转语音的小窗口（tkinter，零额外依赖）

功能：
  - 多行输入，回车换行，Ctrl+Enter 播放
  - 音色下拉（中文神经网络音色）、语速
  - 「同时播到耳机」开关
  - 一键读取剪贴板
  - 状态栏提示 / 播放中提示
"""
import asyncio
import os
import sys
import tempfile
import threading
import tkinter as tk
from tkinter import ttk, messagebox

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import speak_mic_core as core  # noqa: E402

VOICES = [
    ("晓晓（女·自然）", "zh-CN-XiaoxiaoNeural"),
    ("云希（男·年轻）", "zh-CN-YunxiNeural"),
    ("云健（男·浑厚）", "zh-CN-YunjianNeural"),
    ("晓伊（女·活泼）", "zh-CN-XiaoyiNeural"),
    ("云扬（男·新闻）", "zh-CN-YunyangNeural"),
    ("晓辰（女·温柔）", "zh-CN-XiaochenNeural"),
]
RATES = ["-20%", "-10%", "+0%", "+10%", "+20%", "+30%"]


class App:
    def __init__(self, root):
        self.root = root
        self.busy = False
        root.title("文字转语音 → 虚拟麦克风")
        root.geometry("560x430")
        root.minsize(480, 380)

        pad = {"padx": 10, "pady": 6}

        tk.Label(root, text="要说的话：", anchor="w").pack(fill="x", **pad)
        self.text = tk.Text(root, height=7, wrap="word", font=("Microsoft YaHei UI", 11))
        self.text.pack(fill="both", expand=True, padx=10)
        self.text.bind("<Control-Return>", lambda e: (self.speak(), "break")[1])

        bar = tk.Frame(root)
        bar.pack(fill="x", **pad)

        tk.Label(bar, text="音色").pack(side="left")
        self.voice = ttk.Combobox(bar, values=[v[0] for v in VOICES], state="readonly", width=16)
        self.voice.current(0)
        self.voice.pack(side="left", padx=(4, 12))

        tk.Label(bar, text="语速").pack(side="left")
        self.rate = ttk.Combobox(bar, values=RATES, state="readonly", width=6)
        self.rate.set("+0%")
        self.rate.pack(side="left", padx=(4, 12))

        self.monitor = tk.BooleanVar(value=True)
        tk.Checkbutton(bar, text="同时播到耳机", variable=self.monitor).pack(side="left")

        btns = tk.Frame(root)
        btns.pack(fill="x", **pad)
        self.b_speak = tk.Button(btns, text="▶ 播放 (Ctrl+Enter)", command=self.speak,
                                 font=("Microsoft YaHei UI", 10, "bold"), height=1, width=18)
        self.b_speak.pack(side="left")
        tk.Button(btns, text="从剪贴板粘贴", command=self.paste, width=14).pack(side="left", padx=8)
        tk.Button(btns, text="清空", command=lambda: self.text.delete("1.0", "end"), width=8).pack(side="left")
        tk.Button(btns, text="设备信息", command=self.devices, width=10).pack(side="right")

        self.status = tk.Label(root, text="就绪", anchor="w", fg="#555")
        self.status.pack(fill="x", padx=10, pady=(0, 8))

    # ---------- 动作 ----------
    def paste(self):
        try:
            self.text.insert("end", self.root.clipboard_get())
            self.set_status("已从剪贴板粘贴")
        except Exception as e:
            self.set_status(f"剪贴板读取失败: {e}")

    def devices(self):
        try:
            import soundcard as sc
            names = [s.name for s in sc.all_speakers()]
            msg = "播放设备：\n" + "\n".join(" · " + n for n in names)
            msg += "\n\n默认播放设备：" + sc.default_speaker().name
            messagebox.showinfo("音频设备", msg)
        except Exception as e:
            messagebox.showerror("设备信息", str(e))

    def set_status(self, s):
        self.status.config(text=s)
        self.root.update_idletasks()

    def speak(self):
        if self.busy:
            return
        text = self.text.get("1.0", "end").strip()
        if not text:
            self.set_status("先输入点内容")
            return
        voice = dict(VOICES)[self.voice.get()]
        rate = self.rate.get()
        monitor = self.monitor.get()
        self.busy = True
        self.b_speak.config(state="disabled", text="合成中…")
        self.set_status("正在合成语音…")
        threading.Thread(target=self._worker, args=(text, voice, rate, monitor), daemon=True).start()

    def _worker(self, text, voice, rate, monitor):
        core.init_com()
        tmp = os.path.join(tempfile.gettempdir(), "dsh-ui-tts.mp3")
        try:
            asyncio.run(core.synth(text, voice, rate, "+0Hz", tmp))
            speaker = core.pick_speaker()
            if speaker is None:
                raise RuntimeError("找不到 CABLE 播放设备")
            targets = [speaker]
            import soundcard as sc
            if monitor:
                targets.append(sc.default_speaker())
            self.root.after(0, lambda: self.set_status("正在播放…"))
            errs = core.play_multi(tmp, targets)
            names = " + ".join(t.name for t in targets)
            if errs:
                self.root.after(0, lambda: self.set_status("部分失败: " + "; ".join(errs)))
            else:
                self.root.after(0, lambda: self.set_status(f"已播放 → {names}"))
        except Exception as e:
            import traceback
            msg = str(e)
            try:
                with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts-ui-error.log"), "a", encoding="utf-8") as fh:
                    fh.write(traceback.format_exc() + "\n")
            except Exception:
                pass
            self.root.after(0, lambda: self.set_status(f"失败: {msg}"))
        finally:
            try:
                os.remove(tmp)
            except OSError:
                pass
            self.busy = False
            self.root.after(0, lambda: self.b_speak.config(state="normal", text="▶ 播放 (Ctrl+Enter)"))


def main():
    root = tk.Tk()
    try:
        root.iconbitmap(default="")
    except Exception:
        pass
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
