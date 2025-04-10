import streamlit as st
import PyPDF2
import google.generativeai as genai
import re
import os

# Configure the API Key for Gemini (Google's API)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
    api_configured = True
else:
    api_configured = False
    st.error("Gemini API key not found in environment variables. Please set the 'GEMINI_API_KEY' environment variable on your deployment platform.")


# Configure Gemini model
model = genai.GenerativeModel("gemini-1.5-flash")

# Function to extract text from PDF
def extract_text_from_pdf(pdf_file):
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        total_pages = len(pdf_reader.pages)
        
        # Create progress bar
        progress_bar = st.progress(0)
        
        for page_num in range(total_pages):
            text += pdf_reader.pages[page_num].extract_text() or ""  # Handle None return
            progress_bar.progress((page_num + 1) / total_pages)  # Update progress
        return text
    except Exception as e:
        st.error(f"Error extracting text from PDF: {e}")
        return ""

# Function to clean text by removing problematic characters
def clean_text(text):
    return re.sub(r'[\ud800-\udfff]', '', text)

# Function to summarize text using Gemini API
def summarize_text(text):
    cleaned_text = clean_text(text)
    summary_prompt = (
        f"Summarize the following lecture in the given format without labeling each section:\n"
        f"- Start with an introductory sentence mentioning the author and the lecture's title.\n"
        f"- Follow with a brief description of the main points covered in the lecture.\n"
        f"- Then, list the supporting arguments that explain or support the author's main ideas.\n"
        f"- Conclude with a final thought or takeaway from the lecture.\n"
        f"- Lastly, include a list of key points, where each key point defines or explains an important word or concept from the lecture.\n\n"
        f"Lecture: {cleaned_text}"
    )
    try:
        summary_response = model.generate_content(summary_prompt)
        return summary_response.text
    except Exception as e:
        st.error(f"Error summarizing text: {e}")
        return ""

# Function to generate MCQs based on the summary
def generate_mcq(summary):
    mcq_prompt = (
        f"Create 10 multiple-choice questions based on the following lecture summary. "
        f"Each question should have four answer options labeled A, B, C, D, with the correct answer listed at the end.\n"
        f"Format each question as follows:\n"
        f"1. **Question**: [question text]\n"
        f"   A) [Option A]\n"
        f"   B) [Option B]\n"
        f"   C) [Option C]\n"
        f"   D) [Option D]\n"
        f"   Correct Answer: [The correct answer]\n\n"
        f"Lecture Summary:\n{summary}\n\n"
        f"Here are the questions and answers:\n"
    )
    try:
        mcq_response = model.generate_content(mcq_prompt)

        # Parse and format the MCQs
        mcq_list = mcq_response.text.split('\n')
        questions = []
        current_question = None
        current_options = []
        correct_answer = None

        for line in mcq_list:
            line = line.strip()
            if line.startswith(("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.", "10.")):
                if current_question:  # Save the previous question
                    if correct_answer:  # Only append if a correct answer exists
                        questions.append((current_question, current_options, correct_answer))
                current_question = line
                current_options = []
                correct_answer = None
            elif line.startswith(("A)", "B)", "C)", "D)")):
                current_options.append(line)
            elif line.startswith("Correct Answer:"):
                correct_answer = line.replace("Correct Answer: ", "")

        # Append the last question
        if current_question and correct_answer:
            questions.append((current_question, current_options, correct_answer))

        return questions
    except Exception as e:
        st.error(f"Error generating MCQs: {e}")
        return []


# Function to handle chatbot queries based on the summary
def answer_question(text, question):
    cleaned_text = clean_text(text)
    chatbot_prompt = f"Based on the following lecture, answer the question:\n\n Lecture: {cleaned_text}\n\nQuestion: {question}\n\nAnswer:"
    try:
        chatbot_response = model.generate_content(chatbot_prompt)
        return chatbot_response.text
    except Exception as e:
        st.error(f"Error answering question: {e}")
        return ""

# Streamlit UI
st.title("Edura - A Study Assistant")

# File upload for PDF
pdf_file = st.file_uploader("Choose a PDF file", type=["pdf"])

# Initialize the segmented control once the PDF is uploaded
if pdf_file is not None:
    # Extract the text from the uploaded PDF
    with st.spinner('Extracting text from the PDF...'):
        extracted_text = extract_text_from_pdf(pdf_file)

    if extracted_text:
        # Clean the extracted text for chatbot queries
        cleaned_text = clean_text(extracted_text)
        
        # Segmented control for selecting the action after the PDF is uploaded
        option_map = {
            0: "Summary",
            1: "Generate MCQs",
            2: "Chatbot"
        }

        selection = st.segmented_control(
            "What would you like to do?",
            options=option_map.keys(),
            format_func=lambda option: option_map[option],
            selection_mode="single",
        )

        # Perform the task based on the user's selection
        if selection == 0:  # Show summary
            with st.spinner('Generating summary...'):
                summary = summarize_text(extracted_text)
            st.subheader("Lecture Summary")
            st.write(summary)
        
        elif selection == 1:  # Generate MCQs
            with st.spinner('Generating MCQs...'):
                questions = generate_mcq(extracted_text)
            st.subheader("Knowledge Check (MCQs)")
            
            for i, (question, options, correct_answer) in enumerate(questions):
                st.write(f"**{question}**")
                for option in options:
                    st.write(option)
                st.write(f"**Correct Answer**: {correct_answer}")
        
        elif selection == 2:  # Chatbot
            question = st.text_input("Ask a question based on the lecture:")
            if question:
                with st.spinner('Generating answer...'):
                    answer = answer_question(cleaned_text, question)  # Use cleaned_text here for chatbot
                st.subheader("Chatbot Answer")
                st.write(answer)
