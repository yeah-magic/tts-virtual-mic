#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
speak-mic.py —— 把文字合成语音并「只」播进虚拟麦克风（VB-Audio CABLE Input），
            这样微信/QQ 语音通话时对方听到的就是合成的声音。

用法:
  python speak-mic.py -t "你要说的话"
  python speak-mic.py -c                 # 读剪贴板
  python speak-mic.py -t "..." -v zh-CN-YunxiNeural -r +10% -p +0Hz
  python speak-mic.py --list             # 列出可用设备
  python speak-mic.py --test             # 端到端自测（播 + 从 CABLE Output 录回来验证）
"""
import argparse
import asyncio
import os
import sys
import tempfile

import numpy as np

DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"
CABLE_SPK = "CABLE In 16ch"
CABLE_MIC = "CABLE Output"


def list_devices():
    import soundcard as sc
    print("=== 播放设备 (speakers) ===")
    for s in sc.all_speakers():
        print(" -", s.name)
    print("=== 录音设备 (microphones) ===")
    for m in sc.all_microphones(include_loopback=True):
        print(" -", m.name)


def pick_speaker(name_hint=CABLE_SPK):
    """优先精确匹配；否则退回任意名字含 cable 的播放设备。"""
    import soundcard as sc
    spk = sc.all_speakers()
    for s in spk:
        if name_hint.lower() in s.name.lower():
            return s
    for s in spk:
        if "cable" in s.name.lower():
            return s
    return None


def pick_mic(name_hint=CABLE_MIC):
    import soundcard as sc
    for m in sc.all_microphones(include_loopback=True):
        if name_hint.lower() in m.name.lower():
            return m
    return None


async def synth(text, voice, rate, pitch, out_path):
    import edge_tts
    kwargs = {}
    if rate:
        kwargs["rate"] = rate
    if pitch:
        kwargs["pitch"] = pitch
    com = edge_tts.Communicate(text, voice, **kwargs)
    await com.save(out_path)


def play_to_device(mp3_path, speaker):
    import miniaudio
    import soundcard as sc
    decoded = miniaudio.decode_file(mp3_path)
    pcm = np.asarray(decoded.samples, dtype=np.float32) / 32768.0
    ch = decoded.nchannels
    if ch > 1:
        pcm = pcm.reshape(-1, ch)
    else:
        pcm = pcm.reshape(-1, 1)
    speaker.play(pcm, samplerate=decoded.sample_rate, blocksize=2048)


def play_multi(mp3_path, speakers):
    """把同一段音频并发播到多个设备（用一个 Barrier 尽量对齐起点）。"""
    import miniaudio, threading
    decoded = miniaudio.decode_file(mp3_path)
    pcm = np.asarray(decoded.samples, dtype=np.float32) / 32768.0
    ch = decoded.nchannels
    pcm = pcm.reshape(-1, ch) if ch > 1 else pcm.reshape(-1, 1)
    barrier = threading.Barrier(len(speakers) + 1)
    errors = []

    def worker(spk):
        try:
            barrier.wait(timeout=2)
            spk.play(pcm, samplerate=decoded.sample_rate, blocksize=2048)
        except Exception as e:
            errors.append(f"{spk.name}: {e}")

    threads = [threading.Thread(target=worker, args=(s,), daemon=True) for s in speakers]
    for t in threads:
        t.start()
    barrier.wait(timeout=2)
    for t in threads:
        t.join()
    return errors


def record_check(seconds=2.5, samplerate=48000):
    """从 CABLE Output 录一段，返回峰值电平，用来确认虚拟麦里真的有声音。"""
    mic = pick_mic()
    if mic is None:
        print("!! 找不到 CABLE Output 录音设备")
        return None
    import soundcard as sc
    data = mic.record(int(seconds * samplerate), samplerate=samplerate)
    peak = float(np.abs(data).max())
    rms = float(np.sqrt((data ** 2).mean()))
    return peak, rms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-t", "--text")
    ap.add_argument("-c", "--clip", action="store_true", help="从剪贴板取文字")
    ap.add_argument("-v", "--voice", default=DEFAULT_VOICE)
    ap.add_argument("-r", "--rate", default="+0%")
    ap.add_argument("-p", "--pitch", default="+0Hz")
    ap.add_argument("--device", default=CABLE_SPK)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--check", action="store_true", help="只做录音电平检测")
    ap.add_argument("--monitor", action="store_true", help="同时播到默认扬声器(自己也能听到)")
    ap.add_argument("-a", "--also", action="append", default=[], metavar="设备名", help="额外再播到某个设备，可重复")
    args = ap.parse_args()

    if args.list:
        list_devices()
        return

    if args.check:
        r = record_check(2.0)
        print("录音电平:", r)
        return

    text = args.text
    if args.clip or not text:
        try:
            import tkinter
            r = tkinter.Tk()
            r.withdraw()
            text = r.clipboard_get()
            r.destroy()
        except Exception as e:
            print("读取剪贴板失败:", e)
            sys.exit(1)
    text = (text or "").strip()
    if not text:
        print("没有要说的内容")
        sys.exit(1)

    speaker = pick_speaker(args.device)
    if speaker is None:
        print(f"!! 找不到播放设备含 '{args.device}' 的设备，用 --list 看看")
        sys.exit(2)

    tmp = os.path.join(tempfile.gettempdir(), "dsh-speak-mic.mp3")
    try:
        asyncio.run(synth(text, args.voice, args.rate, args.pitch, tmp))
    except Exception as e:
        print("合成失败(检查网络/voice名):", e)
        sys.exit(3)

    targets = [speaker]
    import soundcard as _sc
    if args.monitor:
        targets.append(_sc.default_speaker())
    for extra in (args.also or []):
        sp = pick_speaker(extra)
        if sp is None:
            print(f"!! 跳过找不到的设备: {extra}")
        elif sp.name not in [x.name for x in targets]:
            targets.append(sp)

    errs = play_multi(tmp, targets)
    names = " + ".join(x.name for x in targets)
    print(f"OK 已播到 {names}: {text[:40]}")
    for e in errs:
        print("!!", e)
    if args.test:
        print("播完后再测电平:", record_check(1.5))
    try:
        os.remove(tmp)
    except OSError:
        pass


if __name__ == "__main__":
    main()
