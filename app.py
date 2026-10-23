import os
import json
import streamlit as st
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai
from moviepy.video.io.VideoFileClip import VideoFileClip

st.set_page_config(page_title="AI YouTube Shorts Maker", page_icon="🎬", layout="centered")

st.title("🎬 AI YouTube Shorts Maker")
st.write("যেকোনো বড় ইউটিউব ভিডিওর লিংক দিন, AI অটোমেটিক সেরা অংশ খুঁজে 9:16 শর্টস বানিয়ে দেবে!")

# ইনপুট ফিল্ড
api_key = st.text_input("🔑 আপনার Gemini API Key দিন", type="password")
youtube_url = st.text_input("🔗 YouTube Video Link পেস্ট করুন", placeholder="https://www.youtube.com/watch?v=...")

def extract_video_id(url):
    if "v=" in url:
        return url.split("v=")[1].split("&")[0]
    elif "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0]
    elif "shorts/" in url:
        return url.split("shorts/")[1].split("?")[0]
    return url.strip()

if st.button("🚀 ভাইরাল শর্টস তৈরি করুন", type="primary"):
    if not api_key or not youtube_url:
        st.error("❌ অনুগ্রহ করে API Key এবং YouTube Link উভয়ই দিন!")
    else:
        with st.spinner("⏳ প্রসেসিং চলছে... ভিডিও ডাউনলোড ও এআই অ্যানালাইসিস হচ্ছে, দয়া করে অপেক্ষা করুন..."):
            try:
                genai.configure(api_key=api_key.strip())
                video_id = extract_video_id(youtube_url)
                
                # ১. ক্যাপশন বা ট্রান্সক্রিপ্ট নেওয়া
                try:
                    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                    transcript = transcript_list.find_transcript(['en', 'bn', 'hi', 'es', 'ar']).fetch()
                except Exception:
                    transcript = YouTubeTranscriptApi.get_transcript(video_id)
                    
                formatted_text = "\n".join([f"[{round(item['start'], 2)}s] {item['text']}" for item in transcript])
                
                # ২. Gemini AI দিয়ে সেরা অংশ খোঁজা
                model = genai.GenerativeModel("gemini-2.5-flash")
                prompt = f"""
                You are an expert short-form video editor like OpusClip. 
                Analyze this video transcript with timestamps in seconds. 
                Find the single MOST engaging, viral-worthy segment between 30 and 55 seconds long.
                Return ONLY a valid JSON object in this exact format, with no extra text or markdown:
                {{"start_time": 60.0, "end_time": 105.0, "title": "Catchy Viral Title", "score": 95, "reason": "Why this clip will go viral"}}
                
                Transcript:
                {formatted_text[:30000]}
                """
                
                response = model.generate_content(prompt)
                clean_json = response.text.replace("```json", "").replace("```", "").strip()
                clip_data = json.loads(clean_json)
                
                start_t = float(clip_data['start_time'])
                end_t = float(clip_data['end_time'])
                
                st.success(f"🎬 **টাইটেল:** {clip_data.get('title')}")
                st.info(f"🔥 ভাইরালিটি স্কোর: {clip_data.get('score')}/100 | সময়: {start_t}s থেকে {end_t}s")

                # ৩. ভিডিও ডাউনলোড ও কাটা
                input_video_path = "downloaded_video.mp4"
                if os.path.exists(input_video_path):
                    os.remove(input_video_path)
                    
                ydl_opts = {
                    'format': 'best[ext=mp4][height<=720]/best[ext=mp4]',
                    'outtmpl': input_video_path,
                    'quiet': True
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([youtube_url])
                    
                output_path = "viral_short_output.mp4"
                with VideoFileClip(input_video_path) as video:
                    if end_t > video.duration:
                        end_t = video.duration
                    short_clip = video.subclip(start_t, end_t)
                    w, h = short_clip.size
                    
                    target_w = int(h * 9 / 16)
                    if target_w % 2 != 0:
                        target_w -= 1
                        
                    x_center = w / 2
                    cropped_clip = short_clip.crop(
                        x1=int(x_center - target_w / 2),
                        y1=0,
                        x2=int(x_center + target_w / 2),
                        y2=h
                    )
                    cropped_clip.write_videofile(
                        output_path, codec="libx264", audio_codec="aac", preset="ultrafast", logger=None
                    )
                
                # ৪. সাইটে ভিডিও দেখানো ও ডাউনলোডের ব্যবস্থা
                st.video(output_path)
                with open(output_path, "rb") as file:
                    st.download_button(
                        label="⬇️ আপনার শর্টস ভিডিও ডাউনলোড করুন",
                        data=file,
                        file_name="viral_short.mp4",
                        mime="video/mp4"
                    )
            except Exception as e:
                st.error(f"⚠️ ত্রুটি ঘটেছে: {str(e)}")
                  
