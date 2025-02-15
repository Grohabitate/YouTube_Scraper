from flask import Flask, jsonify
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import openai
import os
from dotenv import load_dotenv
import urllib.parse
import requests

load_dotenv()

app = Flask(__name__)

# Create an OpenAI client instance (as in your working code)
client = openai.Client(api_key=os.getenv("OPENAI_ACCESS"))

# Define custom headers to mimic a browser and help prevent blocking by YouTube
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36'
}

# Create a custom Requests session and update its headers
custom_session = requests.Session()
custom_session.headers.update(HEADERS)
# Monkey-patch the default requests.request so that all calls use our custom headers
requests.request = custom_session.request

# Hardcoded YouTube URL for testing (use your own video URL here)
YOUTUBE_URL = "https://www.youtube.com/watch?v=4vIl4G3-yk8"

@app.route("/summarize_youtube", methods=["GET"])  # Using GET since URL is hardcoded
def summarize_youtube():
    """
    Fetches the transcript from a hardcoded YouTube URL, processes it,
    and returns a summary and tags using OpenAI.
    """
    print("Using hardcoded YouTube URL:", YOUTUBE_URL)

    # 1. Extract Video ID
    parsed = urllib.parse.urlparse(YOUTUBE_URL)
    video_id = urllib.parse.parse_qs(parsed.query).get("v")
    if not video_id:
        return jsonify({"error": "Invalid YouTube URL or missing ?v= parameter"}), 400
    video_id = video_id[0]
    print("Extracted video ID:", video_id)

    # 2. Get Transcript (Handling Errors)
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        print("✅ Transcript successfully retrieved.")
    except TranscriptsDisabled:
        return jsonify({"error": "Subtitles are disabled for this video. No transcript is available."}), 400
    except NoTranscriptFound:
        return jsonify({"error": "Transcript exists but is not accessible via the API."}), 400
    except Exception as e:
        return jsonify({"error": f"Could not retrieve transcript: {str(e)}"}), 400

    # 3. Combine transcript text
    transcript_text = "\n".join([line["text"] for line in transcript])

    # 4. Call OpenAI for Summary using "gpt-3.5-turbo" via the client instance
    summary = "Summary generation failed."
    try:
        summary_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert analyst who specializes in summarizing scraped YouTube data."},
                {"role": "assistant", "content": "Write a 100-word summary of this video."},
                {"role": "user", "content": transcript_text}
            ]
        )
        summary = summary_response.choices[0].message.content.strip()
        print("✅ Summary generated.")
    except Exception as e:
        print("⚠️ OpenAI Summary API failed:", str(e))
    
    # 5. Call OpenAI for Tags using "gpt-3.5-turbo" via the client instance
    tags = "Tag generation failed."
    try:
        tags_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert analyst who specializes in summarizing scraped YouTube data."},
                {"role": "assistant", "content": "Output a list of tags for this blog post in a Python list, like ['item1','item2','item3']."},
                {"role": "user", "content": transcript_text}
            ]
        )
        tags = tags_response.choices[0].message.content.strip()
        print("✅ Tags generated.")
    except Exception as e:
        print("⚠️ OpenAI Tags API failed:", str(e))

    # 6. Return JSON result
    return jsonify({
        "summary": summary,
        "tags": tags,
        "transcript": transcript_text
    })

if __name__ == "__main__":
    port = 5000
    print(f"🚀 Flask API is running! Open: http://127.0.0.1:{port}/summarize_youtube")
    app.run(port=port, debug=True)

