import streamlit as st
import toml
from openai import OpenAI
import time

# Show title and description.
st.title("UBC AI FLEX Advisor")
st.write(
    "This is UBC's Faculty of Medicine's virtual advisor for FLEX 419!"
)

# Secrets
openai_api_key = st.secrets["flexAIToken"]
assistantID = st.secrets["assistantID"]

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
            time.sleep(0.2)

if not openai_api_key:
    st.info("Please add your OpenAI API key to continue.", icon="🗝️")
else:

    # Create an OpenAI client.
    client = OpenAI(api_key=openai_api_key)

    # Create a session state variable to store the chat messages. This ensures that the
    # messages persist across reruns.
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if 'stream' not in st.session_state:
        st.session_state.stream = None

    # Display the existing chat messages via `st.chat_message`.
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Create a OpenAI Thread
    thread = client.beta.threads.create()

    # Create a chat input field to allow the user to enter a message. This will display
    # automatically at the bottom of the page.
    if prompt := st.chat_input("Type your question here!"):

        # Store and display the current prompt.
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Add message to thread
        message = client.beta.threads.messages.create(
            thread_id = thread.id,
            role = "user",
            content = prompt
        )          

        # Run the Thread
        st.session_state.stream = client.beta.threads.runs.create(
            assistant_id=assistantID,        
            thread_id= thread.id,
            stream=True
        )

        # Stream the response to the chat using `st.write_stream`, then store it in 
        # session state.
        with st.chat_message("assistant"):
            response = st.write_stream(data_streamer)
            st.session_state.messages.append({"role": "assistant", "content": response})

# footer
footer_html = """<div style='text-align: center;'>
  <p>Developed by Charley Cai MSI3 with StreamLit 🩺</p>
</div>"""
st.markdown(footer_html, unsafe_allow_html=True)