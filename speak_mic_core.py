#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""speak_mic_core —— 文字转语音 → 虚拟麦克风 的公共函数（CLI 和 UI 共用）。"""
import asyncio
import os

import numpy as np

DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"
CABLE_SPK = "CABLE In 16ch"
CABLE_MIC = "CABLE Output"


def list_speakers():
    import soundcard as sc
    return [s.name for s in sc.all_speakers()]


def pick_speaker(name_hint=CABLE_SPK):
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


async def synth(text, voice=DEFAULT_VOICE, rate="+0%", pitch="+0Hz", out_path=None):
    import edge_tts
    if out_path is None:
        out_path = os.path.join(os.environ.get("TEMP", "."), "speak_mic_tmp.mp3")
    kwargs = {}
    if rate:
        kwargs["rate"] = rate
    if pitch:
        kwargs["pitch"] = pitch
    com = edge_tts.Communicate(text, voice, **kwargs)
    await com.save(out_path)
    return out_path


def load_pcm(mp3_path):
    import miniaudio
    decoded = miniaudio.decode_file(mp3_path)
    pcm = np.asarray(decoded.samples, dtype=np.float32) / 32768.0
    if decoded.nchannels > 1:
        pcm = pcm.reshape(-1, decoded.nchannels)
    else:
        pcm = pcm.reshape(-1, 1)
    return pcm, decoded.sample_rate


def init_com():
    """在线程里初始化 COM（WASAPI 需要，否则报 0x800401f0）。"""
    try:
        import ctypes
        ctypes.windll.ole32.CoInitializeEx(None, 0x2)  # COINIT_APARTMENTTHREADED
    except Exception:
        pass


def play_multi(mp3_path, speakers):
    """把同一段音频并发播到多个设备（Barrier 对齐起点），返回错误列表。"""
    import threading
    pcm, rate = load_pcm(mp3_path)
    if not speakers:
        return ["没有可播放设备"]
    barrier = threading.Barrier(len(speakers) + 1)
    errors = []

    def worker(spk):
        init_com()
        try:
            barrier.wait(timeout=3)
            spk.play(pcm, samplerate=rate, blocksize=2048)
        except Exception as e:
            errors.append(f"{spk.name}: {e}")

    threads = [threading.Thread(target=worker, args=(s,), daemon=True) for s in speakers]
    for t in threads:
        t.start()
    try:
        barrier.wait(timeout=3)
    except Exception:
        pass
    for t in threads:
        t.join()
    return errors


def record_level(seconds=2.0, samplerate=48000):
    mic = pick_mic()
    if mic is None:
        return None
    data = mic.record(int(seconds * samplerate), samplerate=samplerate)
    return float(np.abs(data).max()), float(np.sqrt((data ** 2).mean()))
