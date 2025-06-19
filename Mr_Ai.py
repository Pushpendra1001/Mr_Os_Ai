import os
import shutil
import streamlit as st
import subprocess
import requests
import speech_recognition as sr
from streamlit_webrtc import webrtc_streamer, AudioProcessorBase
import av
import asyncio
import threading
import time


def generate_command(prompt):
    api_key = "genKey"
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
        self.buffer = []
        self.last_process_time = 0
        
    def recv(self, frame: av.AudioFrame):
        import time
        current_time = time.time()
        
        # Add frame data to buffer
        audio_data = frame.to_ndarray().flatten().astype('int16')
        self.buffer.extend(audio_data)
        
        # Process only every 1 second to avoid overloading
        if current_time - self.last_process_time > 1.0 and len(self.buffer) > 16000:
            self.last_process_time = current_time
            
            # Create AudioData from buffer
            audio_bytes = bytes(bytearray(self.buffer))
            self.buffer = []  # Clear buffer after processing
            
            with sr.AudioData(audio_bytes, 16000, 2) as source:
                try:
                    text = self.recognizer.recognize_google(source)
                    st.session_state["speech_prompt"] = text
                except Exception as e:
                    # Only log errors, don't update the prompt
                    print(f"Recognition error: {str(e)}")
        
        return frame


st.set_page_config(page_title="Shakti - Windows Assistant", layout="wide")
st.title("💻 Shakti: Windows File Manager + GenAI Shell")
st.write("Use natural language or voice to generate Windows commands, or manage your files easily.")

if "speech_prompt" not in st.session_state:
    st.session_state["speech_prompt"] = ""

tab1, tab2 = st.tabs(["🧠 GenAI Shell", "📁 File Manager"])


# Replace the voice input section in tab1 with this automated version
with tab1:
    st.subheader("🎙️ Continuous Voice Command System")
    
    # Placeholders for displaying results
    status_placeholder = st.empty()
    command_placeholder = st.empty()
    output_placeholder = st.empty()
    
    # Session state for controlling listening
    if "listening" not in st.session_state:
        st.session_state.listening = False
        
    def toggle_listening():
        st.session_state.listening = not st.session_state.listening
    
    # Button to start/stop continuous listening
    if st.session_state.listening:
        if st.button("Stop Listening", on_click=toggle_listening):
            pass
        status_placeholder.info("Listening for commands... (speak and wait)")
    else:
        if st.button("Start Continuous Listening", on_click=toggle_listening):
            pass
        status_placeholder.info("Click the button above to start listening")
    
    # This will re-run the script periodically when listening is active
    if st.session_state.listening:
        # Process voice input
        try:
            recognizer = sr.Recognizer()
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source)
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
                
            # Recognize speech
            voice_text = recognizer.recognize_google(audio)
            if voice_text:
                status_placeholder.success(f"Detected: '{voice_text}'")
                
                # Generate and execute command
                command = generate_command(voice_text)
                command_placeholder.code(f"Executing command:\n{command}", language="bash")
                
                # Execute the command
                result = subprocess.getoutput(command)
                output_placeholder.text_area("Command Output:", result, height=200)
                
                # Brief pause to show results
                time.sleep(2)
                
        except (sr.UnknownValueError, sr.WaitTimeoutError):
            # Don't display anything for normal timeout/silence
            pass
        except Exception as e:
            status_placeholder.error(f"Error: {str(e)}")
            time.sleep(2)
        
        # Force a rerun to create a continuous listening loop
        time.sleep(0.1)  # Short delay
        st.rerun()
    
    # Still keep the text input for manual editing if needed
    prompt = st.text_input("Manual command input:", st.session_state.get("speech_prompt", ""))
    
    if st.button("Generate & Run Manual Command"):
        if prompt:
            with st.spinner("Processing..."):
                command = generate_command(prompt)
                result = subprocess.getoutput(command)
                command_placeholder.code(f"Executed Command:\n{command}", language="bash")
                output_placeholder.text_area("Command Output:", result, height=200)


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


