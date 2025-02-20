import streamlit as st
import toml
import json
from openai import OpenAI
from google.cloud import firestore
import time

# Show title and description.
st.title("Hi, I'm FLEXI! 🤖")
st.write(
    "UBC's Faculty of Medicine's virtual advisor for FLEX 419!"
)

url = "https://ubc.ca1.qualtrics.com/jfe/form/SV_bC2vtmOwlIQ1e5g"
st.write("If you found me helpful (or you found some bugs) let use know [here](%s)." % url)

# footer
footer_html = """<div style='text-align: center;'>
  <p>Developed by Charley Cai MSI3 with StreamLit 🩺</p>
</div>"""
st.markdown(footer_html, unsafe_allow_html=True)

# Secrets
openai_api_key = st.secrets["flexAIToken"]
assistantID = st.secrets["assistantID"]
db = firestore.Client.from_service_account_info(json.loads(st.secrets["firestore"], strict=False))

# Load prompt
instructions = toml.load("./prompt.toml")["flexPrompt"]

# init streamer
def data_streamer():
    """
    That stream object in ss.stream needs to be examined in detail to come
    up with this solution. It is still in beta stage and may change in future releases.
    """
    for response in st.session_state.stream:
        if response.event == 'thread.message.delta':
            value = response.data.delta.content[0].text.value
            yield value
            time.sleep(0.1)

if not openai_api_key:
    st.info("Please add your OpenAI API key to continue.", icon="🗝️")
else:

    # Create an OpenAI client.
    client = OpenAI(api_key=openai_api_key)

    # Create a session state variable to store the chat messages. This ensures that the
    # messages persist across reruns.
    # Also create a persistent thread
    if "sessionID" not in st.session_state:
        st.session_state.sessionID = f"{time.time():.0f}"
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if 'stream' not in st.session_state:
        st.session_state.stream = None
    if "thread" not in st.session_state:
        st.session_state.thread = client.beta.threads.create()

    # Display the existing chat messages via `st.chat_message`.
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Create a chat input field to allow the user to enter a message. This will display
    # automatically at the bottom of the page.
    if prompt := st.chat_input("Type your question here!"):

        # Store and display the current prompt.
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Add message to thread
        message = client.beta.threads.messages.create(
            thread_id = st.session_state.thread.id,
            role = "user",
            content = prompt
        )          

        # Run the Thread
        st.session_state.stream = client.beta.threads.runs.create(
            assistant_id=assistantID,        
            thread_id= st.session_state.thread.id,
            stream=True
        )

        # Stream the response to the chat using `st.write_stream`, then store it in 
        # session state.
        with st.chat_message("assistant"):
            response = st.write_stream(data_streamer)
            st.session_state.messages.append({"role": "assistant", "content": response})

            # add thread logging
            db.collection("sessions").document(st.session_state.sessionID).set({
                "created": time.strftime("%c", time.localtime(int(st.session_state.sessionID))),
                "thread": st.session_state.messages
            })
