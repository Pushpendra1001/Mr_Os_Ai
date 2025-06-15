import os
import shutil
import streamlit as st
import subprocess
import requests
import speech_recognition as sr
from googletrans import Translator
from streamlit_webrtc import webrtc_streamer, AudioProcessorBase
import av


def generate_command(prompt):
    api_key = "gemi_key"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"

    headers = {"Content-Type": "application/json"}
    body = {
        "contents": [
            {
                "parts": [{"text": f"Convert the following prompt into a single Windows CMD command without quotes:\n{prompt}"}]
            }
        ]
    }

    response = requests.post(url, headers=headers, json=body)
    if response.status_code == 200:
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    else:
        return f"Error: {response.text}"


def list_files(directory):
    try:
        return os.listdir(directory)
    except FileNotFoundError:
        return []

def rename_file(directory, old_name, new_name):
    old_path = os.path.join(directory, old_name)
    new_path = os.path.join(directory, new_name)
    try:
        os.rename(old_path, new_path)
        return True
    except:
        return False

def delete_file(directory, name):
    file_path = os.path.join(directory, name)
    if os.path.exists(file_path):
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
            return True
        except PermissionError:
            return False
    return False

def create_dir(directory, dir_name):
    dir_path = os.path.join(directory, dir_name)
    try:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            return True
        return False
    except:
        return False

def view_file(directory, name):
    file_path = os.path.join(directory, name)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', encoding='latin-1') as file:
                    return file.read()
            except Exception as e:
                return f"Could not decode file: {str(e)}"
        except Exception as e:
            return f"Error reading file: {str(e)}"
    return "File not found."


class AudioProcessor(AudioProcessorBase):
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.translator = Translator()

    def recv(self, frame: av.AudioFrame):
        audio_data = frame.to_ndarray().flatten().astype('int16')
        with sr.AudioData(audio_data.tobytes(), 16000, 2) as source:
            try:
                text = self.recognizer.recognize_google(source)
                translated = self.translator.translate(text, dest="en").text
                st.session_state["speech_prompt"] = translated
            except Exception as e:
                st.session_state["speech_prompt"] = f"Error: {str(e)}"
        return frame


st.set_page_config(page_title="Shakti - Windows Assistant", layout="wide")
st.title("💻 Shakti: Windows File Manager + GenAI Shell")
st.write("Use natural language or voice to generate Windows commands, or manage your files easily.")

if "speech_prompt" not in st.session_state:
    st.session_state["speech_prompt"] = ""

tab1, tab2 = st.tabs(["🧠 GenAI Shell", "📁 File Manager"])


with tab1:
    st.subheader("🎙️ Speak or type your task (e.g., show files, check time)")
    webrtc_streamer(
        key="speech",
        audio_processor_factory=AudioProcessor,
        media_stream_constraints={"audio": True, "video": False},
        async_processing=True,
    )

    prompt = st.text_input("Detected Prompt (editable):", st.session_state["speech_prompt"])

    if st.button("Generate & Run Command"):
        if prompt:
            with st.spinner("Thinking..."):
                command = generate_command(prompt)
                result = subprocess.getoutput(command)
                st.code(f"Generated Command:\n{command}", language="bash")
                st.text_area("Command Output:", result, height=200)


with tab2:
    st.subheader("File Operations")
    directory = st.text_input("Enter directory path:", value=os.getcwd())

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**List of Files**")
        if st.button("List Files"):
            files = list_files(directory)
            st.write(files if files else "No files found or invalid directory.")

        st.markdown("**Delete a File or Directory**")
        del_file = st.text_input("File/Folder to delete:")
        if st.button("Delete File"):
            if delete_file(directory, del_file):
                st.success("File or directory deleted successfully.")
            else:
                st.error("File/folder not found or permission denied.")

        st.markdown("**Create a Directory**")
        new_dir = st.text_input("New directory name:")
        if st.button("Create Directory"):
            if create_dir(directory, new_dir):
                st.success("Directory created successfully.")
            else:
                st.warning("Directory already exists or error occurred.")

    with col2:
        st.markdown("**Rename a File/Directory**")
        old_name = st.text_input("Old name:")
        new_name = st.text_input("New name:")
        if st.button("Rename"):
            if rename_file(directory, old_name, new_name):
                st.success("Renamed successfully.")
            else:
                st.error("Rename failed. Check file names.")

        st.markdown("**View File Content**")
        view_name = st.text_input("File to view:")
        if st.button("View File"):
            content = view_file(directory, view_name)
            st.text_area("File Content:", content, height=200)
