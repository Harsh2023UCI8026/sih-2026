import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})
        
        await page.goto("http://localhost:8081/", wait_until="networkidle")
        await asyncio.sleep(1)
        
        print("Opening chatbot...")
        await page.click("#hydroFabContainer")
        await asyncio.sleep(1) # wait for staggered animations
        
        await page.screenshot(path="scratch/chatbot_welcome_cards.png")
        print("Saved welcome screenshot to scratch/chatbot_welcome_cards.png")
        
        print("Clicking first option card (What does this website do)...")
        first_card = page.locator(".chat-option-card").first
        await first_card.click()
        await asyncio.sleep(0.8) # wait for typing indicator + response animation
        
        await page.screenshot(path="scratch/chatbot_reply_animated.png")
        print("Saved reply screenshot to scratch/chatbot_reply_animated.png")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
