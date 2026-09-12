import os
import sys
import time
import argparse
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from openai import OpenAI

def extract_text_from_file(filepath):
    """Extracts text from a PDF, DOCX, or TXT file."""
    if not os.path.exists(filepath):
        print(f"Error: Could not find CV file at '{filepath}'")
        sys.exit(1)
        
    ext = filepath.lower().split('.')[-1]
    text = ""
    try:
        if ext == 'pdf':
            import PyPDF2
            with open(filepath, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
        elif ext == 'docx':
            import docx
            doc = docx.Document(filepath)
            for para in doc.paragraphs:
                text += para.text + "\n"
        elif ext == 'txt':
            with open(filepath, 'r', encoding='utf-8') as f:
                text = f.read()
        else:
            print("Unsupported file format. Please use PDF, DOCX, or TXT.")
            sys.exit(1)
    except Exception as e:
        print(f"Error reading CV: {e}")
        sys.exit(1)
    return text

def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description='Auto Apply Copilot')
    parser.add_argument('--cv', type=str, required=True, help="Path to your CV (PDF, DOCX, TXT)")
    args = parser.parse_args()

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("\n========================================================")
        print(" ERROR: OPENROUTER_API_KEY environment variable not set in .env!")
        print(" Please add OPENROUTER_API_KEY=your_key_here to your .env file")
        print("========================================================\n")
        sys.exit(1)

    print("[*] Initializing OpenRouter AI...")
    client = OpenAI(
      base_url="https://openrouter.ai/api/v1",
      api_key=api_key,
    )
    
    print(f"[*] Reading CV from {args.cv}...")
    cv_text = extract_text_from_file(args.cv)
    print(f"[*] CV loaded successfully ({len(cv_text)} characters).")

    print("[*] Launching Browser...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()
        
        
        print("\n=====================================================================")
        target_url = input("Enter the website URL you want to apply on\n(e.g., https://www.jobs.nhs.uk/ or press Enter for Google): ").strip().strip("'\"")
        if not target_url:
            target_url = "https://www.google.co.uk/"
        elif not target_url.startswith("http"):
            target_url = "https://" + target_url
        
        page.goto(target_url)

        
        job_description = ""
        
        print("\n=====================================================================")
        print(" UK PUBLIC SECTOR APPLICATION COPILOT")
        print("=====================================================================")
        print(" 1. Please log in to your account in the browser.")
        print(" 2. Navigate to the Job Advert you want to apply for.")
        
        while True:
            print("\n---------------------------------------------------------")
            print(" COMMAND MENU:")
            print(" [1] Extract Job Description (Do this FIRST on the job advert page)")
            print(" [2] Auto-Fill Application Form (Do this on pages with text boxes)")
            print(" [3] Apply for a new role (Load new CV/URL, stay logged in)")
            print(" [4] Exit")
            print("---------------------------------------------------------")
            choice = input("Enter choice (1-4): ").strip().strip("'\"")
            
            if choice == "1":
                print("\n[*] Extracting Job Description from current page...")
                try:
                    # Civil service jobs usually has job description in main content
                    content = page.locator("body").inner_text()
                    prompt = (
                        "Extract the key details from this job advert, including the "
                        "Role Title, Responsibilities, Essential Criteria, and Behaviours required. "
                        "Return a clean summary.\n\n" + content[:15000]
                    )
                    print("[*] Analysing with AI...")
                    response = client.chat.completions.create(
                        model='openai/gpt-4o-mini',
                        messages=[{"role": "user", "content": prompt}]
                    )
                    job_description = response.choices[0].message.content
                    print("\n=== JOB DESCRIPTION EXTRACTED SUCCESSFULLY ===")
                    print(job_description[:500] + "...\n(truncated for display)")
                    print("==============================================\n")
                    print("You can now click 'Apply' in the browser and navigate to the form questions.")
                except Exception as e:
                    print(f"Error extracting JD: {e}")
                    
            elif choice == "2":
                if not job_description:
                    print("WARNING: You haven't extracted a Job Description yet! The AI might not write good answers.")
                    ans = input("Continue anyway? (y/n): ")
                    if ans.lower() != 'y':
                        continue
                
                print("\n[*] Scanning current page for questions and text boxes...")
                try:
                    # Find all text areas, rich text boxes, and standard text inputs
                    textareas = page.locator("textarea, div[contenteditable='true'], input[type='text']").all()
                    
                    # Filter for visible elements only
                    visible_textareas = []
                    for ta in textareas:
                        try:
                            if ta.is_visible():
                                visible_textareas.append(ta)
                        except:
                            pass
                    textareas = visible_textareas
                    
                    if not textareas:
                        print("No text boxes found on this page. Make sure you are on a form page.")
                        continue
                        
                    print(f"Found {len(textareas)} text boxes.")
                    for i, ta in enumerate(textareas):
                        # Try to find the associated label or heading preceding it
                        id_attr = ta.get_attribute("id")
                        question_text = "Unknown Question"
                        
                        if id_attr:
                            label = page.locator(f"label[for='{id_attr}']")
                            if label.count() > 0:
                                question_text = label.first.inner_text()
                            else:
                                # Fallback: look at parent or preceding elements
                                parent_text = ta.locator("xpath=..").inner_text()
                                question_text = parent_text.split('\n')[0] if parent_text else f"Text box {i+1}"
                        
                        print(f"\n--- Question {i+1} ---")
                        print(f"Prompt found: {question_text}")
                        
                        do_generate = input("Generate an AI answer for this box? (y=yes, n=skip): ")
                        if do_generate.lower() != 'y':
                            print("Skipping...")
                            continue
                            
                        print("Generating bespoke answer using your CV...")
                        
                        question_context = ta.evaluate('''(el) => {
                            let p = el.parentElement;
                            let text = "";
                            while(p && text.length < 400 && p.tagName !== 'BODY') {
                                text = p.innerText;
                                p = p.parentElement;
                            }
                            return text.substring(0, 800);
                        }''')
                        
                        ai_prompt = f"""You are an expert UK career coach securely auto-filling an applicant's job application form.
CRITICAL RULES for ALL answers:
1. TONE: You MUST write in plain, natural, professional UK English. Your text MUST NOT be detectable as AI.
2. BANNED JARGON: Do NOT use ChatGPT-isms. NEVER use words like "spearhead", "delve", "foster", "testament", "furthermore", "moreover", "in conclusion", "navigated", "seamless", "elevate", "synergy". Write like a normal human professional.
3. TRUTH: DO NOT invent experience, dates, or skills. Use ONLY the facts from the candidate's CV.
4. FORMAT: Output ONLY the exact raw text to be pasted into the text box. No pleasantries, no markdown (no **bold**), no intro/outro.

JOB DESCRIPTION CONTEXT (The role they are applying for):
{job_description}

CANDIDATE CV:
{cv_text}

TARGET TEXT BOX LABEL: {question_text}
SURROUNDING FORM CONTEXT (Text near the box on the website):
{question_context}

INSTRUCTIONS FOR THIS SPECIFIC BOX:
Analyze the TARGET TEXT BOX LABEL and the SURROUNDING FORM CONTEXT to figure out exactly what this box is asking for, then follow the matching rule below:

- RULE A (Short Form Fields): If the box asks for "Reason for Leaving", "Job Title", "Employer", "Salary", "Notice Period", or similar short facts, extract the exact short answer from the CV and output ONLY those 1-5 words. DO NOT write a sentence. (e.g. "Seeking career progression", "Stagecoach", "2 weeks"). 
- RULE B (Role Description / Duties): If the box is part of a "Work Experience" entry (asking for Duties/Description) and the context shows a specific Job Title/Company, write a factual, human-sounding 50-100 word paragraph describing what the candidate did in THAT SPECIFIC JOB from the CV. Do NOT write a cover letter here.
- RULE C (Personal Statement / Supporting Info): If the box asks "Why are you suitable?", "Skills and Experience", or "Personal Statement", write a highly compelling, natural 300-400 word statement. Weave the candidate's CV experience together to prove they meet the Job Description requirements. Use simple, confident language.
- RULE D (Behaviour/Competency): If the box asks for a specific behaviour (e.g. "Working together"), write a 200-word STAR example from the CV. Keep it grounded and realistic.

Execute the correct rule now:
"""
                        
                        response = client.chat.completions.create(
                            model='openai/gpt-4o-mini',
                            messages=[{"role": "user", "content": ai_prompt}]
                        )
                        answer = response.choices[0].message.content.strip().strip("'\"")
                        print("\nGenerated Answer Preview:")
                        print("-" * 40)
                        print(answer[:300] + "...")
                        print("-" * 40)
                        
                        do_fill = input("Do you want to automatically type this into the browser? (y/n): ")
                        if do_fill.lower() == 'y':
                            tag_name = ta.evaluate("el => el.tagName").lower()
                            if tag_name == 'div':
                                ta.evaluate(f"el => el.innerText = `{answer.replace('`', '')}`")
                            else:
                                ta.fill(answer)
                            print("[*] Successfully filled text box.")
                        else:
                            print("[*] Skipped filling.")
                            
                except Exception as e:
                    print(f"Error filling form: {e}")
                    
            elif choice == "3":
                print("\n[*] Preparing for a new application...")
                new_cv = input("Enter path for new CV (or press Enter to keep using the current one): ").strip().strip('"\'')
                if new_cv:
                    if os.path.exists(new_cv):
                        cv_text = extract_text_from_file(new_cv)
                        print(f"[*] New CV loaded successfully ({len(cv_text)} characters).")
                    else:
                        print("File not found! Keeping old CV.")
                
                new_url = input("Enter the new job advert URL: ").strip().strip('"\'')
                if new_url:
                    if not new_url.startswith("http"):
                        new_url = "https://" + new_url
                    print(f"[*] Navigating to {new_url}...")
                    page.goto(new_url)
                
                # Reset job description for the new role
                job_description = ""
                print("[*] Ready for new role! Please navigate to the advert and press [1] to extract.")
                
            elif choice == "4":
                print("Exiting Copilot...")
                break
            else:
                print("Invalid choice.")
                
        browser.close()

if __name__ == "__main__":
    main()
