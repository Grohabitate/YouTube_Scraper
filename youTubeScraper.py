from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi
import openai
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

openai.api_key = os.getenv("OPENAI_ACCESS")


@app.route("/summarize_youtube", methods=["POST"])
def summarize_youtube():
    """
    Expects JSON in the form: { "url": "https://www.youtube.com/watch?v=..." }
    Returns JSON: {
      "summary": "...",
      "tags": "...",
      "transcript": "...",
      "error": "...",    # only if something went wrong
    }
    """
    data = request.get_json()
    if not data or "url" not in data:
        return jsonify({"error": "No 'url' field found in JSON body"}), 400
    
    url = data["url"]
    print("Received URL:", url)

    # 1) Extract the video ID
    #    E.g. "https://www.youtube.com/watch?v=4vIl4G3-yk8"
    #    We'll parse it robustly with the built-in URL library
    import urllib.parse
    parsed = urllib.parse.urlparse(url)
    video_id = urllib.parse.parse_qs(parsed.query).get("v")
    if not video_id:
        return jsonify({"error": "Invalid YouTube URL or missing ?v= parameter"}), 400
    video_id = video_id[0]
    print("Extracted video ID:", video_id)

    # 2) Get the transcript
    try:
        transcript_data = YouTubeTranscriptApi.get_transcript(video_id)
    except Exception as e:
        return jsonify({"error": f"Could not retrieve transcript: {str(e)}"}), 400

    # 3) Combine transcript text
    output = ""
    for line in transcript_data:
        output += line["text"] + "\n"

    # 4) Call OpenAI - SUMMARY
    try:
        summary_response = openai.ChatCompletion.create(
            model="gpt-4o-mini",  # or "gpt-3.5-turbo" / "gpt-4", etc.
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert analyst who specializes in summarizing scraped YouTube data."
                },
                {
                    "role": "assistant",
                    "content": "Write a 100-word summary of this video."
                },
                {
                    "role": "user",
                    "content": output
                }
            ]
        )
        summary = summary_response.choices[0].message.content
    except Exception as e:
        return jsonify({"error": f"OpenAI Summary request failed: {str(e)}"}), 400

    # 5) Call OpenAI - TAGS
    try:
        tags_response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert analyst who specializes in summarizing scraped YouTube data."
                },
                {
                    "role": "assistant",
                    "content": "Output a list of tags for this blog post in a Python list, like ['item1','item2','item3']."
                },
                {
                    "role": "user",
                    "content": output
                }
            ]
        )
        tags = tags_response.choices[0].message.content
    except Exception as e:
        return jsonify({"error": f"OpenAI Tags request failed: {str(e)}"}), 400

    # 6) Return final JSON result
    return jsonify({
        "summary": summary.strip(),
        "tags": tags.strip(),
        "transcript": output.strip()
    })


if __name__ == "__main__":
    app.run(port=5000, debug=True)
