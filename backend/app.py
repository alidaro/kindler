from flask import Flask, render_template, request, send_file, jsonify
import json
import openai
import os
from dotenv import load_dotenv
from fpdf import FPDF
import asyncio

# Load environment variables from .env file
load_dotenv()

# Import API key from environment variables
openai.api_key = os.getenv('OPENAI_KEY')

app = Flask(__name__, template_folder='../frontend/templates', static_folder='../frontend/static')

def save(filename, text):
    books_directory = os.path.join(app.static_folder, 'books')
    os.makedirs(books_directory, exist_ok=True)
    full_path = os.path.join(books_directory, filename)
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(text)

async def generate_chapters(book_title):
    prompt = [
        {
            "role": "system",
            "content": f"Generate a list of chapters and subchapters for a book titled '{book_title}' in JSON format. Do not include any explanation or code formatting. Format it in this way: "+"{\"chapter_name\":[\"subchapter_names\"],}"+". Please include between 5 and 10 subchapters per chapter."
        },
        {
            "role": "user",
            "content": "Generate with 4 space indents"
        },
    ]
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-4o-mini",
            messages=prompt
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        print(f"Error generating chapters: {e}")
        return None

async def generate_content(chapter_name, subchapter, book_title):
    prompt = [
        {
            "role": "system",
            "content": f"Generate the content for a subchapter in a book. The chapter title is '{chapter_name}'. The title of the subchapter is '{subchapter}'. The title of the book is '{book_title}'. Please only include the requested data."
        },
        {
            "role": "user",
            "content": "Do not include the chapter title, the subchapter title, or the book title in the data, only the chapter content."
        },
    ]
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-4o-mini",
            messages=prompt
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        print(f"Error generating content for subchapter '{subchapter}': {e}")
        return None

async def generate_chapter_content(chapter_name, subchapters, book_title):
    tasks = [generate_content(chapter_name, subchapter, book_title) for subchapter in subchapters]
    results = await asyncio.gather(*tasks)
    sections = [{"subchapter": subchapters[i], "content": content} for i, content in enumerate(results) if content]
    return {"chapter_title": chapter_name, "subchapters": sections}

class PDF(FPDF):
    def __init__(self, book_title, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.book_title = book_title
        self.chapters_list = []

    def header(self):
        self.set_font('Times', 'B', 12)
        self.cell(0, 10, self.book_title, 0, 1, 'C')
        self.ln(10)

    def chapter_title(self, chapter_title):
        self.set_font('Times', 'B', 14)
        self.cell(0, 10, chapter_title, 0, 1, 'L')
        self.ln(5)
        self.chapters_list.append((chapter_title, self.page_no()))

    def chapter_body(self, body):
        self.set_font('Times', '', 12)
        body_text = "\n".join(body)
        self.multi_cell(0, 10, body_text)
        self.ln()

    def footer(self):
        self.set_y(-15)
        self.set_font('Times', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def add_title_page(self):
        self.add_page()
        self.set_font('Times', 'B', 24)
        self.cell(0, 100, self.book_title, 0, 1, 'C')
        self.ln(10)
        self.set_font('Times', '', 16)
        self.cell(0, 10, 'Alidar Panaguzhiyev', 0, 1, 'C')
        self.ln(50)

    def add_table_of_contents(self):
        self.add_page()
        self.set_font('Times', 'B', 16)
        self.cell(0, 10, 'Table of Contents', 0, 1, 'C')
        self.ln(10)

        self.set_font('Times', '', 12)
        for chapter_title, page_num in self.chapters_list:
            self.cell(0, 10, f'{chapter_title} - Page {page_num}', 0, 1, 'L')

def gen_pdf(title, chapters):
    pdf = PDF(book_title=title)
    pdf.add_title_page()
    
    for chapter in chapters:
        pdf.add_page()
        pdf.chapter_title(chapter['chapter_title'])
        combined_subchapters = [subchapter['content'] for subchapter in chapter['subchapters']]
        pdf.chapter_body(combined_subchapters)
    
    pdf.add_table_of_contents()
    
    pdf_filename = f"{title.replace(' ', '_').replace(':', '-').replace('?', '')}.pdf"
    pdf_output_path = os.path.join(app.static_folder, 'books', pdf_filename)
    pdf.output(pdf_output_path, 'F')
    return pdf_filename

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
async def generate():
    book_title = request.form['book_title']
    
    chapters_names = await generate_chapters(book_title)
    if not chapters_names:
        return jsonify({"error": "Failed to generate chapters"}), 500

    save('chapters.json', chapters_names)

    try:
        chapters_json = json.loads(chapters_names)
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return jsonify({"error": "Failed to decode JSON"}), 500

    tasks = [generate_chapter_content(chapter_name, subchapters, book_title) for chapter_name, subchapters in chapters_json.items()]
    chapters = await asyncio.gather(*tasks)

    pdf_filename = gen_pdf(book_title, chapters)
    pdf_out = os.path.join(app.static_folder, 'books', pdf_filename)
    
    if not os.path.exists(pdf_out):
        return jsonify({"error": "PDF file not found"}), 500
    
    return jsonify({"filename": pdf_filename})

@app.route('/download/<filename>')
def download(filename):
    filepath = os.path.join(app.static_folder, 'books', filename)
    if not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404
    return send_file(filepath, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
