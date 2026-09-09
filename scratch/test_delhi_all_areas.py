import sys
import asyncio
from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding='utf-8')

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})
        
        await page.goto("http://localhost:8081/", wait_until="networkidle")
        await asyncio.sleep(1)
        
        # Test 1: Chatbot QA output check for All Delhi NCR
        print("\n--- TEST 1: CHATBOT RESPONSE CHECK ---")
        await page.click("#hydroFabContainer")
        await asyncio.sleep(1)
        
        first_card = page.locator(".chat-option-card").first
        await first_card.click()
        await asyncio.sleep(1)
        
        bot_response = await page.locator(".chat-msg.bot").last.inner_text()
        print("Chatbot Output:\n", bot_response)
        assert "all of Delhi NCR" in bot_response, "Chatbot response does not mention all of Delhi NCR!"
        print("✅ PASSED: Chatbot correctly states 'all of Delhi NCR'!")
        
        # Close chatbot
        await page.click(".chat-close-btn")
        await asyncio.sleep(0.5)
        
        # Test 2: Multi-Delhi Region Route Tests
        delhi_test_pairs = [
            ("Connaught Place, Central Delhi", "Lajpat Nagar, South Delhi"),
            ("Rohini Sector 10, North West Delhi", "Pitampura, North Delhi"),
            ("Uttam Nagar West, West Delhi", "Dwarka Sector 21, South West Delhi"),
            ("Anand Vihar, East Delhi", "ITO Crossing, Central Delhi")
        ]
        
        print("\n--- TEST 2: ALL DELHI ROUTE SEARCH & GEOCODING ---")
        for orig, dest in delhi_test_pairs:
            print(f"\nTesting route: [{orig}] -> [{dest}]...")
            await page.fill("#inputOrigin", orig)
            await page.fill("#inputDestination", dest)
            await page.click(".btn-find-route")
            await asyncio.sleep(1.5)
            
            # Check route cards output
            route_items = page.locator(".route-item")
            count = await route_items.count()
            print(f"  Generated {count} routes successfully.")
            assert count >= 2, f"Failed to generate routes for {orig} -> {dest}"
            
            rec_text = await route_items.first.inner_text()
            print(f"  Recommended Route: {rec_text.splitlines()[0]}")
        
        print("\n🎉 ALL DELHI REGIONAL TESTS PASSED SUCCESSFULLY 100%!")
        await page.screenshot(path="scratch/delhi_regional_test_success.png")
        print("Saved screenshot to scratch/delhi_regional_test_success.png")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
