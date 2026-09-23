import numpy as np
from scipy.io import wavfile

def generate_lofi_track(filename="lofi_music.wav", duration_sec=30, sample_rate=44100):
    bpm = 88
    beat_sec = 60.0 / bpm
    total_samples = sample_rate * duration_sec
    audio = np.zeros(total_samples, dtype=np.float32)

    # Chord frequencies (Hz) for Cmaj7 -> Am7 -> Dm7 -> G7 progression
    chords = [
        [261.63, 329.63, 392.00, 493.88], # Cmaj7 (C4, E4, G4, B4)
        [220.00, 261.63, 329.63, 392.00], # Am7 (A3, C4, E4, G4)
        [293.66, 349.23, 440.00, 523.25], # Dm7 (D4, F4, A4, C5)
        [196.00, 246.94, 293.66, 349.23], # G7 (G3, B3, D4, F4)
    ]

    chord_duration = beat_sec * 4 # 1 bar per chord
    t = np.linspace(0, duration_sec, total_samples, endpoint=False)

    # 1. Warm Rhodes / Electric Piano Synthesizer
    for i, t_val in enumerate(t):
        chord_idx = int(t_val / chord_duration) % len(chords)
        t_in_bar = t_val % chord_duration
        
        # Envelope for soft keyboard strum
        envelope = np.exp(-1.5 * t_in_bar) * 0.4
        
        sample_val = 0.0
        for freq in chords[chord_idx]:
            # Fundamental + soft harmonics
            sample_val += np.sin(2 * np.pi * freq * t_val) * 0.6
            sample_val += np.sin(2 * np.pi * freq * 2 * t_val) * 0.2
            sample_val += np.sin(2 * np.pi * freq * 3 * t_val) * 0.08
            
        audio[i] += sample_val * envelope

    # 2. Lo-Fi Beat (Kick, Snare/Rimshot, Hi-Hat)
    num_beats = int(duration_sec / beat_sec)
    for b in range(num_beats):
        beat_start_sample = int(b * beat_sec * sample_rate)
        
        # Hi-Hat on every 8th note
        for sub in [0, 0.5]:
            hat_sample = int((b + sub) * beat_sec * sample_rate)
            hat_len = int(0.04 * sample_rate)
            if hat_sample + hat_len < total_samples:
                hat_noise = np.random.uniform(-1, 1, hat_len) * np.exp(-np.linspace(0, 10, hat_len)) * 0.08
                audio[hat_sample : hat_sample + hat_len] += hat_noise

        # Kick on beats 1 and 3 (0 and 2 in 0-indexed bar)
        if b % 4 in [0, 2]:
            kick_len = int(0.12 * sample_rate)
            if beat_start_sample + kick_len < total_samples:
                kt = np.linspace(0, 0.12, kick_len)
                kick_freq = 110 * np.exp(-25 * kt) + 40 # Pitch drop
                kick_wave = np.sin(2 * np.pi * kick_freq * kt) * np.exp(-8 * kt) * 0.35
                audio[beat_start_sample : beat_start_sample + kick_len] += kick_wave

        # Snare/Rimshot on beats 2 and 4 (1 and 3 in 0-indexed bar)
        if b % 4 in [1, 3]:
            snare_len = int(0.15 * sample_rate)
            if beat_start_sample + snare_len < total_samples:
                st = np.linspace(0, 0.15, snare_len)
                snare_body = np.sin(2 * np.pi * 180 * st) * np.exp(-15 * st) * 0.2
                snare_noise = np.random.uniform(-1, 1, snare_len) * np.exp(-12 * st) * 0.15
                audio[beat_start_sample : beat_start_sample + snare_len] += (snare_body + snare_noise)

    # 3. Subtle Vinyl Texture / Vinyl Noise
    crackle = np.random.normal(0, 0.008, total_samples)
    audio += crackle

    # Normalize audio
    max_val = np.max(np.abs(audio))
    if max_val > 0:
        audio = audio / max_val * 0.85

    # Save as 16-bit PCM WAV
    audio_int16 = (audio * 32767).astype(np.int16)
    wavfile.write(filename, sample_rate, audio_int16)
    print(f"Generated upbeat lo-fi track: {filename}")

if __name__ == "__main__":
    generate_lofi_track("lofi_music.wav", duration_sec=30)
