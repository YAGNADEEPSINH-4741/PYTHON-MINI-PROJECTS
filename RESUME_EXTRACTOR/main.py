import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext
import re
import os
import json
import csv
import pdfplumber
import docx
import spacy
from collections import Counter
from datetime import datetime

# ==========================================
# 1. ANALYTICS LOGIC (NLP & AI)
# ==========================================

class ResumeAnalyzer:
    def __init__(self):
        # Load NLP model
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            print("Spacy model not found. Please run: python -m spacy download en_core_web_sm")
            self.nlp = None

        # Regex patterns for core contact info
        self.email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        self.phone_pattern = r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        self.year_pattern = r'\b(19|20)\d{2}\b'
        
        # Section Keywords
        self.sections_keywords = {
            "education": ["education", "academic", "qualifications", "university", "college"],
            "skills": ["skills", "technologies", "technical skills", "competencies", "stack"],
            "experience": ["experience", "work history", "employment", "internships", "career", "professional experience"],
            "achievements": ["achievements", "certifications", "awards", "honors", "licenses"],
            "projects": ["projects", "portfolio"]
        }

        # Personality Keywords Map (Heuristic Base)
        self.personality_keywords = {
            "Leadership": ["led", "managed", "spearheaded", "oversaw", "directed", "supervised", "guided", "mentored", "chief", "head"],
            "Teamwork": ["collaborated", "team", "partnered", "assisted", "supported", "cooperated", "joint", "group", "member"],
            "Communication": ["presented", "negotiated", "authored", "wrote", "corresponded", "spoke", "briefed", "explained", "facilitated"],
            "Problem Solving": ["solved", "resolved", "debugged", "fixed", "troubleshot", "analyzed", "diagnosed", "improved", "optimized"],
            "Creativity": ["designed", "created", "innovated", "architected", "developed", "conceptualized", "drafted", "originated"],
            "Adaptability": ["adapted", "adjusted", "flexible", "versatile", "changed", "learned", "migrated", "transitioned"]
        }

    def extract_text(self, filepath):
        """Extracts raw text from PDF or DOCX files."""
        ext = os.path.splitext(filepath)[1].lower()
        text = ""
        try:
            if ext == '.pdf':
                with pdfplumber.open(filepath) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
            elif ext == '.docx' or ext == '.doc':
                doc = docx.Document(filepath)
                for para in doc.paragraphs:
                    text += para.text + "\n"
        except Exception as e:
            print(f"Error reading file: {e}")
            return None
        return text

    def clean_text(self, text):
        if not text: return ""
        return re.sub(r'\n+', '\n', text).strip()

    def calculate_experience_level(self, text, experience_section_text):
        """
        Estimates experience level based on years mentioned and job titles.
        Returns: (Level String, Explanation String)
        """
        # 1. Find all years in the text
        years = [int(y) for y in re.findall(self.year_pattern, experience_section_text)]
        years = sorted([y for y in years if 1980 <= y <= datetime.now().year])
        
        estimated_years = 0
        if years:
            estimated_years = years[-1] - years[0]

        # 2. Check for keywords if dates are ambiguous
        text_lower = text.lower()
        if "senior" in text_lower or "manager" in text_lower or "lead" in text_lower or "architect" in text_lower:
            title_bump = True
        else:
            title_bump = False

        # 3. Logic
        level = "Unknown"
        
        # Override for explicit fresher keywords
        if estimated_years <= 1 and any(k in text_lower for k in ["fresher", "graduate", "entry level"]):
             return "Fresher / Entry-Level", "0-1 Years (inferred)"

        if estimated_years == 0 and not title_bump:
            # Fallback if no dates found but looks like a resume
            return "Entry-Level (Uncertain)", "No dates found"
        
        if estimated_years < 3:
            level = "Junior"
        elif 3 <= estimated_years < 7:
            level = "Mid-Level"
        else:
            level = "Senior"

        # Boost level if high-level titles exist but years are border-line
        if title_bump and level == "Junior" and estimated_years > 1:
            level = "Junior-Mid"
        if title_bump and level == "Mid-Level":
            level = "Mid-Senior"

        return level, f"{estimated_years} Years detected ({min(years) if years else '?'} - {max(years) if years else '?'})"

    def analyze_personality(self, text):
        """
        Analyzes the text for soft skills and personality traits using keyword frequency.
        Returns: Dict {Trait: (Score_Label, Raw_Count)}
        """
        if not self.nlp:
            return {k: ("N/A", 0) for k in self.personality_keywords}

        doc = self.nlp(text.lower())
        tokens = [token.lemma_ for token in doc if not token.is_stop and not token.is_punct]
        
        counts = Counter(tokens)
        results = {}

        for trait, keywords in self.personality_keywords.items():
            score = 0
            for k in keywords:
                # Basic stemming matching
                score += counts[k]
                # Also check exact matches in raw text for non-lemmatized nuances
                score += text.lower().count(k) 
            
            # Normalize Score
            # Adjust these thresholds based on testing
            if score >= 10:
                rating = "High"
            elif score >= 4:
                rating = "Medium"
            elif score > 0:
                rating = "Low"
            else:
                rating = "Not Detected"
            
            results[trait] = (rating, score)
        
        return results

    def parse(self, filepath):
        raw_text = self.extract_text(filepath)
        if not raw_text:
            return {"Error": "Could not extract text."}

        clean_raw_text = self.clean_text(raw_text)
        lines = clean_raw_text.split('\n')
        
        data = {
            "Full Name": "Not Found",
            "Email": "Not Found",
            "Phone": "Not Found",
            "Skills": [],
            "Education": [],
            "Experience": [],
            "Achievements": [],
            "AI_Analysis": {}
        }

        # --- Basic Extraction ---
        email_match = re.search(self.email_pattern, clean_raw_text)
        if email_match: data["Email"] = email_match.group(0)

        phone_match = re.search(self.phone_pattern, clean_raw_text)
        if phone_match: data["Phone"] = phone_match.group(0)

        for line in lines[:5]:
            line_stripped = line.strip()
            if len(line_stripped) > 2 and "resume" not in line_stripped.lower() and "@" not in line_stripped:
                data["Full Name"] = line_stripped
                break

        # --- Section Segmentation ---
        current_section = None
        section_text = {k: [] for k in self.sections_keywords}
        full_experience_text = "" # For AI analysis

        for line in lines:
            clean_line = line.strip().lower()
            is_header = False
            for section, keywords in self.sections_keywords.items():
                if any(k in clean_line for k in keywords) and len(clean_line.split()) < 5:
                    current_section = section
                    is_header = True
                    break
            
            if is_header: continue

            if current_section in section_text:
                if line.strip():
                    section_text[current_section].append(line.strip())
                    if current_section == "experience":
                        full_experience_text += line + " "

        data["Education"] = section_text["education"]
        data["Skills"] = section_text["skills"]
        data["Experience"] = section_text["experience"]
        data["Achievements"] = section_text["achievements"]

        # --- AI / NLP Analysis ---
        exp_level, exp_details = self.calculate_experience_level(clean_raw_text, full_experience_text)
        personality_traits = self.analyze_personality(clean_raw_text)

        data["AI_Analysis"] = {
            "Experience_Level": exp_level,
            "Experience_Detail": exp_details,
            "Personality": personality_traits
        }

        return data

