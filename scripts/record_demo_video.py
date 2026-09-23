import asyncio
import os
import glob
import shutil
from playwright.async_api import async_playwright

ARTIFACT_DIR = "/config/.gemini/antigravity/brain/4ac74992-6020-4c33-9904-61d6a74f18bb"
TEMP_VIDEO_DIR = "/tmp/playwright_video"

async def record_demo():
    print("--- Starting Playwright Demo Video Recording ---")
    os.makedirs(TEMP_VIDEO_DIR, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=TEMP_VIDEO_DIR,
            record_video_size={"width": 1280, "height": 720}
        )
        page = await context.new_page()

        url = "https://board-game-frontend-401956137467.us-central1.run.app"
        print(f"Navigating to {url}...")
        await page.goto(url, wait_until="networkidle")
        await page.wait_for_timeout(2000)

        # 1. Warm Greeting ("hi")
        print("Step 1: Sending 'hi' greeting...")
        await page.fill("#input", "hi")
        await page.wait_for_timeout(1000)
        await page.click("button[type='submit']")
        
        # Wait for agent response to appear
        await page.wait_for_selector(".msg.agent", timeout=30000)
        await page.wait_for_timeout(3000)

        # 2. Click Floating Prompt Chip for Leaderboard
        print("Step 2: Clicking Leaderboard floating chip...")
        chip = await page.query_selector(".chip:has-text('Leaderboard'), .chip:has-text('Squad')")
        if chip:
            await chip.click()
            await page.wait_for_timeout(4000)
        else:
            await page.fill("#input", "Show the ELO leaderboard for Friday Night Strategists")
            await page.click("button[type='submit']")
            await page.wait_for_timeout(4000)

        # 3. Request 3D Video Trailer
        print("Step 3: Requesting 3D animated trailer video...")
        await page.fill("#input", "Generate a 3D animated trailer video for Suzerain Strategy Edition")
        await page.click("button[type='submit']")
        
        # Wait for video element or response
        await page.wait_for_timeout(12000)

        print("Closing context to save video...")
        await context.close()
        await browser.close()

    # Find the recorded video file and move to ARTIFACT_DIR
    videos = glob.glob(os.path.join(TEMP_VIDEO_DIR, "*.webm")) + glob.glob(os.path.join(TEMP_VIDEO_DIR, "*.mp4"))
    if videos:
        recorded_video = videos[0]
        target_path = os.path.join(ARTIFACT_DIR, "demo_walkthrough.mp4")
        
        # Convert webm/mp4 to standard mp4 via ffmpeg
        print(f"Converting recorded video {recorded_video} to {target_path} using ffmpeg...")
        os.system(f"ffmpeg -y -i '{recorded_video}' -c:v libx264 -pix_fmt yuv420p '{target_path}'")
        print(f"✅ Demo video saved to {target_path}")
    else:
        print("❌ No video file recorded.")

if __name__ == "__main__":
    asyncio.run(record_demo())
