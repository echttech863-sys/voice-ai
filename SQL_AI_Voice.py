import streamlit as st
import pandas as pd
import openai
import mysql.connector
import speech_recognition as sr
import threading
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

# Database and API credentials
host_name = os.getenv("HOST_NAME")
port_name = int(os.getenv("PORT_NAME", 33094))
user_name = os.getenv("USER_NAME")
password = os.getenv("PASSWORD")
api_key = os.getenv("OPENAI_API_KEY")

# ✅ Initialize OpenAI client
openai.api_key = api_key

# ✅ Connect to MySQL
conn = mysql.connector.connect(
    host=host_name,
    port=port_name,
    user=user_name,
    password=password
)
cursor = conn.cursor()

# 🔁 Try to initialize text-to-speech if running locally
# try:
#     import pyttsx3
#     engine = pyttsx3.init()
#     TTS_ENABLED = True
# except Exception as e:
#     TTS_ENABLED = False
#     st.warning("🔇 Text-to-speech not supported in this environment.")


# def speak(text):
#     if not TTS_ENABLED:
#         return
#     def run():
#         engine.say(text)
#         engine.runAndWait()
#     t = threading.Thread(target=run)
#     t.start()


# def recognize_speech():
#     recognizer = sr.Recognizer()
#     with sr.Microphone() as source:
#         st.write("🎙️ Listening... Please speak!")
#         recognizer.adjust_for_ambient_noise(source)
#         audio = recognizer.listen(source)
#         try:
#             speech_text = recognizer.recognize_google(audio)
#             return speech_text
#         except sr.UnknownValueError:
#             st.error("Sorry, I couldn't understand the audio.")
#             return ""
#         except sr.RequestError:
#             st.error("There was an issue with the speech recognition service.")
#             return ""


def get_all_schema(cursor):
    cursor.execute("SHOW DATABASES;")
    return [row[0] for row in cursor.fetchall()]


def get_schema(cursor, db_name):
    query = f"""
    SELECT table_name, column_name
    FROM information_schema.columns
    WHERE table_schema = '{db_name}'
    ORDER BY table_name, Ordinal_position;
    """
    cursor.execute(query)
    rows = cursor.fetchall()

    if not rows:
        return None

    schema_dict = {}
    for table, column in rows:
        schema_dict.setdefault(table, []).append(column)

    schema_text = ""
    for table, columns in schema_dict.items():
        schema_text += f"Table '{table}':\n"
        for col in columns:
            schema_text += f"  - {col}\n"
        schema_text += "\n"
    return schema_text.strip()


def get_sql_from_prompt(prompt, schema_text):
    messages = [
        {"role": "system", "content": "Generate only SQL query."},
        {"role": "system", "content": f"Database Schema:\n\n{schema_text}"},
        {"role": "user", "content": prompt}
    ]
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=messages
    )
    sql_query = response.choices[0].message["content"].strip()
    return sql_query


def run_sql_query(sql_query, conn, cursor):
    try:
        cursor.execute(sql_query)
        results = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        return results, columns
    except Exception as e:
        return f"Error Executing Query: {e}", []


# -------------------- UI ------------------------

st.title("🧠 Natural Language SQL Assistant")

if st.button("📚 SHOW Available Schemas"):
    schemas = get_all_schema(cursor)
    st.session_state.schema = schemas
    for i, schema in enumerate(schemas, 1):
        st.write(f"{i}. {schema}")

schemas = st.session_state.get("schema", [])
db_name = st.text_input("Enter Database Name:")

if db_name:
    if db_name not in schemas:
        st.error(f"Schema '{db_name}' not found.")
    else:
        try:
            conn.database = db_name
        except Exception as e:
            st.error(f"Error Selecting Database: {e}")

        schema_text = get_schema(cursor, db_name)

        if not schema_text:
            st.warning(f"No tables found in selected schema.")
        else:
            st.success(f"✅ Connected to: {db_name}")
            with st.expander("📂 View Schema Structure"):
                st.text(schema_text)

            prompt = st.text_area("🧾 Enter the SQL Query in natural language:")

            # if st.button("🎤 Speak SQL Query"):
            #     speech_text = recognize_speech()
            #     if speech_text:
            #         st.text_area("Recognized Query", value=speech_text)
            #         prompt = speech_text

            if prompt:
                with st.spinner("🤖 Generating SQL Query..."):
                    sql = get_sql_from_prompt(prompt, schema_text)
                st.code(sql, language="sql")

                with st.spinner("🚀 Running SQL Query..."):
                    result, columns = run_sql_query(sql, conn, cursor)

                i
