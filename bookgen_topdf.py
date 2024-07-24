from fpdf import FPDF

class PDF(FPDF):
    def __init__(self, book_title, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.book_title = book_title
        self.chapters_list = []  # To store chapter titles and page numbers

    def header(self):
        self.set_font('Times', 'B', 12)
        self.cell(0, 10, self.book_title.encode('latin1', 'replace').decode('latin1'), 0, 1, 'C')
        self.ln(10)

    def chapter_title(self, chapter_title):
        self.set_font('Times', 'B', 14)
        self.cell(0, 10, chapter_title.encode('latin1', 'replace').decode('latin1'), 0, 1, 'L')
        self.ln(5)
        # Record the page number where this chapter starts
        self.chapters_list.append((chapter_title, self.page_no()))

    def chapter_body(self, body):
        self.set_font('Times', '', 12)
        body_text = "\n".join(body)
        self.multi_cell(0, 10, body_text.encode('latin1', 'replace').decode('latin1'))
        self.ln()

    def footer(self):
        self.set_y(-15)
        self.set_font('Times', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def add_title_page(self):
        self.add_page()
        self.set_font('Times', 'B', 24)
        self.cell(0, 100, self.book_title.encode('latin1', 'replace').decode('latin1'), 0, 1, 'C')
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
    
    # Add the title page first
    pdf.add_title_page()
    
    # Add pages for chapters and collect page numbers
    for chapter in chapters:
        pdf.add_page()
        pdf.chapter_title(chapter['chapter_title'])
        combined_subchapters = [subchapter['content'] for subchapter in chapter['subchapters']]
        pdf.chapter_body(combined_subchapters)

    # Add table of contents page after all chapters
    pdf.add_table_of_contents()
    
    pdf_filename = f"{title.replace(' ', '_').replace(':', '-').replace('?', '')}.pdf"
    pdf.output(pdf_filename, 'F')
    return pdf_filename

# Example usage
if __name__ == "__main__":
    chapters = [
        {
            'chapter_title': 'Introduction to AI',
            'subchapters': [
                {'content': 'Artificial Intelligence (AI) is a branch of computer science that aims to create machines that can perform tasks that typically require human intelligence.'},
                {'content': 'It involves various techniques such as machine learning, natural language processing, and robotics.'},
                {'content': 'In this chapter, we will cover the basics of AI, including its history, key concepts, and applications in different fields.'}
            ]
        },
        {
            'chapter_title': 'Deep Learning',
            'subchapters': [
                {'content': 'Deep Learning is a subset of machine learning that uses neural networks with many layers (deep neural networks). It has revolutionized fields such as computer vision, speech recognition, and natural language processing.'}
            ]
        }
    ]

    pdf_filename = gen_pdf('AI_Book', chapters)
    print(f"PDF generated: {pdf_filename}")
