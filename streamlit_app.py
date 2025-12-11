import streamlit as st
import toml
import json
from openai import OpenAI
from google.cloud import firestore
from datetime import datetime
import time
import pytz

# Show title and description.
st.set_page_config(page_title="UBC Flexi 🤖")

st.title("Hi, I'm FLEXI! 🤖")
st.write(
    "UBC's Faculty of Medicine's virtual advisor for FLEX!"
)

url = "https://ubc.ca1.qualtrics.com/jfe/form/SV_bC2vtmOwlIQ1e5g"
st.write(
    "If you found me helpful (or you found some bugs) let us know [here](%s)." % url)

# footer
footer_html = """<div style='text-align: center;'>
  <p>Developed by Charley Cai MSI4 with StreamLit 🩺</p>
</div>"""
st.markdown(footer_html, unsafe_allow_html=True)

# Secrets
openai_api_key = st.secrets["flexAIToken"]
db = firestore.Client.from_service_account_info(
    json.loads(st.secrets["firestore"], strict=False))

# Setup Assistant Version
ASSISTANTS = {
    "First year (MEDD 419)": st.secrets["assistantID419"],
    "Second year (MEDD 429)": st.secrets["assistantID429"],
}

# Load prompts
PROMPTS = {
    "First year (MEDD 419)": toml.load("./prompt.toml")["flexPrompt419"],
    "Second year (MEDD 429)": toml.load("./prompt.toml")["flexPrompt429"],
}


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


def reset_chat():
    # Create a session state variable to store the chat messages. This ensures that the
    # messages persist across reruns.
    # Also create a persistent thread
    st.session_state.sessionID = f"{datetime.timestamp(datetime.now()):.0f}"
    st.session_state.messages = []
    st.session_state.stream = None
    st.session_state.thread = client.beta.threads.create()


if not openai_api_key:
    st.info("Please add your OpenAI API key to continue.", icon="🗝️")
else:
    # Create an OpenAI client.
    client = OpenAI(api_key=openai_api_key)

    # Initialize session state for assistant selection
    if "assistant_name" not in st.session_state:
        st.session_state.assistant_name = None

    st.session_state.assistant_name = st.segmented_control(
        "Please select your year:",
        list(ASSISTANTS.keys()),
        selection_mode="single",
        width="stretch",
        on_change=reset_chat,  # callback to reset chat if changed
        key="assistant_choice"
    )

    if not st.session_state.assistant_name:
        st.stop()

    # select correct agent now user has picked and inject date
    st.session_state.assistant_id = ASSISTANTS[st.session_state.assistant_name]
    st.session_state.my_instructions = f'{PROMPTS[st.session_state.assistant_name]} \n Today is {datetime.now(tz=pytz.timezone("US/Pacific")).strftime("%B %d %Y")}'

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
            thread_id=st.session_state.thread.id,
            role="user",
            content=prompt
        )

        # Run the Thread
        st.session_state.stream = client.beta.threads.runs.create(
            assistant_id=st.session_state.assistant_id,
            thread_id=st.session_state.thread.id,
            instructions=st.session_state.my_instructions,
            stream=True
        )

        # Stream the response to the chat using `st.write_stream`, then store it in
        # session state.
        with st.chat_message("assistant"):
            response = st.write_stream(data_streamer)
            st.session_state.messages.append(
                {"role": "assistant", "content": response})

            # add thread logging
            db.collection("sessions").document(st.session_state.sessionID).set({
                "created": time.strftime("%c", time.localtime(int(st.session_state.sessionID))),
                "version": st.session_state.assistant_name,
                "thread": st.session_state.messages
            })