# ==========================================
# 2. GUI APPLICATION
# ==========================================

class ResumeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Resume Screener")
        self.root.geometry("600x400")
        self.root.configure(bg="#f0f2f5")
        
        self.analyzer = ResumeAnalyzer()
        self.extracted_data = {}
        self.setup_ui()

    def setup_ui(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TButton", padding=8, font=('Segoe UI', 10))
        style.configure("TLabel", background="#f0f2f5", font=('Segoe UI', 11))
        style.configure("Header.TLabel", font=('Segoe UI', 18, 'bold'), foreground="#2c3e50")
        style.configure("Card.TFrame", background="white", relief="groove")

        # Main Container
        frame = ttk.Frame(self.root, padding="30")
        frame.pack(fill=tk.BOTH, expand=True)

        # Header
        lbl_header = ttk.Label(frame, text="AI Resume Screener", style="Header.TLabel")
        lbl_header.pack(pady=(10, 5))

        lbl_sub = ttk.Label(frame, text="Upload resume for parsing & personality analysis.")
        lbl_sub.pack(pady=(0, 30))

        # Upload Area
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10)
        
        self.btn_upload = ttk.Button(btn_frame, text="📂 Upload Resume (PDF/DOCX)", command=self.upload_file)
        self.btn_upload.pack(ipadx=20, ipady=5)

        self.lbl_status = ttk.Label(frame, text="Ready to scan", font=('Segoe UI', 9, 'italic'), foreground="grey")
        self.lbl_status.pack(pady=20)
        
        if self.analyzer.nlp is None:
            self.lbl_status.config(text="Warning: SpaCy model missing. Personality analysis will be limited.", foreground="red")

    def upload_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Resume Files", "*.pdf;*.docx;*.doc")])
        if file_path:
            self.lbl_status.config(text=f"Analyzing {os.path.basename(file_path)}...", foreground="blue")
            self.root.update_idletasks()
            
            try:
                self.extracted_data = self.analyzer.parse(file_path)
                self.show_dashboard(os.path.basename(file_path))
                self.lbl_status.config(text="Analysis Complete", foreground="green")
            except Exception as e:
                messagebox.showerror("Error", f"An error occurred: {str(e)}")
                self.lbl_status.config(text="Error occurred", foreground="red")

    def show_dashboard(self, filename):
        """Enhanced Results Window with AI Insights"""
        win = tk.Toplevel(self.root)
        win.title(f"Analysis Report: {filename}")
        win.geometry("900x700")
        win.configure(bg="#f5f6fa")

        # Scrollable Main Canvas
        main_canvas = tk.Canvas(win, bg="#f5f6fa")
        scrollbar = ttk.Scrollbar(win, orient="vertical", command=main_canvas.yview)
        scrollable_frame = ttk.Frame(main_canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        )

        main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        main_canvas.configure(yscrollcommand=scrollbar.set)

        main_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # --- Content Generation ---
        
        # 1. Candidate Header
        self.create_header_card(scrollable_frame)

        # 2. AI Insights (Side by Side: Exp Level & Personality)
        insights_frame = ttk.Frame(scrollable_frame)
        insights_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.create_exp_card(insights_frame)
        self.create_personality_card(insights_frame)

        # 3. Traditional Data (Text)
        self.create_details_section(scrollable_frame)

        # Buttons
        btn_frame = ttk.Frame(scrollable_frame)
        btn_frame.pack(fill=tk.X, padx=20, pady=20)
        ttk.Button(btn_frame, text="Save JSON", command=self.save_json).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Close", command=win.destroy).pack(side=tk.RIGHT)

    def create_header_card(self, parent):
        card = tk.LabelFrame(parent, text="Candidate Profile", font=('Segoe UI', 12, 'bold'), bg="white", padx=15, pady=15)
        card.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(card, text=self.extracted_data.get('Full Name', 'N/A'), font=('Segoe UI', 16, 'bold'), bg="white").pack(anchor="w")
        tk.Label(card, text=f"📧 {self.extracted_data.get('Email', 'N/A')}   |   📞 {self.extracted_data.get('Phone', 'N/A')}", bg="white", fg="#555").pack(anchor="w")

    def create_exp_card(self, parent):
        ai_data = self.extracted_data.get("AI_Analysis", {})
        
        frame = tk.LabelFrame(parent, text="Experience Analysis", font=('Segoe UI', 11, 'bold'), bg="white", padx=10, pady=10)
        frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        level = ai_data.get("Experience_Level", "Unknown")
        details = ai_data.get("Experience_Detail", "")

        # Color code the level
        color = "#27ae60" if "Senior" in level else "#2980b9" if "Mid" in level else "#f39c12"
        
        tk.Label(frame, text=level, font=('Segoe UI', 14, 'bold'), fg=color, bg="white").pack(pady=5)
        tk.Label(frame, text=details, font=('Segoe UI', 9), fg="#7f8c8d", bg="white").pack()

    def create_personality_card(self, parent):
        ai_data = self.extracted_data.get("AI_Analysis", {})
        traits = ai_data.get("Personality", {})
        
        frame = tk.LabelFrame(parent, text="Personality & Soft Skills (AI Inferred)", font=('Segoe UI', 11, 'bold'), bg="white", padx=10, pady=10)
        frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0))

        for trait, (rating, score) in traits.items():
            row = tk.Frame(frame, bg="white")
            row.pack(fill=tk.X, pady=2)
            
            tk.Label(row, text=trait, width=15, anchor="w", bg="white", font=('Segoe UI', 9)).pack(side=tk.LEFT)
            
            # Visual Bar
            bar_color = "#2ecc71" if rating == "High" else "#f1c40f" if rating == "Medium" else "#ecf0f1"
            canvas = tk.Canvas(row, width=100, height=10, bg="#ecf0f1", highlightthickness=0)
            canvas.pack(side=tk.LEFT, padx=10)
            
            fill_width = 100 if rating == "High" else 60 if rating == "Medium" else 20
            canvas.create_rectangle(0, 0, fill_width, 10, fill=bar_color, outline="")
            
            tk.Label(row, text=rating, width=10, anchor="e", bg="white", fg="#7f8c8d", font=('Segoe UI', 8)).pack(side=tk.RIGHT)
        
        tk.Label(frame, text="*Based on keyword frequency analysis", font=('Arial', 7, 'italic'), fg="grey", bg="white").pack(anchor="e", pady=(5,0))

    def create_details_section(self, parent):
        frame = tk.LabelFrame(parent, text="Extracted Details", font=('Segoe UI', 11, 'bold'), bg="white", padx=10, pady=10)
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        txt = scrolledtext.ScrolledText(frame, height=15, font=('Consolas', 9))
        txt.pack(fill=tk.BOTH, expand=True)

        sections = ["Skills", "Education", "Experience", "Achievements"]
        content = ""
        for sec in sections:
            content += f"--- {sec.upper()} ---\n"
            items = self.extracted_data.get(sec, [])
            if items:
                for item in items:
                    content += f"• {item}\n"
            else:
                content += "Not Found\n"
            content += "\n"
        
        txt.insert(tk.END, content)
        txt.config(state='disabled')

    def save_json(self):
        f = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if f:
            try:
                with open(f, 'w', encoding='utf-8') as outfile:
                    json.dump(self.extracted_data, outfile, indent=4)
                messagebox.showinfo("Success", "Saved successfully.")
            except Exception as e:
                messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = ResumeApp(root)
    root.mainloop()