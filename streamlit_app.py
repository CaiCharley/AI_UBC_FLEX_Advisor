import streamlit as st
import toml
from openai import OpenAI

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

if not openai_api_key:
    st.info("Please add your OpenAI API key to continue.", icon="🗝️")
else:

    # Create an OpenAI client.
    client = OpenAI(api_key=openai_api_key)

    # Create a session state variable to store the chat messages. This ensures that the
    # messages persist across reruns.
    if "messages" not in st.session_state:
        st.session_state.messages = []

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
        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread.id,
            assistant_id = assistantID,
            instructions = instructions
        )

        if run.status == 'completed': 
            messageResponse = client.beta.threads.messages.list(
            thread_id=thread.id
        )
            textResponse = messageResponse.data[0].content[0].text.value
        else:
            st.write(run.status)


        # TODO: Implement streaming
        
        # Stream the response to the chat using `st.write_stream`, then store it in 
        # session state.
        with st.chat_message("assistant"):
            # response = st.write_stream(stream)
            st.markdown(textResponse)
        st.session_state.messages.append({"role": "assistant", "content": textResponse})

# footer
footer_html = """<div style='text-align: center;'>
  <p>Developed by Charley Cai MSI3 with StreamLit 🩺</p>
</div>"""
st.markdown(footer_html, unsafe_allow_html=True)