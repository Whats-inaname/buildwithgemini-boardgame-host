import asyncio
import os
import glob
import shutil
from playwright.async_api import async_playwright

ARTIFACT_DIR = "/config/.gemini/antigravity/brain/4ac74992-6020-4c33-9904-61d6a74f18bb"
TEMP_VIDEO_DIR = "/tmp/playwright_full_demo"

STEPS = [
    {
        "title": "1. Warm Conversational Greeting",
        "prompt": "hi"
    },
    {
        "title": "2. Create Gaming Squad",
        "prompt": "Create a gaming group called 'Friday Night Strategists'"
    },
    {
        "title": "3. Save Location Profile & Gaming Tastes",
        "prompt": "Set my home city to Seattle, WA and my favorite genres to Political Strategy and Sci-Fi"
    },
    {
        "title": "4. Implicit Weather & Environmental Recommendation",
        "prompt": "Recommend a cozy rainy day board game for my location"
    },
    {
        "title": "5. Collaborative Session Planner",
        "prompt": "Start a session planner for 'Friday Night Strategists' this Saturday at 7pm with Catan, Wingspan, and Ticket to Ride"
    },
    {
        "title": "6. ELO Match Result & Squad Leaderboard",
        "prompt": "Record a match for 'Friday Night Strategists': Catan won by Alex against Sam and Taylor, then show our squad leaderboard"
    },
    {
        "title": "7. Rules & RAG Document Retrieval",
        "prompt": "What are the key setup rules and resource production rules for Catan?"
    },
    {
        "title": "8. 3D Animated Video Trailer Generation",
        "prompt": "Generate a 3D animated trailer video for Suzerain Strategy Edition"
    }
]

async def record_full_demo():
    print("--- Starting Full Step-by-Step Feature Walkthrough Video Recording ---")
    if os.path.exists(TEMP_VIDEO_DIR):
        shutil.rmtree(TEMP_VIDEO_DIR)
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

        for step in STEPS:
            print(f"\n▶️ DEMO STEP: {step['title']}")
            print(f"   Prompt: '{step['prompt']}'")

            # Ensure input field is re-enabled before proceeding
            await page.wait_for_selector("#input:not([disabled])", timeout=60000)
            await page.wait_for_timeout(1000)

            # Scroll log to bottom so latest chat state is visible
            await page.evaluate("const log = document.getElementById('log'); if(log) log.scrollTop = log.scrollHeight; window.scrollTo(0, document.body.scrollHeight);")

            # Fill input and click submit
            await page.fill("#input", step["prompt"])
            await page.wait_for_timeout(800)
            await page.click("button[type='submit']")

            # Wait for turn to start and finish
            await page.wait_for_timeout(2000)
            await page.wait_for_selector("#input:not([disabled])", timeout=60000)
            await page.wait_for_timeout(2500)
            
            # Smooth scroll to show full response
            await page.evaluate("const log = document.getElementById('log'); if(log) log.scrollTop = log.scrollHeight; window.scrollTo(0, document.body.scrollHeight);")

        print("Finalizing video recording...")
        await page.wait_for_timeout(3000)
        await context.close()
        await browser.close()

    # Find recorded video and process with ffmpeg
    videos = glob.glob(os.path.join(TEMP_VIDEO_DIR, "*.webm")) + glob.glob(os.path.join(TEMP_VIDEO_DIR, "*.mp4"))
    if videos:
        recorded_video = videos[0]
        target_path_docs = "/config/Desktop/Session1/board-game-host/docs/demo_walkthrough.mp4"
        target_path_artifacts = os.path.join(ARTIFACT_DIR, "demo_walkthrough.mp4")

        print(f"Encoding full video to standard MP4 with FFmpeg...")
        os.system(f"ffmpeg -y -i '{recorded_video}' -c:v libx264 -pix_fmt yuv420p '{target_path_docs}'")
        shutil.copy(target_path_docs, target_path_artifacts)
        print(f"✅ Full comprehensive demo video created successfully:\n   1. {target_path_docs}\n   2. {target_path_artifacts}")
    else:
        print("❌ No video file recorded.")

if __name__ == "__main__":
    asyncio.run(record_full_demo())
