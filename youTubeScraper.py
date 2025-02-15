from flask import Flask, jsonify, request
import openai
import os
from dotenv import load_dotenv
import urllib.parse

# Selenium imports
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

load_dotenv()

app = Flask(__name__)

# Create an OpenAI client instance (using your API key)
client = openai.Client(api_key=os.getenv("OPENAI_ACCESS"))

def get_youtube_transcript(video_url):
    """
    Uses Selenium with headless Chrome to load a YouTube video page,
    click the "More actions" button and "Open transcript", and then
    scrape the transcript text.
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36"
    )
    
    # Initialize ChromeDriver (ensure chromedriver is in your PATH)
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        driver.get(video_url)
        # Wait for the "More actions" button and click it
        more_button = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='More actions']"))
        )
        more_button.click()
        
        # Wait for the "Open transcript" option to appear and click it
        transcript_option = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//yt-formatted-string[text()='Open transcript']"))
        )
        transcript_option.click()
        
        # Wait for the transcript panel to load and get all transcript lines
        transcript_lines = WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "ytd-transcript-renderer #segments yt-formatted-string"))
        )
        transcript_text = "\n".join([line.text for line in transcript_lines])
        return transcript_text
    except Exception as e:
        print("Error retrieving transcript via Selenium:", e)
        return None
    finally:
        driver.quit()

@app.route("/summarize_youtube", methods=["GET"])
def summarize_youtube_endpoint():
    """
    Endpoint that retrieves the transcript from a YouTube video using Selenium,
    then uses OpenAI to generate a summary and tags.
    Accepts a query parameter "url"; if not provided, uses a default URL.
    """
    # Get the YouTube URL from query parameters or use a default
    video_url = request.args.get("url", "https://www.youtube.com/watch?v=YOUR_DEFAULT_VIDEO_ID")
    print("Processing video URL:", video_url)
    
    # Use Selenium to get the transcript
    transcript_text = get_youtube_transcript(video_url)
    if not transcript_text:
        return jsonify({"error": "Failed to retrieve transcript via Selenium."}), 400
    
    # Use OpenAI to generate a summary
    summary = "Summary generation failed."
    try:
        summary_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert analyst who summarizes YouTube videos."},
                {"role": "assistant", "content": "Write a 100-word summary of this video."},
                {"role": "user", "content": transcript_text}
            ]
        )
        summary = summary_response.choices[0].message.content.strip()
        print("✅ Summary generated.")
    except Exception as e:
        print("⚠️ OpenAI Summary API error:", e)
    
    # Use OpenAI to generate tags
    tags = "Tag generation failed."
    try:
        tags_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert analyst who generates blog tags."},
                {"role": "assistant", "content": "Output a list of tags for this blog post in a Python list, like ['item1','item2','item3']."},
                {"role": "user", "content": transcript_text}
            ]
        )
        tags = tags_response.choices[0].message.content.strip()
        print("✅ Tags generated.")
    except Exception as e:
        print("⚠️ OpenAI Tags API error:", e)
    
    # Return the results as JSON
    return jsonify({
        "transcript": transcript_text,
        "summary": summary,
        "tags": tags
    })

if __name__ == "__main__":
    port = 5000
    print(f"🚀 Flask API is running! Open: http://127.0.0.1:{port}/summarize_youtube")
    app.run(port=port, debug=True)
