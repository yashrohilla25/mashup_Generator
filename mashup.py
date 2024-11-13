import streamlit as st
from googleapiclient.discovery import build
import yt_dlp
import os
import shutil
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pydub import AudioSegment


def get_youtube_links(api_key, query, max_results=2):
    youtube = build('youtube', 'v3', developerKey=api_key)
    search_response = youtube.search().list(
        q=query,
        part='snippet',
        type='video',
        maxResults=max_results
    ).execute()

    video_links = []
    for item in search_response['items']:
        video_id = item['id']['videoId']
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        video_links.append(video_url)

    return video_links


def download_audio(video_urls, download_path):
    if not os.path.exists(download_path):
        os.makedirs(download_path)

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{download_path}/%(title)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192'
        }],
    }

    downloaded_files = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for url in video_urls:
            info_dict = ydl.extract_info(url, download=False)
            ydl.download([url])
            filename = ydl.prepare_filename(info_dict).rsplit('.', 1)[0] + '.mp3'
            downloaded_files.append(filename)

    return downloaded_files


def create_mashup(audio_files, duration_ms, output_file):
    mashup = AudioSegment.silent(duration=0)

    for file in audio_files:
        audio = AudioSegment.from_file(file)
        part = audio[:duration_ms]
        mashup += part

    mashup.export(output_file, format="mp3")
    return output_file


def send_email_with_attachment(sender_email, sender_password, recipient_email, subject, body, file_path):
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    if os.path.exists(file_path):
        attachment = open(file_path, "rb")
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename= {os.path.basename(file_path)}")
        msg.attach(part)
        attachment.close()

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.quit()
        st.success("Email sent successfully!")
    except Exception as e:
        st.error(f"Error: {e}")


st.title("Mashup Generator")
st.write("Enter the details to generate a mashup and get it delivered to your email!")


email = st.text_input("Enter your email")
singer_name = st.text_input("Enter the singer's name")
duration = st.number_input("Enter the mashup duration (in seconds)", min_value=10, max_value=300, step=1)
api_key = "AIzaSyCVGOVkLO4Q4rqPl4Gf5Yu_16wnw_CJpsA"  

if st.button("Generate Mashup"):
    if email and singer_name and duration:
        st.info("Fetching songs...")

        query = singer_name
        result = get_youtube_links(api_key, query, max_results=5)

        if result:
            st.success(f"Found {len(result)} videos. Downloading...")
            downloaded_files = download_audio(result, "./downloads")

            if downloaded_files:
                st.info("Creating mashup...")
                output_file = create_mashup(downloaded_files, duration * 1000, "mashup.mp3")

                if output_file:
                    st.success(f"Mashup created successfully! Sending it to {email}")
                    send_email_with_attachment(
                        sender_email="your_email@gmail.com",  # Replace with your email
                        sender_password="your_password",  # Replace with your email password
                        recipient_email=email,
                        subject="Your Requested Mashup",
                        body=f"Hello, \n\nPlease find the requested mashup attached.",
                        file_path=output_file
                    )
            else:
                st.error("Failed to download audio files.")
        else:
            st.error("No videos found.")
    else:
        st.error("Please fill in all the fields.")
