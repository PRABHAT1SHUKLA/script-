import PyPDF2
import anthropic
import os

def extract_text_from_pdf(pdf_path):
    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text

def summarize_with_ai(text, api_key):
    client = anthropic.Anthropic(api_key=api_key)
    
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": f"Please provide a comprehensive summary of the following document:\n\n{text}"
            }
        ]
    )
    
    return message.content[0].text

def main():
    pdf_path = "document.pdf"
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    
    print("Extracting text from PDF...")
    extracted_text = extract_text_from_pdf(pdf_path)
    
    print("Sending to AI for summarization...")
    summary = summarize_with_ai(extracted_text, api_key)
    
    print("\n=== SUMMARY ===")
    print(summary)

if __name__ == "__main__":
    main()
