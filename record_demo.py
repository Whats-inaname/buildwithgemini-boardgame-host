import os
import glob
import subprocess
import asyncio
from playwright.async_api import async_playwright

APP_URL = "http://localhost:8080"
RECORDINGS_DIR = "/config/Desktop/Session1/board-game-host/recordings"
ARTIFACTS_DIR = "/config/.gemini/antigravity/brain/4ac74992-6020-4c33-9904-61d6a74f18bb"

async def record_demo():
    os.makedirs(RECORDINGS_DIR, exist_ok=True)
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)

    # Clean old recordings
    for f in glob.glob(os.path.join(RECORDINGS_DIR, "*.webm")):
        try: os.remove(f)
        except Exception: pass

    print("Launching Chromium browser for full recording...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            record_video_dir=RECORDINGS_DIR,
            record_video_size={"width": 1280, "height": 800}
        )
        
        page = await context.new_page()
        print(f"Navigating to app: {APP_URL}")
        await page.goto(APP_URL, wait_until="networkidle")
        await asyncio.sleep(2)

        # 1. Click prompt chip
        print("Action 1: Clicking 4-Player Games prompt chip...")
        chip = page.locator('.chip[data-prompt*="Recommend a game"]')
        if await chip.count() > 0:
            await chip.click()
        else:
            await page.fill("#input", "Recommend a game for 4 players under 90 mins")
            await page.click('button[type="submit"]')

        # Wait for recommendation A2UI response
        print("Waiting for recommendation response...")
        await asyncio.sleep(8)

        # 2. Submitting prompt for image generation tool call
        print("Action 2: Submitting image generation prompt...")
        await page.fill("#input", "Generate custom box art for a dragon-themed strategy board game")
        await page.click('button[type="submit"]')

        # Wait 25 seconds while scrolling down to keep new messages/images in view
        print("Waiting for image generation tool call & card rendering...")
        for _ in range(5):
            await asyncio.sleep(5)
            await page.evaluate("const log = document.getElementById('log'); if(log) log.scrollTop = log.scrollHeight;")

        print("Finishing browser recording...")
        await page.close()
        await context.close()
        await browser.close()

    # Find recorded webm file
    webm_files = glob.glob(os.path.join(RECORDINGS_DIR, "*.webm"))
    if not webm_files:
        raise RuntimeError("No recorded video file found in recordings directory!")

    raw_video = max(webm_files, key=os.path.getmtime)
    print(f"Recorded raw video: {raw_video}")

    # Combine with lo-fi background audio using ffmpeg
    lofi_audio = "/config/Desktop/Session1/board-game-host/lofi_music.wav"
    output_mp4 = "/config/Desktop/Session1/board-game-host/demo_video.mp4"
    artifact_mp4 = os.path.join(ARTIFACTS_DIR, "demo_video.mp4")

    print("Merging video with upbeat lo-fi background music using ffmpeg...")
    cmd = [
        "ffmpeg", "-y",
        "-i", raw_video,
        "-stream_loop", "-1",
        "-i", lofi_audio,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        output_mp4
    ]
    subprocess.run(cmd, check=True)

    # Copy to artifacts directory
    subprocess.run(["cp", output_mp4, artifact_mp4], check=True)

    # Convert to optimized demo.gif for README
    output_gif = "/config/Desktop/Session1/board-game-host/demo.gif"
    print("Converting full recording to optimized looping GIF demo.gif...")
    gif_cmd = [
        "ffmpeg", "-y",
        "-i", raw_video,
        "-vf", "fps=12,scale=800:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse",
        output_gif
    ]
    subprocess.run(gif_cmd, check=True)

    print(f"Successfully generated updated demo video & GIF!\nMP4: {output_mp4}\nGIF: {output_gif}")

if __name__ == "__main__":
    asyncio.run(record_demo())
