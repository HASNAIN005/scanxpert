from flask import Flask, request, jsonify
import re
import spacy
import os
import logging

app = Flask(__name__)

# Load SpaCy large model
nlp = spacy.load("en_core_web_lg")

def preprocess_text(text):
    """Normalize and clean input text."""
    text = re.sub(r'\s+', ' ', text)  # Collapse multiple spaces/newlines
    text = text.replace("O00)", "Pakistan").replace("zl", "21").replace("be", "Blue")
    return text

def extract_email(text):
    """Extract email addresses from text."""
    return re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)

def extract_phone_numbers(text):
    """Extract phone numbers and classify them into Tel, Cell, and Fax."""
    patterns = {
        "Fax": r"(?:Fax:)?\s?(?:051|(?:\+92-51))-\d{7}",
        "Tel": r"(?:Tel:)?\s?(?:\+92|0)?-?\d{2,3}-?\d{7,8}",
        "Cell": r"(?:Cell:)?\s?(?:\+92|0)?-?\d{3}-?\d{7}"
    }

    results = {key: re.findall(pattern, text) for key, pattern in patterns.items()}

    clean_results = {
        key: [re.sub(r"^(Tel:|Cell:|Fax:)?\s?", "", phone).strip() for phone in phones]
        for key, phones in results.items()
    }

    return clean_results

def extract_address(text):
    """Extract probable address strings from text."""
    normalized_text = re.sub(r'\s+', ' ', text)

    address_match = re.search(
        r'\b\d{1,3}[A-Za-z\s,#&.\-]*\b(?:Road|Street|Area|Mention|Block|Town|Phase|Sector|Building|Avenue)[,.\s]*[A-Za-z\s]*(?:Pakistan)?\b',
        normalized_text
    )
    return address_match.group().strip() if address_match else "nil"

def extract_website(text):
    """Extract website URLs from text."""
    return re.findall(r'www\.\S+\.com', text)

def extract_designation(text):
    """Extract designations such as job titles."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for line in lines:
        designation_match = re.search(
            r'\b(?:Chief Executive|Senior|Junior|Lead|Chief|Head|Principal|Assistant|Associate|Director|Manager|Engineer|Officer|Analyst|Scientist|Specialist|Consultant|Administrator|Developer|Executive|Coordinator)\b(?:\s?\([^)]*\))?',
            line
        )
        if designation_match:
            return designation_match.group().strip()

    return "nil"

def extract_name(entities):
    """Extract name using SpaCy entities, preferring longer PERSON entities."""
    names = [value for key, value in entities.items() if key == "PERSON"]
    return max(names, key=len, default="nil")

def extract_company(entities):
    """Use SpaCy entities for accurate company name extraction."""
    return entities.get("ORG", "nil")

@app.route('/extract', methods=['POST'])
def extract_info():
    """Extract information from raw text."""
    data = request.json
    text = data.get('text', '')

    app.logger.info(f"Received Input: {text}")

    # Process text with SpaCy large model
    doc = nlp(text)
    entities = {ent.label_: ent.text for ent in doc.ents}

    # Extract specific fields
    emails = extract_email(text)
    phones = extract_phone_numbers(text)
    websites = extract_website(text)
    designation = extract_designation(text)
    company = extract_company(entities)

    # Extract name
    name = extract_name(entities)

    # Extract address
    address = extract_address(text)

    # Prepare structured output
    structured_output = {
        "Name": name,
        "Address": address,
        "company_name": company,
        "Designation": designation,
        "Email": ", ".join(emails) if emails else "nil",
        "Cell": ", ".join(phones["Cell"]) if phones["Cell"] else "nil",
        "Tel": ", ".join(phones["Tel"]) if phones["Tel"] else "nil",
        "Fax": ", ".join(phones["Fax"]) if phones["Fax"] else "nil",
        "Website": ", ".join(websites) if websites else "nil"
    }

    app.logger.info(f"Response Sent: {structured_output}")
    return jsonify(structured_output)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    app.run(debug=os.getenv('FLASK_DEBUG', 'False') == 'True', host='0.0.0.0', port=int(os.getenv('PORT', 8080)))